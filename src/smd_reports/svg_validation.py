"""Validate self-contained SVG styles and embedded fonts without rewriting artwork."""

import base64
import re
import struct
from functools import lru_cache
from io import BytesIO
from xml.etree.ElementTree import TreeBuilder, fromstring

import brotli
import tinycss2
from defusedxml.ElementTree import DefusedXMLParser
from fontTools.ttLib import TTFont
from fontTools.ttLib.woff2 import WOFF2DirectoryEntry

from .errors import ReportInputError

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_TAGS = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "defs",
    "use",
    "symbol",
    "clipPath",
    "mask",
    "linearGradient",
    "radialGradient",
    "stop",
    "title",
    "desc",
    "metadata",
    "style",
}
EDITOR_TAGS = {
    "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd": {"namedview", "guide"},
    "http://www.inkscape.org/namespaces/inkscape": {"grid", "perspective"},
}
METADATA_NAMESPACES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://purl.org/dc/elements/1.1/",
    "http://purl.org/dc/terms/",
    "http://creativecommons.org/ns#",
    "http://ns.adobe.com/xap/1.0/",
}
CSS_PROPERTIES = set(
    """
    fill fill-opacity fill-rule stroke stroke-width stroke-opacity stroke-linecap
    stroke-linejoin stroke-miterlimit stroke-dasharray stroke-dashoffset opacity
    color stop-color stop-opacity flood-color flood-opacity lighting-color
    clip clip-path clip-rule mask filter marker-start marker-mid marker-end
    font font-family font-size font-size-adjust font-style font-weight font-stretch
    font-feature-settings font-variation-settings font-kerning font-variant
    font-variant-ligatures letter-spacing word-spacing text-anchor text-decoration
    text-rendering text-transform shape-rendering image-rendering color-interpolation
    color-interpolation-filters alignment-baseline dominant-baseline baseline-shift
    paint-order vector-effect transform transform-origin display visibility overflow
    white-space writing-mode direction unicode-bidi background background-color
    -inkscape-font-specification -webkit-font-smoothing -moz-osx-font-smoothing
""".split()
)
FONT_DESCRIPTORS = {
    "font-family",
    "src",
    "font-style",
    "font-weight",
    "font-stretch",
    "font-display",
    "unicode-range",
    "font-feature-settings",
    "font-variation-settings",
}
STATIC_FUNCTIONS = set(
    """
    rgb rgba hsl hsla hwb lab lch oklab oklch color color-mix calc min max clamp
    matrix matrix3d translate translatex translatey translatez translate3d
    scale scalex scaley scalez scale3d rotate rotatex rotatey rotatez rotate3d
    skew skewx skewy perspective cubic-bezier steps var
""".split()
)
FONT_PREFIX = "data:font/woff2;base64,"
MAX_FONT_BYTES = 2 * 1024 * 1024
MAX_FONT_EXPANDED_BYTES = 16 * 1024 * 1024


class _SvgTreeBuilder(TreeBuilder):
    """Reject processing instructions after XML encoding has been decoded."""

    def pi(self, target, text=None):
        """Reject every processing instruction, including stylesheet instructions.

        Args:
            target: Processing instruction name supplied by the XML parser.
            text: Optional processing instruction payload.

        Raises:
            ReportInputError: Processing instructions are not report artwork.
        """
        raise ReportInputError("SVG processing instructions are prohibited")


def _brotli_size(content: bytes, expected: int) -> None:
    """Check decoded size before the font parser allocates its complete buffer.

    Args:
        content: One complete Brotli stream from a WOFF2 container.
        expected: Declared decoded byte count, bounded by the font-size policy.

    Raises:
        ValueError: Decoding fails or exceeds the declared size.
    """
    if not 0 < expected <= MAX_FONT_EXPANDED_BYTES:
        raise ValueError("Invalid expanded font size")
    decoder = brotli.Decompressor()
    size = 0
    for byte in content:
        size += len(decoder.process(bytes((byte,))))
        if size > expected:
            raise ValueError("Font stream exceeds declared size")
    if not decoder.is_finished() or size != expected:
        raise ValueError("Invalid compressed font stream")


