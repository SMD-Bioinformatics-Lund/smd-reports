"""Validation primitives for the JSON document format."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Language = Literal["en", "sv"]
Translations = Annotated[dict[Language, str], Field(min_length=1)]
LocalizedText = str | Translations
Scalar = str | int | float | bool | None
CellValue = Scalar | Translations


class Model(BaseModel):
    """Reject unknown fields and non-finite numbers."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class FieldValue(Model):
    label: LocalizedText
    value: CellValue


class SectionBase(Model):
    key: str = Field(min_length=1)
    title: LocalizedText = ""
    enabled: bool = True
    analysis: str | None = None
    page_break_before: bool = False
