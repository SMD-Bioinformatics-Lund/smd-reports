"""Measure compact-table cells with the report's bundled fonts."""

import base64
import math
import re
from functools import lru_cache
from importlib.resources import files
from io import BytesIO

from fontTools.ttLib import TTFont
from PIL import ImageFont, features

from .errors import ReportInputError


@lru_cache(maxsize=1)
def _font_data():
    """Read the bundled font faces and their supported characters.

    Returns:
        Font bytes and character maps in stylesheet order.
    """
    css = files("smd_reports").joinpath("static/fonts.css").read_text(encoding="utf-8")
    result = []
    for encoded in re.findall(r"data:font/woff2;base64,([A-Za-z0-9+/=]+)", css):
        with TTFont(BytesIO(base64.b64decode(encoded))) as font:
            characters = frozenset(font.getBestCmap())
            font.flavor = None
            output = BytesIO()
            font.save(output)
            result.append((output.getvalue(), characters))
    return tuple(result)


@lru_cache(maxsize=12)
def _fonts(size_pt):
    """Load reusable font measurements at the selected print size.

    Args:
        size_pt: Compact-table text size in points.

    Returns:
        Font instances using CSS pixel units.
    """
    return tuple(
        ImageFont.truetype(BytesIO(data), size=size_pt * 96 / 72) for data, _ in _font_data()
    )


def column_widths(texts, size_pt, width_mm, *, columns=None, markdown=False):
    """Choose equal-width columns that fit complete, single-line items.

    Args:
        texts: Visible cell text in its display order.
        size_pt: Compact-table text size in points.
        width_mm: Available content width after page margins.
        columns: Optional upper limit on the number of columns.
        markdown: Allow for the widest bundled emphasis face.

    Returns:
        Column widths in CSS pixels, excluding empty cells in the final row.

    Raises:
        ReportInputError: An item cannot fit on one line or uses unsupported characters.
    """
    if not texts:
        return []
    fonts = _fonts(size_pt)
    characters = _font_data()[0][1]
    available = math.floor(width_mm * 96 / 25.4) - 2
    options = {"features": ["tnum"]} if features.check_feature("raqm") else {}
    widths = []
    for text in texts:
        if any(ord(character) not in characters for character in text):
            raise ReportInputError(
                "Compact table text uses characters missing from the bundled font; "
                "use a regular table."
            )
        faces = fonts if markdown else fonts[:1]
        measured = max(face.getlength(text, **options) for face in faces)
        # Include 4px horizontal padding, 1px collapsed borders and 0.5px rounding safety.
        emphasis = len(text) * size_pt * 96 / 72 * 0.04 if markdown else 0
        width = measured + emphasis + 5.5
        if width > available:
            raise ReportInputError(
                "A compact table item cannot fit on one line; use a wider page or a shorter item."
            )
        widths.append(width)
    cell_width = max(widths)
    count = min(len(widths), columns or len(widths), math.floor(available / cell_width))
    if len(widths) > count:
        cell_width = available / count
    return [cell_width] * count
