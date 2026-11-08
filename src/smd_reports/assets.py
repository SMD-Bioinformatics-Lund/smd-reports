"""Embed local report artwork and validate static SVG without external resources."""

import base64
import re
from io import BytesIO
from pathlib import Path
from typing import Literal

from defusedxml import ElementTree

ImageFormat = Literal["png", "jpeg", "svg", "webp", "gif", "tiff", "bmp"]
IMAGE_MIMES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "svg": "image/svg+xml",
    "webp": "image/webp",
    "gif": "image/gif",
    "tiff": "image/tiff",
    "bmp": "image/bmp",
}
IMAGE_EXTENSIONS = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".svg": "svg",
    ".webp": "webp",
    ".gif": "gif",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".bmp": "bmp",
}


def validate_image_reference(value: str) -> str:
    """Validate a local path or embedded image reference without fetching URLs.

    Args:
        value: An image path or base64 data URI.

    Returns:
        The validated reference.

    Raises:
        ValueError: The path is empty or remote, or embedded image data is invalid.
    """
    if value.startswith("data:"):
        validate_image(value)
    elif not value.strip() or (":" in value and not Path(value).is_absolute()) or "\x00" in value:
        raise ValueError("Use a local image path or embedded image data URI")
    return value


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
    """Validate raster content or a restricted static SVG document.

    Args:
        value: A supported base64 image data URI.

    Returns:
        The original data URI.

    Raises:
        ValueError: Content is empty, malformed, unsafe, or inconsistent with its MIME type.
    """
    prefix, separator, encoded = value.partition(",")
    if not separator or prefix not in {f"data:{mime};base64" for mime in IMAGE_MIMES.values()}:
        raise ValueError("Supply a supported base64 image data URI")
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
    else:
        from PIL import Image

        try:
            with Image.open(BytesIO(raw)) as image:
                expected = prefix.removeprefix("data:").removesuffix(";base64").split("/")[-1]
                if image.format.lower() != expected:
                    raise ValueError("Image content does not match its MIME type")
                image.verify()
        except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
            raise ValueError("Invalid or unsupported raster image") from exc
    return value


def prepare_image(value: str, *, frame: int = 0, accepted_formats=None) -> str:
    """Select an image frame and produce portable HTML image data.

    Args:
        value: A supported embedded image data URI.
        frame: Nonnegative frame or TIFF page index, starting at zero.
        accepted_formats: Optional allowed format names; None permits every
            format supported by the package.

    Returns:
        A PNG, JPEG, or static SVG data URI. Other supported raster formats
        are converted to a static PNG.

    Raises:
        ValueError: The image format or requested frame is not accepted.
    """
    validate_image(value)
    prefix, encoded = value.split(",", 1)
    image_format = next(
        name for name, mime in IMAGE_MIMES.items() if prefix == f"data:{mime};base64"
    )
    if accepted_formats is not None and image_format not in accepted_formats:
        raise ValueError("Image format is not in accepted_image_formats")
    if image_format == "svg":
        if frame != 0:
            raise ValueError("SVG images have only one frame")
        return value
    from PIL import Image

    with Image.open(BytesIO(base64.b64decode(encoded))) as image:
        if frame >= getattr(image, "n_frames", 1):
            raise ValueError("The selected image frame does not exist")
        image.seek(frame)
        image.load()
        if image_format in {"png", "jpeg"} and frame == 0 and getattr(image, "n_frames", 1) == 1:
            return value
        output = BytesIO()
        image.convert("RGBA").save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()


def embed_image(path: str | Path) -> str:
    """Read a local artwork file and encode it as validated image data.

    Args:
        path: Path to a supported image file.

    Returns:
        A base64 image data URI.

    Raises:
        OSError: The file cannot be read.
        ValueError: The extension or file contents are unsupported.
    """
    path = Path(path)
    image_format = IMAGE_EXTENSIONS.get(path.suffix.lower())
    if image_format is None:
        raise ValueError("Unsupported image file extension")
    mime = IMAGE_MIMES[image_format]
    return validate_image(f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode())
