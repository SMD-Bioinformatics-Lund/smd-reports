"""Validated JSON document and reusable presentation sections."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from pathlib import Path
from string import Formatter
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from ._models import CellValue, FieldValue, Language, LocalizedText, Model, SectionBase


class Branding(Model):
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
    accreditation_label: LocalizedText = "Ackreditering"

    @field_validator("application_logo", "center_logo", "accreditation_logo")
    @classmethod
    def image_reference(cls, value):
        if value is None:
            return value
        if value.startswith("data:"):
            from .assets import validate_image

            validate_image(value)
        elif (
            not value.strip() or (":" in value and not Path(value).is_absolute()) or "\x00" in value
        ):
            raise ValueError("Use a local image path or embedded image data URI")
        return value


class Provenance(Model):
    application_version: str = ""
    configuration_version: str = ""
    assay_version: str = ""
    source_revision: str = ""
    package_version: str = ""
    template_version: str = ""


class ReportMetadata(Model):
    report_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    generated_at: datetime
    author: str = ""
    fields: list[FieldValue] = Field(default_factory=list)

    @field_validator("generated_at")
    @classmethod
    def aware_timestamp(cls, value):
        if value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value


class Presentation(Model):
    header_height_mm: float = Field(default=65, ge=40, le=120)
    footer_height_mm: float = Field(default=38, ge=22, le=50)


class TextSection(SectionBase):
    kind: Literal["text"] = "text"
    text: LocalizedText
    format: Literal["plain", "markdown"] = "plain"
    conclusion: bool = False


class Column(Model):
    label: LocalizedText
    width: float = Field(default=1, gt=0)
    format: Literal["plain", "markdown"] = "plain"
    full_width: bool = False
    emphasis: bool = False
    highlight: bool = False


class MatrixSection(SectionBase):
    columns: list[Column] = Field(min_length=1)
    rows: list[list[CellValue]] = Field(default_factory=list)
    empty_text: LocalizedText = "Inga rapporterbara resultat"

    @model_validator(mode="after")
    def rectangular_rows(self):
        if not isfinite(sum(column.width for column in self.columns)):
            raise ValueError("The total column width must be finite")
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("Every row must contain exactly one value per declared column")
        return self


class TableSection(MatrixSection):
    kind: Literal["table"] = "table"


def validate_heading(pattern: LocalizedText | None, columns: int):
    if pattern is None:
        return
    for text in [pattern] if isinstance(pattern, str) else pattern.values():
        for _, name, spec, conversion in Formatter().parse(text):
            if name is not None and (
                not name.isascii()
                or not name.isdigit()
                or int(name) >= columns
                or spec
                or conversion
            ):
                raise ValueError("Headings accept only column indexes such as {0} or {1}")


class RecordSection(MatrixSection):
    record_heading: LocalizedText | None = None
    record_titles: list[LocalizedText] | None = None

    @model_validator(mode="after")
    def valid_headings(self):
        validate_heading(self.record_heading, len(self.columns))
        if self.record_titles is not None and len(self.record_titles) != len(self.rows):
            raise ValueError("record_titles must have one title per row")
        return self


class DetailSection(RecordSection):
    kind: Literal["details"] = "details"
    fields_per_row: int = Field(default=3, ge=1, le=6)
    full_width_last: bool = False


class GridCell(Model):
    column: int = Field(ge=0)
    mode: Literal["pair", "inline", "value", "label"] = "pair"
    span: int = Field(default=2, ge=1)
    label_span: int = Field(default=1, ge=1)
    label: LocalizedText | None = None

    @model_validator(mode="after")
    def valid_span(self):
        if self.mode == "pair" and self.label_span >= self.span:
            raise ValueError("A pair needs space for both its label and value")
        return self


class GridRow(Model):
    cells: list[GridCell] = Field(min_length=1)
    hide_if_empty: bool = False


class GridSection(RecordSection):
    kind: Literal["grid"] = "grid"
    grid_columns: int = Field(default=5, ge=1, le=24)
    layout: list[GridRow] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_layout(self):
        for row in self.layout:
            if sum(cell.span for cell in row.cells) != self.grid_columns:
                raise ValueError("Each layout row must fill grid_columns exactly")
            if any(cell.column >= len(self.columns) for cell in row.cells):
                raise ValueError("A grid cell references an undeclared column")
        return self


class ImageSection(SectionBase):
    kind: Literal["image"] = "image"
    source: str
    caption: LocalizedText = ""

    @field_validator("source")
    @classmethod
    def image_reference(cls, value):
        Branding.image_reference(value)
        return value


ReportSection = Annotated[
    TextSection | TableSection | DetailSection | GridSection | ImageSection,
    Field(discriminator="kind"),
]


class Report(Model):
    application: Literal["coyote3", "genexus", "cll_genie", "pgx"]
    title: LocalizedText
    language: Language = "sv"
    analyte: str = ""
    report: ReportMetadata
    branding: Branding = Field(default_factory=Branding)
    provenance: Provenance = Field(default_factory=Provenance)
    presentation: Presentation = Field(default_factory=Presentation)
    supported_analyses: list[str] | None = None
    enabled_analyses: list[str] | None = None
    sections: list[ReportSection] = Field(default_factory=list)

    @property
    def metadata(self):
        return self.report

    @property
    def header_height_mm(self):
        return self.presentation.header_height_mm

    @property
    def footer_height_mm(self):
        return self.presentation.footer_height_mm

    @property
    def visible_sections(self):
        return [
            section
            for section in self.sections
            if section.enabled
            and (
                section.analysis is None
                or self.enabled_analyses is None
                or section.analysis in self.enabled_analyses
            )
        ]

    @model_validator(mode="after")
    def valid_sections(self):
        keys = [section.key for section in self.sections]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate section keys")
        for names in [self.supported_analyses, self.enabled_analyses]:
            if names is not None and len(names) != len(set(names)):
                raise ValueError("Duplicate analysis names")
        if self.supported_analyses is not None:
            requested = set(self.enabled_analyses or []) | {
                s.analysis for s in self.sections if s.analysis is not None
            }
            if requested - set(self.supported_analyses):
                raise ValueError("An analysis is not in supported_analyses")
        return self
