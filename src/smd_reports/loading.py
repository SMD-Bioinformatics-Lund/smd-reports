"""Read report JSON and embed local artwork."""

import json
from pathlib import Path

from .assets import embed_image, prepare_image
from .core import Report

APPLICATIONS = ("generic", "coyote3", "genexus", "cll_genie", "pgx")


def unique_object(pairs):
    """Build a JSON object while detecting duplicate keys.

    Args:
        pairs: Key/value pairs emitted by the JSON decoder.

    Returns:
        A dictionary containing the decoded members.

    Raises:
        ValueError: A key occurs more than once.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    """Reject nonstandard JSON numeric constants.

    Args:
        value: The NaN or Infinity token encountered by the decoder.

    Raises:
        ValueError: Always, because the token is not a finite JSON number.
    """
    raise ValueError("Non-finite JSON numbers are prohibited")


class ReportAssetError(ValueError):
    """An image-loading error identified by its JSON field name."""

    def __init__(self, field):
        """Initialize an asset error without exposing image bytes or file paths.

        Args:
            field: Dotted JSON field name for the image that could not be loaded.
        """
        super().__init__(f"Cannot load {field}; supply valid local or embedded artwork")


class ReportLoader:
    """Load a JSON file or JSON text into a validated document."""

    def load(self, path: str | Path) -> Report:
        """Read a JSON file and embed its referenced artwork.

        Args:
            path: Path to the UTF-8 JSON document. Relative artwork paths resolve
                against this file's parent directory.

        Returns:
            A validated report with embedded artwork.

        Raises:
            OSError: The JSON file cannot be read.
            ValueError: JSON syntax, numeric constants, or object keys are invalid.
            pydantic.ValidationError: Document fields do not match the input format.
            ReportAssetError: Referenced artwork cannot be loaded.
        """
        path = Path(path)
        return self.loads(path.read_text(encoding="utf-8-sig"), base_dir=path.parent)

    def loads(self, source: str | bytes, *, base_dir: str | Path | None = None) -> Report:
        """Validate JSON text or bytes and embed referenced images.

        Args:
            source: JSON text or UTF-8 bytes.
            base_dir: Directory for relative image paths. Omit it when artwork
                is already embedded or uses absolute paths.

        Returns:
            A validated report with its original section order.

        Raises:
            TypeError: The source is neither text nor bytes.
            ValueError: JSON syntax, numeric constants, or object keys are invalid.
            pydantic.ValidationError: Report fields fail validation.
            ReportAssetError: An image, frame, or accepted format is invalid.
        """
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
            assets = section.images + ([section] if section.kind == "image" else [])
            for index, asset in enumerate(assets):
                field = f"sections.{section.key}.images.{index}"
                asset.source = image(asset.source, field)
                try:
                    prepare_image(
                        asset.source,
                        frame=asset.frame,
                        accepted_formats=document.presentation.accepted_image_formats,
                    )
                except (OSError, ValueError) as exc:
                    raise ReportAssetError(field) from exc
        return document

    def schema(self, application: str | None = None) -> dict:
        """Export validation rules for the installed JSON format.

        Args:
            application: Optional preset name to constrain the exported identity.

        Returns:
            The JSON Schema dictionary.

        Raises:
            ValueError: The requested preset name is unknown.
        """
        if application is not None and application not in APPLICATIONS:
            raise ValueError("Unknown application")
        result = Report.model_json_schema()
        if application is not None:
            result["properties"]["application"] = {"type": "string", "const": application}
        return result
