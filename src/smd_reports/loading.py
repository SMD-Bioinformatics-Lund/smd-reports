"""Read report JSON and embed local artwork."""

import json
from importlib.resources import files
from pathlib import Path

from .assets import embed_image
from .core import Report

APPLICATIONS = ("coyote3", "genexus", "cll_genie", "pgx")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Non-finite JSON numbers are prohibited")


class ReportAssetError(ValueError):
    def __init__(self, field):
        super().__init__(f"Cannot load {field}; supply valid local or embedded artwork")


class ReportLoader:
    """Load a JSON file or JSON text into a validated document."""

    def load(self, path: str | Path) -> Report:
        path = Path(path)
        return self.loads(path.read_text(encoding="utf-8-sig"), base_dir=path.parent)

    def loads(self, source: str | bytes, *, base_dir: str | Path | None = None) -> Report:
        if not isinstance(source, (str, bytes)):
            raise TypeError("Supply JSON text or bytes")
        document = Report.model_validate(
            json.loads(
                source,
                object_pairs_hook=unique_object,
                parse_constant=reject_constant,
            )
        )

        def image(value, field):
            if value is None or value.startswith("data:"):
                return value
            try:
                path = Path(value)
                if not path.is_absolute():
                    if base_dir is None:
                        raise ValueError("Relative artwork requires base_dir")
                    path = Path(base_dir) / path
                return embed_image(path)
            except (OSError, ValueError) as exc:
                raise ReportAssetError(field) from exc

        for key in ("application_logo", "center_logo", "accreditation_logo"):
            setattr(
                document.branding, key, image(getattr(document.branding, key), f"branding.{key}")
            )
        for section in document.sections:
            if section.kind == "image":
                section.source = image(section.source, f"sections.{section.key}.source")
        from . import __version__

        versions = json.loads(files("smd_reports.themes").joinpath("versions.json").read_text())
        revisions = versions[document.application]
        document.provenance.package_version = __version__
        document.provenance.template_version = revisions.get(
            document.analyte, revisions.get("default", next(iter(revisions.values())))
        )
        return document

    def schema(self, application: str | None = None) -> dict:
        if application is not None and application not in APPLICATIONS:
            raise ValueError("Unknown application")
        result = Report.model_json_schema()
        if application is not None:
            result["properties"]["application"] = {"type": "string", "const": application}
        return result
