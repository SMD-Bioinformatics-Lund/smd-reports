"""Validated design tokens and application theme defaults."""

import re

from pydantic import Field, field_validator

from ..core import Model
from ..errors import ReportInputError


class Theme(Model):
    """Named colors and typography used by the shared report layout.

    Attributes:
        name: Registry key for the theme.
        heading: Section-heading color.
        accent: Primary brand-rule color.
        tint: Table and metadata background color.
        rule_end: Secondary brand-rule color.
        body_pt: Body type size in points.
    """

    name: str
    heading: str
    accent: str
    tint: str
    rule_end: str
    body_pt: float = Field(default=9.25, ge=8, le=12)

    @field_validator("heading", "accent", "tint", "rule_end")
    @classmethod
    def hex_color(cls, value: str) -> str:
        """Validate an opaque six-digit RGB color.

        Args:
            value: CSS hexadecimal color string.

        Returns:
            The original color string.

        Raises:
            ValueError: The color is not in #RRGGBB form.
        """
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ReportInputError("Expected a six-digit hex color")
        return value


def default_themes() -> dict[str, Theme]:
    """Create independent theme instances for each built-in preset.

    Returns:
        A mapping of preset names to fresh Theme instances.
    """
    palettes = {
        "generic": ("#435365", "#64748B", "#f3f5f7", "#aab4c0"),
        "coyote3": ("#665271", "#a58ab8", "#f4eff8", "#d9b18a"),
        "genexus": ("#3c6585", "#3c6585", "#f0f6fb", "#91b5cd"),
        "cll_genie": ("#7B4925", "#DF7849", "#FFF8F5", "#dca37b"),
        "pgx": ("#176B68", "#278780", "#edf7f5", "#9dcac0"),
    }
    return {
        key: Theme(name=key, heading=p[0], accent=p[1], tint=p[2], rule_end=p[3])
        for key, p in palettes.items()
    }
