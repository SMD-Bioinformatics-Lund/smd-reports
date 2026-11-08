"""Validated JSON document and reusable presentation sections."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from math import isfinite
from string import Formatter
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from ._models import CellValue, FieldValue, ImageAsset, Language, LocalizedText, Model, SectionBase
from .assets import ImageFormat, validate_image_reference
from .pages import PAGE_SIZES_MM, PageSize


@lru_cache(maxsize=1)
def template_versions():
    return json.loads(files("smd_reports").joinpath("themes/versions.json").read_text())


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
        return validate_image_reference(value) if value is not None else None


class Provenance(Model):
    application_name: str = ""
    application_version: str = ""
    pipeline_name: str = ""
    pipeline_version: str = ""
    assay_name: str = ""


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
    page_size: PageSize = "A4"
    orientation: Literal["portrait", "landscape"] | None = None
    custom_width_mm: float | None = Field(default=None, gt=0)
    custom_height_mm: float | None = Field(default=None, gt=0)
    header_height_mm: float = Field(default=65, ge=40, le=120)
    footer_height_mm: float = Field(default=38, ge=22, le=50)
    accepted_image_formats: list[ImageFormat] = Field(
        default_factory=lambda: ["png", "jpeg", "svg", "webp", "gif", "tiff", "bmp"],
        min_length=1,
    )

    @property
    def dimensions_mm(self):
        width, height = (
            (self.custom_width_mm, self.custom_height_mm)
            if self.page_size == "custom"
            else PAGE_SIZES_MM[self.page_size]
        )
        if self.orientation == "portrait":
            return min(width, height), max(width, height)
        if self.orientation == "landscape":
            return max(width, height), min(width, height)
        return width, height

    @model_validator(mode="after")
    def valid_page(self):
        if self.page_size == "custom":
            if self.custom_width_mm is None or self.custom_height_mm is None:
                raise ValueError("Custom pages require custom_width_mm and custom_height_mm")
        elif self.custom_width_mm is not None or self.custom_height_mm is not None:
            raise ValueError("Custom dimensions require page_size custom")
        width, height = self.dimensions_mm
        if width <= 52 or height <= self.header_height_mm + self.footer_height_mm + 20:
            raise ValueError("Page dimensions must leave room for margins, headers and content")
        if len(set(self.accepted_image_formats)) != len(self.accepted_image_formats):
            raise ValueError("Duplicate accepted image formats")
        return self


TEXT_HEADINGS = {
    "summary": {"en": "Conclusion", "sv": "Slutsats"},
    "description": {"en": "Analysis description", "sv": "Analysbeskrivning"},
    "references": {"en": "References", "sv": "Referenser"},
}


class TextSection(SectionBase):
    kind: Literal["text", "summary", "description", "references"] = "text"
    text: LocalizedText
    format: Literal["plain", "markdown"] = "plain"

    @model_validator(mode="before")
    @classmethod
    def default_heading(cls, data):
        if isinstance(data, dict) and "heading" not in data:
            return {**data, "heading": TEXT_HEADINGS.get(data.get("kind"), "")}
        return data


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


class ImageSection(SectionBase, ImageAsset):
    kind: Literal["image"] = "image"


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
    def template_version(self):
        revisions = template_versions()[self.application]
        return revisions.get(self.analyte, revisions.get("default", next(iter(revisions.values()))))

    @property
    def rendering_metadata(self):
        from . import __version__

        return {
            **{key: value for key, value in self.provenance.model_dump().items() if value},
            "package_name": "smd-reports",
            "package_version": __version__,
            "template_version": self.template_version,
        }

    @property
    def image_height_limit_mm(self):
        footer = (
            self.footer_height_mm
            if (self.branding.accredited and self.branding.accreditation_logo)
            else 22
        )
        return self.presentation.dimensions_mm[1] - self.header_height_mm - footer - 20

    @model_validator(mode="after")
    def valid_sections(self):
        keys = [section.key for section in self.sections]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate section keys")
        return self
