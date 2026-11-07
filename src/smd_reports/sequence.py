"""Prepared sequence facts and the dedicated CLL Genie report section."""

from typing import Literal

from pydantic import Field, model_validator

from ._models import FieldValue, Model, Scalar, SectionBase


class CLLSequence(Model):
    """Reviewed IMGT and read-count facts; no status or productivity inference."""

    sequence_id: str = Field(min_length=1)
    length_nt: int | None = Field(default=None, ge=0)
    identity_percent: float | None = Field(default=None, ge=0, le=100)
    identity_nt: str | None = None
    identity_with_indels: str | None = None
    mutation_status: str
    productivity: str
    subset: str | None = None
    analysis_category: str | None = None
    indel_summary: str | None = None
    functionality_label: str = "V-Domain functionality"
    functionality_comment: str | None = None
    v_gene: str | None = None
    v_score: Scalar = None
    j_gene: str | None = None
    j_score: Scalar = None
    j_identity_percent: float | None = Field(default=None, ge=0, le=100)
    j_identity_nt: str | None = None
    d_gene: str | None = None
    d_reading_frame: Scalar = None
    fr_lengths: str | None = None
    cdr_lengths: str | None = None
    aa_junction: str | None = None
    junction_length_nt: int | None = Field(default=None, ge=0)
    junction_decryption: str | None = None
    junction_legend: str | None = None
    merge_count: int | None = Field(default=None, ge=0)
    total_reads_percent: float | None = Field(default=None, ge=0, le=100)
    details: list[FieldValue] = Field(default_factory=list)


class CLLSequenceSection(SectionBase):
    """Original grouped sequence layout, independent of generic finding cards."""

    kind: Literal["cll_sequences"] = "cll_sequences"
    sequences: list[CLLSequence] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_sequences(self):
        keys = [sequence.sequence_id for sequence in self.sequences]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate sequence identifiers")
        return self
