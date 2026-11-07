"""CLL Genie rendering consumes authoritative facts prepared by the application."""

from typing import Literal

from pydantic import Field, model_validator

from ..core import Column, FieldValue, Model, TableSection
from ..localization import label, localize_table
from .prepared import PreparedContent, PreparedData, PreparedReport, ReportConfig


class CLLSequence(Model):
    """Supplied IMGT facts; status and productivity are never inferred here."""

    sequence_id: str
    length_nt: int | None = Field(default=None, ge=0)
    identity_percent: float | None = Field(default=None, ge=0, le=100)
    identity_nt: str | None = None
    identity_with_indels: str | None = None
    mutation_status: str
    productivity: str
    subset: str | None = None
    details: list[FieldValue] = Field(default_factory=list)


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
        trailing = [s for s in document.sections if s.key in {"description", "references"}]
        document.sections = [
            s for s in document.sections if s.key not in {"description", "references"}
        ]
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
                        ("productivity", "Produktivitet"),
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
                        ),
                        "status": sequence.mutation_status,
                        "productivity": sequence.productivity,
                        "subset": sequence.subset,
                    }
                    for sequence in self.data.sequences
                ],
            )
            document.sections.insert(0, summary)
            localize_table(summary, self.config.language)
            for index, sequence in enumerate(self.data.sequences):
                details = list(sequence.details)
                if sequence.identity_with_indels is not None:
                    details.insert(
                        0,
                        FieldValue(
                            label=label("V-gen identitet med indels", self.config.language),
                            value=sequence.identity_with_indels,
                        ),
                    )
                document.sections.append(
                    TableSection(
                        key=f"cll-detail-{index}",
                        title=f"{label('Detaljer', self.config.language)} - {sequence.sequence_id}",
                        page_break_before=index == 0,
                        columns=[
                            Column(key="label", label="Parameter"),
                            Column(key="value", label="Resultat"),
                        ],
                        rows=[item.model_dump() for item in details],
                    )
                )
                localize_table(document.sections[-1], self.config.language)
        document.sections.extend(trailing)
        # Validate again after adding generated sections.
        return type(document).model_validate(document.model_dump())
