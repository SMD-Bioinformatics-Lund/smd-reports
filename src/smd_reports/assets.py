"""Embed local report artwork and validate static SVG without external resources."""

import base64
import re
from pathlib import Path

from defusedxml import ElementTree

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
}


def validate_image(value: str) -> str:
    """Accept embedded PNG, JPEG or static SVG; reject active or remote SVG content."""
    prefix, separator, encoded = value.partition(",")
    if not separator or prefix not in {
        "data:image/png;base64",
        "data:image/jpeg;base64",
        "data:image/svg+xml;base64",
    }:
        raise ValueError("Supply a base64 PNG, JPEG or static SVG data URI")
    raw = base64.b64decode(encoded, validate=True)
    if not raw:
        raise ValueError("Empty image")
    if prefix == "data:image/svg+xml;base64":
        without_declaration = re.sub(rb"^\s*<\?xml\s[^?]*\?>", b"", raw)
        if b"<?" in without_declaration or b"<!DOCTYPE" in raw.upper():
            raise ValueError("SVG processing instructions and document types are prohibited")
        try:
            root = ElementTree.fromstring(raw)
        except Exception as exc:
            raise ValueError("Invalid or unsafe SVG") from exc
        if root.tag.split("}")[-1] != "svg":
            raise ValueError("Expected an SVG root")
        for element in root.iter():
            if element.tag.split("}")[-1] not in SVG_TAGS:
                raise ValueError("SVG must contain static artwork only")
            for name, attribute in element.attrib.items():
                name = name.split("}")[-1].lower()
                if name.startswith("on") or name in {"src", "base"}:
                    raise ValueError("Active SVG attributes are prohibited")
                if name == "href" and not re.fullmatch(r"#[A-Za-z_][\w.-]*", attribute):
                    raise ValueError("SVG references must be local fragments")
                # Disallow CSS escapes/imports and all URL functions, including encoded variants.
                if "\\" in attribute or "@" in attribute or re.search(r"url\s*\(", attribute, re.I):
                    raise ValueError("SVG URL/CSS resources are prohibited")
    return value


def embed_image(path: str | Path) -> str:
    """Read an explicitly supplied local artwork file into a validated data URI."""
    path = Path(path)
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
    }.get(path.suffix.lower())
    if mime is None:
        raise ValueError("Logo files must be PNG, JPEG or static SVG")
    return validate_image(f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode())
