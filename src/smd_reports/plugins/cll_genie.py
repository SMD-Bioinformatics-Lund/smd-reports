"""CLL Genie rendering consumes authoritative facts prepared by the application."""

from typing import Literal

from pydantic import Field, model_validator

from ..core import Column, FieldValue, TableSection
from ..localization import label, localize_table
from ..sequence import CLLSequence, CLLSequenceSection
from .prepared import PreparedContent, PreparedData, PreparedReport, ReportConfig


class CLLGenieContent(PreparedContent):
    """Reviewed positive or no-result report and its submission context."""

    report_type: Literal["positive", "nonfunctional", "no_clone"]
    submission_id: str | None = None
    sequences: list[CLLSequence] = Field(default_factory=list)

    @model_validator(mode="after")
    def report_context(self):
        """Require a reviewed conclusion and preserve distinct no-result cases."""
        if not self.summary.strip():
            raise ValueError("A reviewed summary is required")
        if self.report_type == "positive" and (not self.submission_id or not self.sequences):
            raise ValueError("Positive reports require submission identity and sequence results")
        if self.report_type != "positive" and self.sequences:
            raise ValueError("No-result reports must not contain positive sequence tables")
        ids = [sequence.sequence_id for sequence in self.sequences]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate sequence identifiers")
        return self


class CLLGenieData(CLLGenieContent, PreparedData):
    """CLL content with shared Python document inputs."""


class CLLGenieReport(PreparedReport):
    """Build shared-format IGHV reports from reviewed CLL Genie facts."""

    application = "cll_genie"

    def __init__(self, data: CLLGenieData, config: ReportConfig):
        super().__init__(data, config)

    def build(self):
        document = super().build()
        trailing_keys = {"description", "references"} | {
            s.key for s in self.data.supporting_sections
        }
        trailing = [s for s in document.sections if s.key in trailing_keys]
        document.sections = [s for s in document.sections if s.key not in trailing_keys]
        document.metadata.fields.append(
            FieldValue(
                label=label("Rapporttyp", self.config.language),
                value=label(
                    {
                        "positive": "Positiv",
                        "nonfunctional": "Klonal, icke-funktionell sekvens",
                        "no_clone": "Ingen klonal sekvens detekterad",
                    }[self.data.report_type],
                    self.config.language,
                ),
            )
        )
        if self.data.submission_id:
            document.metadata.fields.append(
                FieldValue(
                    label="Submission",
                    value=self.data.submission_id,
                )
            )
        if self.data.sequences:
            summary = TableSection(
                key="cll-sequences",
                title="Analysresultat",
                columns=[
                    Column(key=key, label=label)
                    for key, label in (
                        ("id", "Sekvens-ID"),
                        ("length", "Sekvenslängd"),
                        ("identity", "V-gen identitet"),
                        ("status", "IGHV-mutationsstatus"),
                        ("subset", "CLL subset"),
                    )
                ],
                rows=[
                    {
                        "id": sequence.sequence_id,
                        "length": sequence.length_nt,
                        "identity": (
                            None
                            if sequence.identity_percent is None
                            else f"{sequence.identity_percent}%"
                            + (f" ({sequence.identity_nt})" if sequence.identity_nt else "")
                            + (
                                f" [{sequence.identity_with_indels}]"
                                if sequence.identity_with_indels
                                else ""
                            )
                        ),
                        "status": sequence.mutation_status,
                        "subset": sequence.subset,
                    }
                    for sequence in self.data.sequences
                ],
            )
            document.sections.insert(0, summary)
            localize_table(summary, self.config.language)
            for index, sequence in enumerate(self.data.sequences):
                document.sections.append(
                    CLLSequenceSection(
                        key=f"cll-detail-{index}",
                        title=label("Detaljerade analysresultat", self.config.language)
                        if index == 0
                        else "",
                        sequences=[sequence.model_copy(deep=True)],
                    )
                )
        document.sections.extend(trailing)
        # Validate again after adding generated sections.
        return type(document).model_validate(document.model_dump())
