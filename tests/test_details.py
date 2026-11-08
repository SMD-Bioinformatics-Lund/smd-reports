"""Columns defined once support arbitrary matrix rows and grouped layouts."""

import pytest
from pydantic import ValidationError

from smd_reports import ReportRenderer


@pytest.mark.parametrize("application", ["coyote3", "genexus", "cll_genie", "pgx"])
@pytest.mark.parametrize("kind", ["table", "details"])
def test_new_columns_need_only_json_changes(payloads, load, application, kind):
    data = payloads["pgx"]
    data["application"] = application
    data["sections"] = [
        {
            "kind": kind,
            "key": "dynamic",
            "heading": "Dynamic",
            "columns": {
                "en": [f"Field {i}" for i in range(9)],
                "sv": [f"Field {i}" for i in range(9)],
            },
            "rows": [[f"VALUE-{r}-{c}" for c in range(9)] for r in range(3)],
        }
    ]
    html = ReportRenderer().render_html(load(data))
    for row in data["sections"][0]["rows"]:
        assert all(value in html for value in row)
    assert "Field 8" in html
    assert "column.key" not in html


@pytest.mark.parametrize("row", [[1], [1, 2, 3]])
def test_misaligned_rows_fail_instead_of_losing_values(payloads, load, row):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "table",
            "key": "bad",
            "columns": {"en": ["A", "B"], "sv": ["A", "B"]},
            "rows": [row],
        }
    ]
    with pytest.raises(ValidationError, match="exactly one value"):
        load(data)


@pytest.mark.parametrize("pairs", [1, 2, 3, 4])
def test_detail_headers_are_declared_once_and_rows_preserve_values(payloads, load, pairs):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "details",
            "key": "details",
            "fields_per_row": pairs,
            "record_heading": "{0}: {1}",
            "columns": {
                "en": ["Gene", "Variant", "Zero", "Boolean", "Missing", "Comment"],
                "sv": ["Gene", "Variant", "Zero", "Boolean", "Missing", "Comment"],
            },
            "column_options": {"5": {"full_width": True, "format": "markdown"}},
            "rows": [
                ["DEMO1", "p.Example", 0, False, None, "**FIRST**"],
                ["DEMO2", "p.Other", 1, True, "present", "**SECOND**"],
            ],
        }
    ]
    html = ReportRenderer().render_html(load(data))
    for value in [
        "DEMO1: p.Example",
        "DEMO2: p.Other",
        ">0</td>",
        ">Nej</td>",
        ">-</td>",
        "<strong>SECOND</strong>",
    ]:
        assert value in html


@pytest.mark.parametrize("heading", ["{9}", "{0.__class__}", "{0[0]}", "{0!r}", "{0:>1000}", "{}"])
def test_record_heading_rejects_unsafe_or_unknown_fields(payloads, load, heading):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "details",
            "key": "details",
            "columns": {"en": ["A"], "sv": ["A"]},
            "rows": [["x"]],
            "record_heading": heading,
        }
    ]
    with pytest.raises(ValidationError):
        load(data)


def test_detail_full_width_placement_is_json_configurable(payloads, load):
    data = payloads["pgx"]
    section = {
        "kind": "details",
        "key": "details",
        "columns": {"en": ["A", "Comment", "B"], "sv": ["A", "Comment", "B"]},
        "column_options": {"1": {"full_width": True}},
        "rows": [["FIRST-VALUE", "WIDE-VALUE", "LAST-VALUE"]],
    }
    data["sections"] = [section]
    renderer = ReportRenderer()
    html = renderer.render_html(load(data))
    assert html.index("WIDE-VALUE") < html.index("LAST-VALUE")
    section["full_width_last"] = True
    html = renderer.render_html(load(data))
    assert html.index("LAST-VALUE") < html.index("WIDE-VALUE")


@pytest.mark.parametrize("invalid", ["index", "width", "pair", "heading"])
def test_grid_layout_is_validated(payloads, load, invalid):
    data = payloads["cll-genie-positive"]
    section = next(s for s in data["sections"] if s["kind"] == "grid")
    if invalid == "index":
        section["layout"][0]["cells"][0]["column"] = 1000
    elif invalid == "width":
        section["layout"][0]["cells"][0]["span"] = 10
    elif invalid == "pair":
        section["layout"][0]["cells"][0]["label_span"] = 2
    else:
        section["record_titles"] = ["One", "Two"]
    with pytest.raises(ValidationError):
        load(data)


def test_cll_layout_and_additional_field_are_defined_in_json(payloads, load):
    data = payloads["cll-genie-positive"]
    section = next(s for s in data["sections"] if s["kind"] == "grid")
    added = len(section["columns"]["en"])
    section["columns"]["en"].append("New metric")
    section["columns"]["sv"].append("Nytt mått")
    for row in section["rows"]:
        row.append(0)
    section["rows"].append(list(section["rows"][0]))
    section["rows"][1][0] = "Seq2"
    section["layout"].append({"cells": [{"column": added, "span": 5}]})
    html = ReportRenderer().render_html(load(data))
    assert "Nytt mått" in html and "Seq2 - 321 nt" in html
    assert "IGHV3-21*01" in html and "1500" in html and "313/321" in html
    assert "D-REGION reading frame" in html and "FR-IMGT lengths" in html
    assert "junction_legend" not in html


def test_grid_hide_if_empty_preserves_zero_and_false(payloads, load):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "grid",
            "key": "grid",
            "columns": {"en": ["Zero", "False", "Empty"], "sv": ["Zero", "False", "Empty"]},
            "rows": [[0, False, None]],
            "record_heading": "Values",
            "grid_columns": 2,
            "layout": [
                {"hide_if_empty": True, "cells": [{"column": i, "span": 2}]} for i in range(3)
            ],
        }
    ]
    html = ReportRenderer().render_html(load(data))
    assert ">0</td>" in html and ">Nej</td>" in html
    assert ">Empty</th>" not in html
