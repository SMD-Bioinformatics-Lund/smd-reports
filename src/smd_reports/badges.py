"""Optional badge styles for values in shared report components."""

from typing import Literal

from pydantic import Field, model_validator

from .errors import ReportInputError
from .models import Model

TierPreset = Literal["tier1", "tier2", "tier3", "tier4"]
TIER_COLORS = {
    "tier1": "#af6246",
    "tier2": "#ae8540",
    "tier3": "#4f7d9f",
    "tier4": "#4b8b76",
}


class BadgeStyle(Model):
    """A tier preset, an explicit background color, or the current theme color.

    Attributes:
        preset: Optional predefined tier color.
        color: Optional background color in six-digit hexadecimal notation.
    """

    preset: TierPreset | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @model_validator(mode="after")
    def single_color_source(self):
        """Require one unambiguous source for the badge background.

        Returns:
            The validated style.

        Raises:
            ReportInputError: Both a preset and explicit color are supplied.
        """
        if self.preset is not None and self.color is not None:
            raise ReportInputError("Choose either a badge preset or a custom color")
        return self


class BadgeOptions(BadgeStyle):
    """One badge style for a column, or styles keyed by displayed cell text.

    Attributes:
        values: Exact display values mapped to tier names or style objects.
            Unlisted values remain plain when this mapping is nonempty.
    """

    values: dict[str, BadgeStyle | TierPreset] = Field(default_factory=dict)

    @model_validator(mode="after")
    def single_selection_mode(self):
        """Keep whole-column styling separate from per-value styling.

        Returns:
            The validated badge options.

        Raises:
            ReportInputError: A whole-column style and value mapping are combined.
        """
        if self.values and (self.preset is not None or self.color is not None):
            raise ReportInputError("Choose a whole-column badge style or per-value badge styles")
        return self

    def style_for(self, text: str) -> BadgeStyle | None:
        """Resolve a style without assigning meaning to the displayed value.

        Args:
            text: Cell text in the selected report language.

        Returns:
            A badge style, or None for an unlisted value.
        """
        if not self.values:
            return self
        selected = self.values.get(text)
        return BadgeStyle(preset=selected) if isinstance(selected, str) else selected


def badge_colors(style: BadgeStyle, theme_color: str) -> tuple[str, str]:
    """Select a background and the more legible black or white foreground.

    Args:
        style: Validated color selection.
        theme_color: Theme heading color used when no explicit style is selected.

    Returns:
        Background and foreground colors in hexadecimal notation.
    """
    background = style.color or TIER_COLORS.get(style.preset, theme_color)
    channels = [int(background[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    luminance = sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    black_contrast = (luminance + 0.05) / 0.05
    white_contrast = 1.05 / (luminance + 0.05)
    return background, "#000000" if black_contrast >= white_contrast else "#ffffff"
