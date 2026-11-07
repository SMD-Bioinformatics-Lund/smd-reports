"""Common input envelope for applications supplying prepared clinical content."""

import json
from importlib.resources import files
from typing import Literal

from pydantic import Field, model_validator

from ..core import (
    Branding,
    ClinicalReport,
    FieldValue,
    Model,
    Provenance,
    Report,
    ReportMetadata,
    ReportSection,
    TextSection,
)
from ..localization import label


class Analysis(Model):
    """One prepared analysis, its parameters, and explicitly selected sections."""

    name: str
    parameters: list[FieldValue] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)


class ReportConfig(Model):
    """Presentation configuration, separate from assay capability and clinical rules."""

    title: str
    language: Literal["sv", "en"] = "sv"
    section_order: list[str] | None = None
    summary_new_page: Literal[True] = True
    header_height_mm: float = Field(default=65, ge=40, le=120)
    footer_height_mm: float = Field(default=38, ge=22, le=50)


class PreparedContent(Model):
    """Prepared clinical content without document identity or branding."""

    supported_analyses: list[str] = Field(default_factory=list)
    enabled_analyses: list[str] = Field(default_factory=list)
    analyses: list[Analysis] = Field(default_factory=list)
    summary: str = ""
    summary_format: Literal["plain", "markdown"] = "plain"
    description: str = ""
    references: str = ""

    @model_validator(mode="after")
    def consistent_analyses(self):
        """Keep capability, selected analyses, and supplied result sets distinct."""
        for values in (self.supported_analyses, self.enabled_analyses):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate analysis names")
        names = [analysis.name for analysis in self.analyses]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate prepared analyses")
        if set(self.enabled_analyses) - set(self.supported_analyses):
            raise ValueError("An enabled analysis is not supported")
        if set(names) - set(self.supported_analyses):
            raise ValueError("Prepared data contains an unsupported analysis")
        if set(self.enabled_analyses) - set(names):
            raise ValueError("Supply a prepared result, even if empty, for enabled analyses")
        return self


class PreparedData(PreparedContent):
    """Python builder inputs combining content with shared document context."""

    metadata: ReportMetadata
    branding: Branding = Field(default_factory=Branding)
    provenance: Provenance = Field(default_factory=Provenance)


class PreparedReport(ClinicalReport):
    """Compose prepared content without applying clinical selection or text rules."""

    application: str

    def __init__(self, data: PreparedData, config: ReportConfig):
        self.data = data.model_copy(deep=True)
        self.config = config.model_copy(deep=True)

    def build(self) -> Report:
        """Validate a fresh document and attach the installed presentation revision."""
        from .. import __version__

        sections = []
        for analysis in self.data.analyses:
            if analysis.name not in self.data.enabled_analyses:
                continue
            sections.extend(section.model_copy(deep=True) for section in analysis.sections)
            if analysis.parameters:
                from ..core import Column, TableSection

                sections.append(
                    TableSection(
                        key=f"parameters-{analysis.name}",
                        title=f"{analysis.name} - {label('parametrar', self.config.language)}",
                        columns=[
                            Column(key="label", label="Parameter"),
                            Column(key="value", label=label("Värde", self.config.language)),
                        ],
                        rows=[item.model_dump() for item in analysis.parameters],
                    )
                )
        if self.config.section_order is not None:
            by_key = {section.key: section for section in sections}
            if (
                len(by_key) != len(sections)
                or len(self.config.section_order) != len(set(self.config.section_order))
                or set(self.config.section_order) != set(by_key)
            ):
                raise ValueError("section_order must name every selected section exactly once")
            sections = [by_key[key] for key in self.config.section_order]
        if self.data.summary:
            sections.append(
                TextSection(
                    key="summary",
                    title=label("Slutsats", self.config.language),
                    text=self.data.summary,
                    format=self.data.summary_format,
                    conclusion=True,
                    page_break_before=self.config.summary_new_page,
                )
            )
        if self.data.description:
            sections.append(
                TextSection(
                    key="description",
                    title=label("Analysbeskrivning", self.config.language),
                    text=self.data.description,
                )
            )
        if self.data.references:
            sections.append(
                TextSection(
                    key="references",
                    title=label("Referenser", self.config.language),
                    text=self.data.references,
                )
            )
        versions = json.loads(files("smd_reports.themes").joinpath("versions.json").read_text())
        analyte = getattr(self.data, "analyte", "")
        revision = versions[self.application].get(
            analyte, versions[self.application].get("default")
        )
        provenance = self.data.provenance.model_copy(
            update={
                "package_version": __version__,
                "template_version": revision,
            }
        )
        return Report(
            header_height_mm=self.config.header_height_mm,
            footer_height_mm=self.config.footer_height_mm,
            application=self.application,
            title=self.config.title,
            language=self.config.language,
            analyte=analyte,
            metadata=self.data.metadata.model_copy(deep=True),
            branding=self.data.branding.model_copy(deep=True),
            provenance=provenance,
            sections=sections,
        )
