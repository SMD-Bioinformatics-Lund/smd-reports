"""Base models and field types for report JSON."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)

Language = Literal["en", "sv"]
Translations = Annotated[dict[Language, str], Field(min_length=1)]
LocalizedText = str | Translations
Scalar = StrictBool | StrictInt | StrictFloat | StrictStr | None
CellValue = Scalar | Translations


class Model(BaseModel):
    """Reject unknown fields and non-finite numbers."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class FieldValue(Model):
    """An ordered metadata label paired with a scalar or translated value."""

    label: LocalizedText
    value: CellValue


class ImageAsset(Model):
    """A local or embedded plot and its display options.

    Attributes:
        source: Local path or embedded data URI.
        caption: Literal or translated caption text.
        alt: Alternative text, falling back to the caption when omitted.
        frame: Zero-based frame or TIFF page index.
        width_percent: Width relative to the content area.
        max_height_mm: Optional additional physical height limit.
    """

    source: str
    caption: LocalizedText = ""
    alt: LocalizedText = ""
    frame: int = Field(default=0, ge=0)
    width_percent: float = Field(default=100, gt=0, le=100)
    max_height_mm: float | None = Field(default=None, gt=0)

    @field_validator("source")
    @classmethod
    def image_reference(cls, value):
        """Validate the image path or embedded content.

        Args:
            value: Local image path or base64 data URI.

        Returns:
            The validated reference.

        Raises:
            ValueError: The reference or embedded image is unsupported.
        """
        from .assets import validate_image_reference

        return validate_image_reference(value)


class SectionBase(Model):
    """Shared section identity, heading, pagination, and inline image fields."""

    key: str = Field(min_length=1)
    heading: LocalizedText = ""
    page_break_before: bool = False
    images: list[ImageAsset] = Field(default_factory=list)
