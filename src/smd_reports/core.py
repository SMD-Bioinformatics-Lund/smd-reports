"""Typed document contracts, independent of clinical workflows and storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Scalar = str | int | float | bool | None


class Model(BaseModel):
    """Reject unknown fields and invalid non-finite numeric values."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class FieldValue(Model):
    """An ordered, caller-labelled metadata or parameter value."""

    label: str
    value: Scalar


class Branding(Model):
    """Embedded branding; callers decide whether an assay is accredited."""

    organization: str = ""
    department: str = ""
    address: str = ""
    telephone: str = ""
    email: str = ""
    website: str = ""
    application_logo: str | None = None
    center_logo: str | None = None
    accreditation_logo: str | None = None
    accredited: bool = False
    center_logo_width_mm: float = Field(default=11.64, ge=5, le=35)
    application_logo_width_mm: float = Field(default=13.75, ge=5, le=30)
    accreditation_logo_width_mm: float = Field(default=25, ge=10, le=35)
    accreditation_label: str = "Ackreditering"

    @field_validator("application_logo", "center_logo", "accreditation_logo")
    @classmethod
    def embedded_image(cls, value: str | None) -> str | None:
        """Validate embedded artwork without accepting active SVG or external resources."""
        if value is not None:
            from .assets import validate_image

            validate_image(value)
        return value

    @classmethod
    def from_files(
        cls, *, center_logo=None, application_logo=None, accreditation_logo=None, **information
    ):
        """Embed explicit local logo paths alongside validated center information.

        Paths are read once; reports remain independent of host paths after creation.
        Accreditation eligibility must still be supplied by the application.
        """
        from .assets import embed_image

        logos = {
            key: embed_image(path) if path is not None else None
            for key, path in {
                "center_logo": center_logo,
                "application_logo": application_logo,
                "accreditation_logo": accreditation_logo,
            }.items()
        }
        return cls(**information, **logos)


class Provenance(Model):
    """Caller-owned generation context plus versioned reporting identities."""

    application_version: str = ""
    configuration_version: str = ""
    assay_version: str = ""
    source_revision: str = ""
    package_version: str = "0.1.0"
    plugin_version: str = "1.0.0"
    schema_version: Literal[1] = 1
    template_version: str = "1.0.0"


class ReportMetadata(Model):
    """Report identity and ordered patient/sample fields supplied by the host."""

    report_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    generated_at: datetime
    author: str = ""
    fields: list[FieldValue] = Field(default_factory=list)

    @field_validator("generated_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        """Require an explicit timezone rather than guessing the host timezone."""
        if value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value


class SectionBase(Model):
    """Common layout controls for an ordered section."""

    key: str = Field(min_length=1)
    title: str
    page_break_before: bool = False


class TextSection(SectionBase):
    """Plain text or sanitized Markdown, optionally styled as a conclusion."""

    kind: Literal["text"] = "text"
    text: str
    format: Literal["plain", "markdown"] = "plain"
    conclusion: bool = False


class Column(Model):
    """A declared table column; values are already prepared for reporting."""

    key: str
    label: str


class TableSection(SectionBase):
    """Explicit columns and scalar rows; no clinical inference is performed."""

    kind: Literal["table"] = "table"
    columns: list[Column] = Field(min_length=1)
    rows: list[dict[str, Scalar]] = Field(default_factory=list)
    empty_text: str = "Inga rapporterbara resultat"
    emphasis_column: str | None = None
    emphasis_value: Scalar = None

    @model_validator(mode="after")
    def valid_columns(self) -> TableSection:
        """Reject duplicate columns and accidentally discarded row fields."""
        keys = [column.key for column in self.columns]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate table columns")
        if any(set(row) - set(keys) for row in self.rows):
            raise ValueError("A row contains undeclared columns")
        if self.emphasis_column is not None and self.emphasis_column not in keys:
            raise ValueError("Unknown emphasis column")
        return self


class ImageSection(SectionBase):
    """An embedded plot prepared by the application."""

    kind: Literal["image"] = "image"
    source: str
    caption: str = ""

    @field_validator("source")
    @classmethod
    def embedded_source(cls, value: str) -> str:
        Branding.embedded_image(value)
        return value


ReportSection = Annotated[TextSection | TableSection | ImageSection, Field(discriminator="kind")]


class Report(Model):
    """Validated, serializable document produced by an application report builder."""

    schema_version: Literal[1] = 1
    application: Literal["coyote3", "genexus", "cll_genie", "pgx"]
    title: str
    language: Literal["sv", "en"] = "sv"
    analyte: str = ""
    header_height_mm: float = Field(default=65, ge=40, le=120)
    footer_height_mm: float = Field(default=38, ge=22, le=50)
    metadata: ReportMetadata
    branding: Branding = Field(default_factory=Branding)
    provenance: Provenance = Field(default_factory=Provenance)
    sections: list[ReportSection] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_sections(self) -> Report:
        """Require stable, unique section identifiers."""
        keys = [section.key for section in self.sections]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate section keys")
        return self


class ClinicalReport(ABC):
    """Base builder; rendering is delegated to a replaceable renderer instance."""

    @abstractmethod
    def build(self) -> Report:
        """Build the document from validated application data."""
        raise NotImplementedError

    def render_html(self, *, renderer=None) -> str:
        """Render the built document using the supplied or default renderer."""
        from .rendering import ReportRenderer

        return (renderer or ReportRenderer()).render_html(self.build())

    def render_pdf(self, *, renderer=None) -> bytes:
        """Return PDF bytes without persisting a clinical artifact."""
        from .rendering import ReportRenderer

        return (renderer or ReportRenderer()).render_pdf(self.build())
