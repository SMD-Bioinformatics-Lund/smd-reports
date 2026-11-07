"""Shared model primitives for document and application-specific section contracts."""

from pydantic import BaseModel, ConfigDict, Field

Scalar = str | int | float | bool | None


class Model(BaseModel):
    """Reject unknown fields and invalid non-finite numeric values."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class FieldValue(Model):
    """An ordered, caller-labelled metadata or parameter value."""

    label: str
    value: Scalar


class SectionBase(Model):
    """Common layout controls for an ordered section."""

    key: str = Field(min_length=1)
    title: str
    page_break_before: bool = False
