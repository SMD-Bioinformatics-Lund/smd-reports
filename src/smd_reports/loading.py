"""Application-owned JSON input contracts and portable normalized report loading."""

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator

from .assets import embed_image
from .core import Branding, Model, Provenance, Report, ReportMetadata
from .plugins.cll_genie import CLLGenieContent, CLLGenieData, CLLGenieReport
from .plugins.coyote import CoyoteContent, CoyoteData, CoyoteReport
from .plugins.genexus import GenexusContent, GenexusData, GenexusReport
from .plugins.pgx import PGxContent, PGxData, PGxReport
from .plugins.prepared import ReportConfig


class InputBranding(Branding):
    """JSON artwork may be an embedded data URI or a local file path."""

    @field_validator("application_logo", "center_logo", "accreditation_logo")
    @classmethod
    def embedded_image(cls, value: str | None) -> str | None:
        """Defer local path loading until the complete input has been validated."""
        if value is None or value.startswith("data:"):
            return Branding.embedded_image(value)
        if not value.strip() or ":" in value or "\x00" in value:
            raise ValueError("Artwork must be a local path or embedded data URI")
        return value


class Presentation(Model):
    """Print controls kept separate from language, document identity and content."""

    section_order: list[str] | None = None
    summary_new_page: Literal[True] = True
    header_height_mm: float = Field(default=65, ge=40, le=120)
    footer_height_mm: float = Field(default=38, ge=22, le=50)


class InputBase(Model):
    """Shared JSON envelope; clinical payloads are typed by application."""

    schema_version: Literal[1]
    title: str = Field(min_length=1)
    language: Literal["sv", "en"] = "sv"
    report: ReportMetadata
    branding: InputBranding = Field(default_factory=InputBranding)
    provenance: Provenance = Field(default_factory=Provenance)
    presentation: Presentation = Field(default_factory=Presentation)


class CoyoteInput(InputBase):
    """Coyote3 JSON schema."""

    application: Literal["coyote3"]
    data: CoyoteContent


class GenexusInput(InputBase):
    """Genexus JSON schema."""

    application: Literal["genexus"]
    data: GenexusContent


class CLLGenieInput(InputBase):
    """CLL Genie JSON schema."""

    application: Literal["cll_genie"]
    data: CLLGenieContent


class PGxInput(InputBase):
    """PGx JSON schema; clinical input preparation remains available separately."""

    application: Literal["pgx"]
    data: PGxContent


INPUT_MODELS = {
    "coyote3": CoyoteInput,
    "genexus": GenexusInput,
    "cll_genie": CLLGenieInput,
    "pgx": PGxInput,
}
BUILDERS = {
    "coyote3": (CoyoteData, CoyoteReport),
    "genexus": (GenexusData, GenexusReport),
    "cll_genie": (CLLGenieData, CLLGenieReport),
    "pgx": (PGxData, PGxReport),
}
INPUT = TypeAdapter(
    Annotated[
        CoyoteInput | GenexusInput | CLLGenieInput | PGxInput, Field(discriminator="application")
    ]
)


def unique_object(pairs):
    """Reject duplicate JSON keys rather than silently replacing clinical values."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    """Reject JSON NaN/Infinity extensions."""
    raise ValueError("Non-finite JSON numbers are prohibited")


class ReportAssetError(ValueError):
    """A named branding field could not be loaded, without exposing its path or content."""

    def __init__(self, field):
        super().__init__(f"Cannot load branding.{field}; supply valid local or embedded artwork")


class ReportLoader:
    """Load application JSON or a normalized document snapshot without network access."""

    def load(self, path: str | Path) -> Report:
        """Resolve logos relative to the input file, then build a validated document.

        Normalized snapshots contain embedded assets and load directly. Input JSON
        requires the application discriminator and its corresponding typed payload.
        Filesystem, JSON and model errors are propagated to Python callers.
        """
        path = Path(path)
        raw = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        if isinstance(raw, dict) and "sections" in raw:
            return Report.model_validate(raw)
        envelope = INPUT.validate_python(raw)
        branding = envelope.branding.model_dump()
        for key in ("application_logo", "center_logo", "accreditation_logo"):
            value = branding[key]
            if value is not None and not value.startswith("data:"):
                source = Path(value)
                try:
                    branding[key] = embed_image(
                        source if source.is_absolute() else path.parent / source
                    )
                except (OSError, ValueError) as exc:
                    raise ReportAssetError(key) from exc
        data_model, builder = BUILDERS[envelope.application]
        data = data_model.model_validate(
            {
                **envelope.data.model_dump(),
                "metadata": envelope.report.model_dump(),
                "branding": branding,
                "provenance": envelope.provenance.model_dump(),
            }
        )
        config = ReportConfig(
            title=envelope.title, language=envelope.language, **envelope.presentation.model_dump()
        )
        return builder(data, config).build()

    def schema(self, application: str) -> dict:
        """Export an application's JSON Schema without reading any report data."""
        if application not in INPUT_MODELS:
            raise ValueError("Unknown application")
        return INPUT_MODELS[application].model_json_schema()
