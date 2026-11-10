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


def test_normalization_preserves_explicit_width_and_omits_default_formatting(payloads, load):
    data = payloads["pgx"]
    definition = section()
    definition["column_options"] = {"0": {"width": 1, "format": "plain", "emphasis": False}}
    data["sections"] = [definition]
    report = load(data)
    encoded = report.model_dump_json()
    exported = json.loads(encoded)["sections"][0]
    assert exported["column_options"] == {"0": {"width": 1}}
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


def table_cells(report):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML

    from smd_reports.rendering import _offline_url_fetcher

    rendered = HTML(
        string=ReportRenderer().render_html(report), url_fetcher=_offline_url_fetcher()
    ).render()
    table = next(
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if type(box).__name__ == "TableBox"
        and box.element is not None
        and "variant_table" in box.element.get("class", "")
    )
    cells = [
        box
        for box in table.descendants()
        if type(box).__name__ == "TableCellBox" and box.element_tag == "td"
    ]
    return table, cells


@pytest.mark.parametrize("language", ["en", "sv"])
def test_content_sizing_keeps_v_gene_identity_on_one_line(payloads, load, language):
    payload = payloads["cll-genie-positive"]
    payload["language"] = language
    payload["sections"] = [
        next(section for section in payload["sections"] if section["key"] == "cll-sequences")
    ]
    report = load(payload)
    assert report.sections[0].automatic_widths
    table, cells = table_cells(report)
    identity = cells[2]
    lines = [box for box in identity.descendants() if type(box).__name__ == "LineBox"]
    assert len(lines) == 1
    assert identity.width > cells[0].width and identity.width > cells[1].width
    assert table.border_width() <= (210 - 32) * 96 / 25.4 + 1
    assert ReportRenderer().render_html(
        ReportLoader().loads(report.model_dump_json())
    ) == ReportRenderer().render_html(report)


@pytest.mark.parametrize("options", [{}, {"1": {"emphasis": True}}])
def test_formatting_options_keep_automatic_widths(payloads, load, options):
    payload = payloads["generic"]
    payload["sections"] = [
        {
            "kind": "table",
            "key": "measurements",
            "columns": {"en": ["ID", "Description"]},
            "rows": [["A", "A longer description of the measured result"]],
            "column_options": options,
        }
    ]
    report = load(payload)
    assert report.sections[0].automatic_widths
    assert "variant_table auto-columns" in ReportRenderer().render_html(report)
    assert ReportLoader().loads(report.model_dump_json()).sections[0].automatic_widths


def test_explicit_equal_widths_remain_fixed_after_json_export(payloads, load):
    payload = payloads["generic"]
    payload["sections"] = [
        {
            "kind": "table",
            "key": "measurements",
            "columns": {"en": ["ID", "Description"]},
            "rows": [["A", "A longer description of the measured result"]],
            "column_options": {"0": {"width": 1}},
        }
    ]
    report = ReportLoader().loads(load(payload).model_dump_json())
    assert not report.sections[0].automatic_widths
    _, cells = table_cells(report)
    assert cells[0].border_width() == pytest.approx(cells[1].border_width())


def test_long_unbroken_values_still_fit_narrow_pages(payloads, load):
    payload = payloads["generic"]
    payload["presentation"] = {
        "page_size": "custom",
        "custom_width_mm": 100,
        "custom_height_mm": 210,
    }
    payload["sections"] = [
        {
            "kind": "table",
            "key": "long-values",
            "columns": {"en": ["ID", "Value"]},
            "rows": [["A", "LONGVALUE" * 60], ["B", "Short value"]],
        }
    ]
    table, cells = table_cells(load(payload))
    assert table.border_width() <= (100 - 32) * 96 / 25.4 + 1
    assert all(
        line.width <= cell.width + 1
        for cell in cells
        for line in cell.descendants()
        if type(line).__name__ == "LineBox"
    )


@pytest.mark.parametrize(
    "row_highlight,expected", [(False, (1, 1, 224 / 255)), (True, (1, 230 / 255, 230 / 255))]
)
def test_column_highlight_is_visible_and_row_highlight_takes_precedence(
    payloads, load, row_highlight, expected
):
    payload = payloads["generic"]
    payload["sections"] = [
        {
            "kind": "table",
            "key": "highlighted",
            "columns": {"en": ["Result"]},
            "rows": [["Example"]],
            "column_options": {"0": {"highlight": True}},
            "row_options": {"0": {"highlight": row_highlight}},
        }
    ]
    _, cells = table_cells(load(payload))
    assert tuple(cells[0].style["background_color"].coordinates) == pytest.approx(expected)
