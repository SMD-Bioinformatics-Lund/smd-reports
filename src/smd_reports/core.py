"""Report models and section definitions."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from math import isfinite
from string import Formatter
from typing import Annotated, Literal

from pydantic import Field, field_serializer, field_validator, model_validator

from ._models import CellValue, FieldValue, ImageAsset, Language, LocalizedText, Model, SectionBase
from .assets import ImageFormat, validate_image_reference
from .pages import PAGE_SIZES_MM, PageSize


@lru_cache(maxsize=1)
def template_versions():
    """Read and cache the installed template revision registry.

    Returns:
        A mapping of preset names to their template revision strings.
    """
    return json.loads(files("smd_reports").joinpath("themes/versions.json").read_text())


class Branding(Model):
    """Header and footer artwork, contact details, and image dimensions."""

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
        """Validate an optional local or embedded image reference.

        Args:
            value: Image path or data URI, or None to omit the artwork.

        Returns:
            The validated reference or None.

        Raises:
            ValueError: The reference is empty, remote, or contains invalid image data.
        """
        return validate_image_reference(value) if value is not None else None


class Provenance(Model):
    """Application, pipeline, and assay identifiers included with a report."""

    application_name: str = ""
    application_version: str = ""
    pipeline_name: str = ""
    pipeline_version: str = ""
    assay_name: str = ""


class ReportMetadata(Model):
    """Report identity, generation timestamp, and optional reference fields.

    Attributes:
        report_id: Nonempty document identifier.
        sample_id: Optional sample or reference identifier.
        generated_at: Timezone-aware generation timestamp.
        author: Display name of the report creator.
        fields: Additional ordered labels and values.
    """

    report_id: str = Field(min_length=1)
    sample_id: str = ""
    generated_at: datetime
    author: str = ""
    fields: list[FieldValue] = Field(default_factory=list)

    @field_validator("generated_at")
    @classmethod
    def aware_timestamp(cls, value):
        """Require a generation timestamp with a UTC offset.

        Args:
            value: Parsed generation timestamp.

        Returns:
            The timestamp unchanged.

        Raises:
            ValueError: The timestamp has no UTC offset.
        """
        if value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value


class Presentation(Model):
    """Paper dimensions, reserved print areas, and accepted plot formats."""

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
        """The resolved paper width and height in millimetres."""
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
        """Check custom dimensions, available content space, and format choices.

        Returns:
            The validated presentation settings.

        Raises:
            ValueError: Dimensions are incomplete, content cannot fit, or formats repeat.
        """
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
    """A plain-text or Markdown block with an optional translated heading."""

    kind: Literal["text", "summary", "description", "references"] = "text"
    text: LocalizedText
    format: Literal["plain", "markdown"] = "plain"

    @model_validator(mode="before")
    @classmethod
    def default_heading(cls, data):
        """Supply localized headings for the built-in narrative section kinds.

        Args:
            data: Raw section fields or an existing model instance.

        Returns:
            Section fields with a default heading, or the original instance.
        """
        if isinstance(data, dict) and "heading" not in data:
            return {**data, "heading": TEXT_HEADINGS.get(data.get("kind"), "")}
        return data


class ColumnOptions(Model):
    """Optional column widths, text formatting, and detail-card layout settings."""

    width: float = Field(default=1, gt=0)
    format: Literal["plain", "markdown"] = "plain"
    full_width: bool = False
    emphasis: bool = False
    highlight: bool = False


class Column(ColumnOptions):
    """A translated column label combined with its rendering options."""

    label: LocalizedText


class MatrixSection(SectionBase):
    """Column labels grouped by language and equally sized rows of cell values."""

    columns: dict[Language, Annotated[list[str], Field(min_length=1)]] = Field(min_length=1)
    column_options: dict[Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)$")], ColumnOptions] = (
        Field(default_factory=dict)
    )
    rows: list[list[CellValue]] = Field(default_factory=list)
    empty_text: LocalizedText = "Inga rapporterbara resultat"

    @property
    def column_count(self) -> int:
        """The number of labels in each language and values in each row."""
        return len(next(iter(self.columns.values())))

    @property
    def render_columns(self) -> list[Column]:
        """Translated labels combined with options for rendering each column."""
        return [
            Column(
                label={language: labels[index] for language, labels in self.columns.items()},
                **self.column_options.get(str(index), ColumnOptions()).model_dump(),
            )
            for index in range(self.column_count)
        ]

    @field_serializer("column_options")
    def serialize_column_options(self, value: dict[str, ColumnOptions]) -> dict[str, dict]:
        """Serialize column options without repeating their default values.

        Args:
            value: Column options indexed by zero-based column position.

        Returns:
            The same indexes with only nondefault formatting settings.
        """
        return {
            index: options.model_dump(exclude_defaults=True) for index, options in value.items()
        }

    @model_validator(mode="after")
    def rectangular_rows(self):
        """Validate translated label counts, formatting indexes, and row lengths.

        Returns:
            The validated matrix section.

        Raises:
            ValueError: Label counts differ, a formatting index is invalid, a row
                has the wrong length, or the total width is not finite.
        """
        if any(len(labels) != self.column_count for labels in self.columns.values()):
            raise ValueError("Column labels must have the same count in every language")
        if any(int(index) >= self.column_count for index in self.column_options):
            raise ValueError("Column options reference an undeclared column")
        if not isfinite(sum(column.width for column in self.render_columns)):
            raise ValueError("The total column width must be finite")
        if any(len(row) != self.column_count for row in self.rows):
            raise ValueError("Every row must contain exactly one value per declared column")
        return self


class TableSection(MatrixSection):
    """A result table whose headers are declared once for all rows."""

    kind: Literal["table"] = "table"


def validate_heading(pattern: LocalizedText | None, columns: int):
    """Check a record-heading format without permitting attribute access.

    Args:
        pattern: Literal or translated format text, or None for the default heading.
        columns: Number of available positional values.

    Raises:
        ValueError: A placeholder is unsafe, malformed, or outside the column range.
    """
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
    """Shared row matrices and per-record heading options for finding cards."""

    record_heading: LocalizedText | None = None
    record_titles: list[LocalizedText] | None = None

    @model_validator(mode="after")
    def valid_headings(self):
        """Validate positional headings and explicit record-title counts.

        Returns:
            The validated record section.

        Raises:
            ValueError: A heading is invalid or record titles do not match the rows.
        """
        validate_heading(self.record_heading, self.column_count)
        if self.record_titles is not None and len(self.record_titles) != len(self.rows):
            raise ValueError("record_titles must have one title per row")
        return self


class DetailSection(RecordSection):
    """Finding cards with compact label/value pairs and full-width text rows."""

    kind: Literal["details"] = "details"
    fields_per_row: int = Field(default=3, ge=1, le=6)
    full_width_last: bool = False


class GridCell(Model):
    """A column reference and its placement within a grouped detail grid."""

    column: int = Field(ge=0)
    mode: Literal["pair", "inline", "value", "label"] = "pair"
    span: int = Field(default=2, ge=1)
    label_span: int = Field(default=1, ge=1)
    label: LocalizedText | None = None

    @model_validator(mode="after")
    def valid_span(self):
        """Reserve enough grid columns for both parts of a label/value pair.

        Returns:
            The validated grid cell.

        Raises:
            ValueError: A pair leaves no room for its value.
        """
        if self.mode == "pair" and self.label_span >= self.span:
            raise ValueError("A pair needs space for both its label and value")
        return self


class GridRow(Model):
    """An ordered group of grid cells with optional empty-row suppression."""

    cells: list[GridCell] = Field(min_length=1)
    hide_if_empty: bool = False


class GridSection(RecordSection):
    """Repeated finding grids arranged using JSON-defined column spans."""

    kind: Literal["grid"] = "grid"
    grid_columns: int = Field(default=5, ge=1, le=24)
    layout: list[GridRow] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_layout(self):
        """Check that grid rows fit and reference existing data columns.

        Returns:
            The validated grid section.

        Raises:
            ValueError: Row spans do not fit or a referenced column is missing.
        """
        for row in self.layout:
            if sum(cell.span for cell in row.cells) != self.grid_columns:
                raise ValueError("Each layout row must fill grid_columns exactly")
            if any(cell.column >= self.column_count for cell in row.cells):
                raise ValueError("A grid cell references an undeclared column")
        return self


class ImageSection(SectionBase, ImageAsset):
    """A standalone plot with a heading, caption, and page-break controls."""

    kind: Literal["image"] = "image"


ReportSection = Annotated[
    TextSection | TableSection | DetailSection | GridSection | ImageSection,
    Field(discriminator="kind"),
]


class Report(Model):
    """A validated JSON report with a neutral default presentation.

    Attributes:
        application: Optional preset identity; defaults to generic.
        title: Literal or translated document title.
        language: Language used for interface labels and translations.
        report: Document identity and metadata fields.
        branding: Header and footer configuration.
        provenance: Application, pipeline, and assay context.
        presentation: Paper dimensions and image-format settings.
        sections: Ordered report contents.
    """

    application: Literal["generic", "coyote3", "genexus", "cll_genie", "pgx"] = "generic"
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
        """The document identity and optional user-defined metadata fields."""
        return self.report

    @property
    def header_height_mm(self):
        """The vertical space reserved for the repeating header, in millimetres."""
        return self.presentation.header_height_mm

    @property
    def footer_height_mm(self):
        """The configured accreditation-footer height, in millimetres."""
        return self.presentation.footer_height_mm

    @property
    def template_name(self):
        """The template display name, including the Coyote3 DNA or RNA variant."""
        name = {
            "generic": "Rapport",
            "coyote3": "Coyote3",
            "genexus": "Genexus",
            "cll_genie": "CLL Genie",
            "pgx": "PGx",
        }[self.application]
        if self.application == "coyote3" and self.analyte in {"dna", "rna"}:
            return f"{name} {self.analyte.upper()}"
        return name

    @property
    def template_version(self):
        """The installed template revision for the selected preset and analyte."""
        revisions = template_versions()[self.application]
        return revisions.get(self.analyte, revisions.get("default", next(iter(revisions.values()))))

    @property
    def rendering_metadata(self):
        """The supplied context and automatically computed package/template versions."""
        from . import __version__

        return {
            **{key: value for key, value in self.provenance.model_dump().items() if value},
            "package_name": "smd-reports",
            "package_version": __version__,
            "template_version": self.template_version,
        }

    @property
    def image_height_limit_mm(self):
        """The image-height limit after reserving headers, footers, and captions."""
        footer = (
            self.footer_height_mm
            if (self.branding.accredited and self.branding.accreditation_logo)
            else 22
        )
        return self.presentation.dimensions_mm[1] - self.header_height_mm - footer - 20

    @model_validator(mode="after")
    def valid_sections(self):
        """Require unique section identifiers within the document.

        Returns:
            The validated report.

        Raises:
            ValueError: Two sections share the same key.
        """
        keys = [section.key for section in self.sections]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate section keys")
        return self