@lru_cache(maxsize=8)
def validate_font_uri(uri: str) -> None:
    """Validate a complete embedded WOFF2 font before it reaches a renderer.

    Args:
        uri: Strict base64 data URI with the font/woff2 MIME type.

    Raises:
        ReportInputError: Font encoding, header, tables or contents are invalid.
    """
    if not uri.startswith(FONT_PREFIX) or len(uri) > MAX_FONT_BYTES * 4 // 3 + 64:
        raise ReportInputError("Supply an embedded WOFF2 font within the size limit")
    try:
        raw = base64.b64decode(uri[len(FONT_PREFIX) :], validate=True)
        if len(raw) < 48 or len(raw) > MAX_FONT_BYTES:
            raise ValueError("Invalid font size")
        header = struct.unpack(">4s4sIHHIIHHIIIII", raw[:48])
        signature, flavor, length, tables, reserved, expanded, compressed = header[:7]
        if (
            signature != b"wOF2"
            or flavor not in {b"\x00\x01\x00\x00", b"OTTO"}
            or length != len(raw)
            or not 0 < tables <= 4095
            or reserved
            or not 0 < expanded <= MAX_FONT_EXPANDED_BYTES
            or not 0 < compressed <= len(raw) - 48
            or header[11] > MAX_FONT_EXPANDED_BYTES
        ):
            raise ValueError("Invalid WOFF2 header")
        directory = BytesIO(raw)
        directory.seek(48)
        entries = []
        for _ in range(tables):
            entry = WOFF2DirectoryEntry()
            entry.fromFile(directory)
            entries.append(entry)
        if len({entry.tag for entry in entries}) != tables:
            raise ValueError("Duplicate font tables")
        if 12 + 16 * tables + sum((entry.origLength + 3) // 4 * 4 for entry in entries) != expanded:
            raise ValueError("Inconsistent expanded font size")
        end = directory.tell() + compressed
        if end > len(raw):
            raise ValueError("Truncated font stream")
        _brotli_size(raw[directory.tell() : end], sum(entry.length for entry in entries))
        meta_offset, meta_length, meta_expanded, private_offset, private_length = header[9:]
        for offset, length in ((meta_offset, meta_length), (private_offset, private_length)):
            if bool(offset) != bool(length) or (
                offset and (offset < end or offset + length > len(raw))
            ):
                raise ValueError("Invalid font metadata bounds")
        if meta_offset:
            _brotli_size(raw[meta_offset : meta_offset + meta_length], meta_expanded)
        elif meta_expanded:
            raise ValueError("Invalid font metadata size")
        if meta_offset and private_offset and private_offset < meta_offset + meta_length:
            raise ValueError("Overlapping font metadata")
        with TTFont(
            BytesIO(raw), lazy=False, checkChecksums=2, recalcBBoxes=False, recalcTimestamp=False
        ) as font:
            if "SVG " in font:
                raise ValueError("SVG glyph documents are not supported")
            required = {"head", "hhea", "maxp", "hmtx", "cmap", "name"}
            if not required.issubset(font.keys()) or not (
                {"glyf", "CFF ", "CFF2"} & set(font.keys())
            ):
                raise ValueError("Missing font tables")
            font.ensureDecompiled(recurse=True)
    except Exception as exc:
        raise ReportInputError("Invalid embedded WOFF2 font") from exc


def _tokens(tokens, *, font_source=False, depth=0, strict_functions=True):
    """Check decoded CSS tokens and every nested resource reference.

    Args:
        tokens: Tokens produced by tinycss2, including decoded CSS escapes.
        font_source: Whether URLs belong to a font-face src descriptor.
        depth: Current CSS nesting depth.
        strict_functions: Enforce the CSS function allowlist for presentation values.

    Raises:
        ReportInputError: A token, function or reference is unsafe or unsupported.
    """
    if depth > 32:
        raise ReportInputError("SVG CSS nesting is too deep")
    for token in tokens:
        reference = None
        if token.type in {"error", "at-keyword"}:
            raise ReportInputError("Invalid or unsafe SVG CSS")
        if token.type == "url":
            reference = token.value
        elif token.type == "function":
            name = token.lower_name
            if name == "url":
                args = [
                    item for item in token.arguments if item.type not in {"whitespace", "comment"}
                ]
                if len(args) != 1 or args[0].type != "string":
                    raise ReportInputError("Invalid SVG CSS URL")
                reference = args[0].value
            elif name == "format" and font_source:
                args = [
                    item for item in token.arguments if item.type not in {"whitespace", "comment"}
                ]
                if len(args) != 1 or args[0].type != "string" or args[0].value.lower() != "woff2":
                    raise ReportInputError("SVG font format must be WOFF2")
            elif name not in STATIC_FUNCTIONS and strict_functions:
                raise ReportInputError("Unsafe or unsupported SVG CSS function")
            else:
                _tokens(
                    token.arguments,
                    font_source=font_source,
                    depth=depth + 1,
                    strict_functions=strict_functions,
                )
        elif hasattr(token, "content"):
            _tokens(
                token.content,
                font_source=font_source,
                depth=depth + 1,
                strict_functions=strict_functions,
            )
        if reference is not None:
            if font_source:
                validate_font_uri(reference)
            elif not re.fullmatch(r"#[A-Za-z_][\w.-]*", reference):
                raise ReportInputError("SVG CSS references must be local fragments")


def _font_sources(tokens):
    """Require each font source to be an embedded URL with an optional WOFF2 format.

    Args:
        tokens: Component-value tokens from a font-face src descriptor.

    Raises:
        ReportInputError: Sources use indirection, local fonts or malformed syntax.
    """
    tokens = [t for t in tokens if t.type not in {"whitespace", "comment"}]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type != "url" and not (token.type == "function" and token.lower_name == "url"):
            raise ReportInputError("SVG fonts require embedded WOFF2 URL sources")
        index += 1
        if (
            index < len(tokens)
            and tokens[index].type == "function"
            and tokens[index].lower_name == "format"
        ):
            index += 1
        if index == len(tokens):
            return
        if tokens[index].type != "literal" or tokens[index].value != ",":
            break
        index += 1
    raise ReportInputError("Invalid SVG font source list")


def _declarations(content, *, font_face=False):
    """Validate CSS properties and font descriptors without changing their values.

    Args:
        content: CSS text or component-value tokens.
        font_face: Whether declarations belong to an embedded font definition.

    Returns:
        Validated declarations.

    Raises:
        ReportInputError: Declarations contain unsupported properties or unsafe values.
    """
    declarations = tinycss2.parse_declaration_list(
        content, skip_comments=True, skip_whitespace=True
    )
    allowed = FONT_DESCRIPTORS if font_face else CSS_PROPERTIES
    for declaration in declarations:
        if declaration.type != "declaration" or declaration.lower_name not in allowed:
            raise ReportInputError("Unsafe or unsupported SVG CSS property")
        source = font_face and declaration.lower_name == "src"
        _tokens(declaration.value, font_source=source)
        if source:
            _font_sources(declaration.value)
    return declarations


def _stylesheet(content):
    """Validate static SVG CSS and collect its embedded font-face rules.

    Args:
        content: Decoded SVG stylesheet text.

    Returns:
        Font-face rules safe for the document's print renderer.

    Raises:
        ReportInputError: Styles contain imports, unsupported rules or invalid fonts.
    """
    faces = []
    for rule in tinycss2.parse_stylesheet(content, skip_comments=True, skip_whitespace=True):
        if rule.type == "qualified-rule":
            _tokens(rule.prelude, strict_functions=False)
            _declarations(rule.content)
        elif (
            rule.type == "at-rule"
            and rule.lower_at_keyword == "font-face"
            and rule.content is not None
        ):
            if any(t.type not in {"whitespace", "comment"} for t in rule.prelude):
                raise ReportInputError("Invalid SVG font-face rule")
            declarations = _declarations(rule.content, font_face=True)
            values = {d.lower_name: d.value for d in declarations}
            family = [
                t for t in values.get("font-family", []) if t.type not in {"whitespace", "comment"}
            ]
            if not family or not values.get("src"):
                raise ReportInputError("SVG font-face requires font-family and embedded src")
            if not (
                len(family) == 1 and family[0].type == "string" and family[0].value.strip()
            ) and not all(t.type == "ident" for t in family):
                raise ReportInputError("SVG font-family must name one font family")
            # CSS strings containing '<' must not terminate the surrounding HTML style element.
            faces.append(tinycss2.serialize([rule]).replace("<", r"\3c "))
        else:
            raise ReportInputError("SVG CSS supports static rules and embedded font-face only")
    return faces


def validate_svg(content: bytes) -> tuple[str, ...]:
    """Validate SVG XML, inert metadata, CSS and fonts while preserving original bytes.

    Args:
        content: Original SVG bytes, including an optional XML declaration.

    Returns:
        Embedded font-face rules needed by renderers that ignore SVG-local definitions.

    Raises:
        ReportInputError: XML, artwork, metadata, styles or resources are unsafe.
    """
    try:
        parser = DefusedXMLParser(
            target=_SvgTreeBuilder(), forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
        root = fromstring(content, parser=parser)
    except ReportInputError:
        raise
    except Exception as exc:
        raise ReportInputError("Invalid or unsafe SVG") from exc
    if root.tag not in {"svg", f"{{{SVG_NAMESPACE}}}svg"}:
        raise ReportInputError("Expected an SVG root")
    faces = []
    pending = [(root, False)]
    while pending:
        element, metadata = pending.pop()
        namespace, _, tag = (
            element.tag[1:].partition("}") if element.tag.startswith("{") else ("", "", element.tag)
        )
        if tag.lower() in {
            "script",
            "foreignobject",
            "image",
            "animate",
            "animatetransform",
            "set",
        }:
            raise ReportInputError("SVG must contain static artwork only")
        if namespace in {"", SVG_NAMESPACE}:
            if tag not in SVG_TAGS:
                raise ReportInputError("SVG must contain static artwork only")
        elif tag not in EDITOR_TAGS.get(namespace, set()) and not (
            metadata and namespace in METADATA_NAMESPACES
        ):
            raise ReportInputError("Unsupported SVG metadata or element namespace")
        inert_element = metadata or tag == "metadata" or namespace in EDITOR_TAGS
        for key, value in element.attrib.items():
            attribute_namespace = key[1:].partition("}")[0] if key.startswith("{") else ""
            inert_attribute = (
                inert_element
                or attribute_namespace in EDITOR_TAGS
                or attribute_namespace in METADATA_NAMESPACES
            )
            name = key.rsplit("}", 1)[-1].lower()
            if name.startswith("on") or name in {"src", "base"}:
                raise ReportInputError("Active SVG attributes are prohibited")
            if name == "href" and not re.fullmatch(r"#[A-Za-z_][\w.-]*", value):
                raise ReportInputError("SVG references must be local fragments")
            if name == "style":
                _declarations(value)
            elif name in CSS_PROPERTIES or not inert_attribute:
                _tokens(
                    tinycss2.parse_component_value_list(value),
                    strict_functions=name in CSS_PROPERTIES,
                )
        if tag == "style":
            if len(element) or element.get("type", "text/css").strip().lower() != "text/css":
                raise ReportInputError("SVG styles must contain CSS text only")
            faces.extend(_stylesheet(element.text or ""))
        pending.extend((child, metadata or tag == "metadata") for child in element)
    return tuple(dict.fromkeys(faces))


def svg_font_css(sources, report_fonts: str) -> str:
    """Expose validated SVG fonts to HTML/PDF conversion without changing the SVG.

    Args:
        sources: Embedded artwork data URIs, including optional absent logos.
        report_fonts: The package's existing font-face stylesheet.

    Returns:
        Additional font-face CSS safe inside an HTML style element.

    Raises:
        ReportInputError: Artwork font definitions conflict with another font of the same name.
    """
    faces = []
    for source in sources:
        if source and source.startswith("data:image/svg+xml;base64,"):
            for face in validate_svg(base64.b64decode(source.split(",", 1)[1], validate=True)):
                if face not in faces:
                    faces.append(face)
    if not faces:
        return ""
    registry = {}
    reserved = set()

    def register(face, *, bundled=False):
        rule = tinycss2.parse_stylesheet(face, skip_comments=True, skip_whitespace=True)[0]
        values = {
            d.lower_name: d.value
            for d in tinycss2.parse_declaration_list(
                rule.content, skip_comments=True, skip_whitespace=True
            )
        }
        family = " ".join(
            t.value for t in values["font-family"] if t.type in {"string", "ident"}
        ).casefold()
        descriptors = {key: tinycss2.serialize(value).strip() for key, value in values.items()}
        weight = descriptors.get("font-weight", "normal")
        weight = {"normal": "400", "bold": "700"}.get(weight, weight)
        key = (
            family,
            descriptors.get("font-style", "normal"),
            weight,
            descriptors.get("font-stretch", "normal"),
        )
        source = []
        for token in values["src"]:
            if token.type == "url":
                source.append(token.value)
            elif token.type == "function" and token.lower_name == "url":
                source.append(next(t.value for t in token.arguments if t.type == "string"))
        identity = (
            tuple(source),
            descriptors.get("unicode-range"),
            descriptors.get("font-feature-settings"),
            descriptors.get("font-variation-settings"),
        )
        if not bundled and (
            (key in registry and registry[key] != identity)
            or (family in reserved and key not in registry)
        ):
            raise ReportInputError(
                "SVG font-family conflicts with an existing report or artwork font"
            )
        registry[key] = identity
        if bundled:
            reserved.add(family)

    for rule in tinycss2.parse_stylesheet(report_fonts, skip_comments=True, skip_whitespace=True):
        if rule.type == "at-rule" and rule.lower_at_keyword == "font-face":
            register(tinycss2.serialize([rule]), bundled=True)
    for face in faces:
        register(face)
    return "\n".join(faces)
