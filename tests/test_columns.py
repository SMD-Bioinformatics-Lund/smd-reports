"""Compact translated headers and positional column formatting."""

import json

import pytest
from pydantic import ValidationError

from smd_reports import ReportLoader, ReportRenderer


def section(kind="table"):
    result = {
        "kind": kind,
        "key": "results",
        "columns": {
            "en": ["Gene", "Copy number", "Comment"],
            "sv": ["Gen", "Kopietal", "Kommentar"],
        },
        "column_options": {
            "1": {"width": 2, "emphasis": True, "highlight": True},
            "2": {"full_width": True, "format": "markdown"},
        },
        "rows": [["EXAMPLE", 0, "**Reviewed**"], ["SECOND", False, None]],
    }
    if kind in {"details", "grid"}:
        result["record_heading"] = "{0}: {2}"
    if kind == "grid":
        result.update(
            grid_columns=6,
            layout=[{"cells": [{"column": index, "span": 6}]} for index in range(3)],
        )
    return result


@pytest.mark.parametrize("kind", ["table", "details", "grid"])
@pytest.mark.parametrize(
    "language,header,boolean", [("en", "Copy number", "No"), ("sv", "Kopietal", "Nej")]
)
def test_compact_headers_and_formatting_render_and_round_trip(
    payloads, load, kind, language, header, boolean
):
    data = payloads["pgx"]
    data["language"] = language
    data["sections"] = [section(kind)]
    report = load(data)
    html = ReportRenderer().render_html(report)
    assert f">{header}</th>" in html
    assert ">0</td>" in html and f">{boolean}</td>" in html
    assert "<strong>Reviewed</strong>" in html
    assert "emphasis" in html and "cell-highlight" in html
    if kind == "table":
        assert "width: 50.0%" in html
    encoded = report.model_dump_json()
    exported = json.loads(encoded)["sections"][0]
    assert exported["columns"] == data["sections"][0]["columns"]
    assert exported["column_options"] == data["sections"][0]["column_options"]
    assert exported["rows"][1][1] is False
    restored = ReportLoader().loads(encoded)
    assert restored == report
    assert ReportRenderer().render_html(restored) == html


@pytest.mark.parametrize(
    "language,available,label", [("en", "sv", "Kopietal"), ("sv", "en", "Copy number")]
)
def test_single_language_headers_are_used_when_requested_language_is_absent(
    payloads, load, language, available, label
):
    data = payloads["pgx"]
    data["language"] = language
    definition = section()
    definition["columns"] = {available: definition["columns"][available]}
    data["sections"] = [definition]
    assert f">{label}</th>" in ReportRenderer().render_html(load(data))


@pytest.mark.parametrize(
    "columns",
    [
        {},
        {"en": []},
        {"en": ["A"], "sv": ["A", "B"]},
        {"de": ["Gene"]},
        {"en": [5]},
        {"en": "Gene"},
        {"en": None},
        [{"label": {"en": "Gene", "sv": "Gen"}}],
    ],
)
def test_invalid_column_definitions_fail_validation(payloads, load, columns):
    data = payloads["pgx"]
    data["sections"] = [{"kind": "table", "key": "invalid", "columns": columns}]
    with pytest.raises(ValidationError):
        load(data)


@pytest.mark.parametrize(
    "options",
    [
        {"-1": {"width": 2}},
        {"01": {"width": 2}},
        {"1.0": {"width": 2}},
        {"gene": {"width": 2}},
        {"3": {"width": 2}},
        {"0": {"label": "Replacement"}},
        {"0": {"width": 0}},
        {"0": {"format": "html"}},
        {"0": None},
    ],
)
def test_invalid_column_options_cannot_change_other_columns(payloads, load, options):
    data = payloads["pgx"]
    definition = section()
    definition["column_options"] = options
    data["sections"] = [definition]
    with pytest.raises(ValidationError):
        load(data)


def test_normalization_omits_default_formatting_values(payloads, load):
    data = payloads["pgx"]
    definition = section()
    definition["column_options"] = {"0": {"width": 1, "format": "plain", "emphasis": False}}
    data["sections"] = [definition]
    report = load(data)
    encoded = report.model_dump_json()
    exported = json.loads(encoded)["sections"][0]
    assert exported["column_options"] == {"0": {}}
    assert ReportLoader().loads(encoded) == report


def test_schema_describes_translated_lists_and_optional_formatting():
    schema = ReportLoader().schema()
    for kind in ["TableSection", "DetailSection", "GridSection"]:
        definition = schema["$defs"][kind]
        columns = definition["properties"]["columns"]
        assert columns["type"] == "object"
        assert columns["additionalProperties"]["type"] == "array"
        assert columns["additionalProperties"]["items"]["type"] == "string"
        assert "column_options" not in definition["required"]
