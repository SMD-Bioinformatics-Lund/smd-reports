"""Read report JSON and embed local artwork."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .assets import embed_image, prepare_image
from .core import Report
from .errors import ReportAssetError, ReportInputError
from .presets import PRESETS

logger = logging.getLogger(__name__)

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
            raise ReportInputError("Duplicate JSON keys are not allowed; remove the repeated key.")
        result[key] = value
    return result


def reject_constant(value):
    """Reject nonstandard JSON numeric constants.

    Args:
        value: The NaN or Infinity token encountered by the decoder.

    Raises:
        ValueError: Always, because the token is not a finite JSON number.
    """
    raise ReportInputError("Non-finite JSON numbers are prohibited; use null or a finite value.")


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
            UnicodeError: The JSON file is not UTF-8 encoded.
            ValueError: JSON syntax, numeric constants, or object keys are invalid.
            pydantic.ValidationError: Document fields do not match the input format.
            ReportAssetError: Referenced artwork cannot be loaded.
        """
        path = Path(path)
        try:
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            logger.error("Unable to read report JSON file")
            raise
        return self.loads(source, base_dir=path.parent)

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
        logger.info("Loading report JSON")
        if not isinstance(source, (str, bytes)):
            logger.error("Report input is not JSON text or bytes")
            raise TypeError("Supply JSON text or UTF-8 bytes; use load() for a JSON file.")
        try:
            values = json.loads(
                source, object_pairs_hook=unique_object, parse_constant=reject_constant
            )
        except (ValueError, UnicodeError):
            logger.error("Report JSON parsing failed")
            raise
        try:
            document = Report.model_validate(values)
        except ValidationError:
            logger.error("Report validation failed")
            raise

        def image(value, field):
            """Embed one image using a structural field path for errors."""
            if value is None or value.startswith("data:"):
                return value
            path = Path(value)
            if not path.is_absolute():
                if base_dir is None:
                    raise ReportAssetError(field, "Relative image paths require base_dir.")
                path = Path(base_dir) / path
            try:
                return embed_image(path)
            except FileNotFoundError as exc:
                raise ReportAssetError(
                    field, "Image file not found. Check the local image path."
                ) from exc
            except PermissionError as exc:
                raise ReportAssetError(field, "Permission denied while reading the image.") from exc
            except IsADirectoryError as exc:
                raise ReportAssetError(
                    field, "The image path is a directory; choose an image file."
                ) from exc
            except ReportInputError as exc:
                raise ReportAssetError(field, str(exc)) from exc
            except (OSError, ValueError) as exc:
                raise ReportAssetError(field, "Image could not be read or decoded.") from exc

        image_count = 0
        try:
            for key in ("application_logo", "center_logo", "accreditation_logo"):
                value = image(getattr(document.branding, key), f"branding.{key}")
                setattr(document.branding, key, value)
                image_count += value is not None
            for section_index, section in enumerate(document.sections):
                assets = [
                    (asset, f"sections[{section_index}].images[{index}].source")
                    for index, asset in enumerate(section.images)
                ]
                if section.kind == "image":
                    assets.append((section, f"sections[{section_index}].source"))
                for asset, field in assets:
                    asset.source = image(asset.source, field)
                    try:
                        prepare_image(
                            asset.source,
                            frame=asset.frame,
                            accepted_formats=document.presentation.accepted_image_formats,
                        )
                    except ReportInputError as exc:
                        raise ReportAssetError(field, str(exc)) from exc
                    except (OSError, ValueError) as exc:
                        raise ReportAssetError(
                            field, "Image could not be decoded or prepared."
                        ) from exc
                    image_count += 1
        except ReportAssetError as exc:
            logger.error("Report asset loading failed at %s", exc.field)
            raise
        logger.info(
            "Report loaded: preset=%s, sections=%d, images=%d",
            document.preset_name,
            len(document.sections),
            image_count,
        )
        return document

    def schema(self, application: str | None = None, *, preset: str | None = None) -> dict:
        """Export validation rules for the installed JSON format.

        Args:
            application: Legacy preset constraint, retained for existing callers.
            preset: Optional named preset to require in the exported document.

        Returns:
            The JSON Schema dictionary.

        Raises:
            ValueError: The requested preset name is unknown.
        """
        if application is not None and preset is not None:
            raise ReportInputError("Choose either preset or application for schema export")
        if any(value is not None and value not in PRESETS for value in (application, preset)):
            logger.error("Report schema export failed: unknown preset")
            raise ReportInputError(
                "Unknown preset. Choose generic, coyote3, genexus, cll_genie or pgx."
            )
        result = Report.model_json_schema()
        if application is not None:
            result["properties"]["application"] = {"type": "string", "const": application}
        if preset is not None:
            result["properties"]["preset"] = {"type": "string", "const": preset}
            result["required"].append("preset")
        logger.info("Report JSON Schema exported")
        return result
