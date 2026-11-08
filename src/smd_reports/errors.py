"""Report exceptions and validation messages suitable for user-facing output."""

from functools import lru_cache

from pydantic import ValidationError


class ReportInputError(ValueError):
    """An input error whose message contains no report values or file paths."""


class ReportAssetError(ReportInputError):
    """An image-loading failure identified by its JSON field."""

    def __init__(
        self, field: str, reason: str = "Check the image file, format and frame selection."
    ):
        """Describe the failing image without exposing its path or contents.

        Args:
            field: Structural JSON path, using indexes for sections and images.
            reason: Explanation that excludes report values, image data and file paths.
        """
        self.field = field
        self.reason = reason
        super().__init__(f"Cannot load {field}: {reason}")


class ReportRenderError(RuntimeError):
    """Report templates or the rendering engine could not produce output."""


class PDFUnavailableError(ReportRenderError):
    """The optional PDF renderer or its native runtime is unavailable."""


@lru_cache(maxsize=1)
def _schema_names() -> frozenset[str]:
    """Collect structural names and fixed options from the report schema.

    Returns:
        Names that can be shown in validation paths without revealing input keys.
    """
    from .core import Report

    names = {"en", "sv"}

    def visit(value):
        if isinstance(value, dict):
            names.update(value.get("properties", {}))
            names.update(item for item in value.get("enum", []) if isinstance(item, str))
            if isinstance(value.get("const"), str):
                names.add(value["const"])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(Report.model_json_schema())
    return frozenset(names)


def _field_path(location) -> str:
    """Format a validation path while redacting unrecognized input keys.

    Args:
        location: Field locations supplied by Pydantic.

    Returns:
        A JSON field path containing structural names and positional indexes.
    """
    parts = []
    for item in location:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        elif item in _schema_names():
            parts.append(("." if parts else "") + item)
        elif (
            isinstance(item, str)
            and item.isascii()
            and item.isdigit()
            and parts[-1:] == [".column_options"]
        ):
            parts.append(f"[{item}]")
        else:
            parts.append(("." if parts else "") + "<unknown>")
    return "".join(parts) or "report"


def format_validation_error(error: ValidationError) -> str:
    """Describe invalid fields without including report values or unknown input keys.

    Args:
        error: Validation error raised while loading or rendering a report.

    Returns:
        A readable message with up to ten field errors. Input values and exception
        representations are excluded; additional errors are reported as a count.
    """
    messages = {
        "missing": "Required field is missing.",
        "extra_forbidden": "Unknown field; remove it or consult the JSON Schema.",
        "union_tag_invalid": "Unknown section kind; check the supported section types.",
        "union_tag_not_found": "Section must include a kind.",
        "literal_error": "Unsupported option; check the allowed values in the JSON Schema.",
        "dict_type": "Expected a JSON object.",
        "list_type": "Expected a JSON array.",
        "string_type": "Expected text.",
        "int_type": "Expected an integer.",
        "int_parsing": "Expected an integer.",
        "float_type": "Expected a number.",
        "float_parsing": "Expected a number.",
        "bool_type": "Expected true or false.",
        "bool_parsing": "Expected true or false.",
        "finite_number": "Expected a finite number.",
        "datetime_type": "Expected an ISO 8601 timestamp with a UTC offset.",
        "datetime_parsing": "Expected an ISO 8601 timestamp with a UTC offset.",
        "datetime_from_date_parsing": "Expected an ISO 8601 timestamp with a UTC offset.",
    }
    bounds = {
        "greater_than",
        "greater_than_equal",
        "less_than",
        "less_than_equal",
        "too_short",
        "too_long",
        "string_too_short",
        "string_too_long",
        "string_pattern_mismatch",
    }
    errors = error.errors(include_input=False, include_url=False)
    result = []
    for item in errors[:10]:
        code = item["type"]
        reason = item.get("ctx", {}).get("error")
        if code == "value_error" and isinstance(reason, ReportInputError):
            message = str(reason)
        elif code in bounds:
            message = item["msg"]
        else:
            message = messages.get(code, "Invalid value; check this field in the JSON Schema.")
        result.append(f"{_field_path(item['loc'])}: {message}")
    if len(errors) > 10:
        result.append(f"{len(errors) - 10} additional validation errors")
    return "Invalid report: " + "; ".join(result)
