"""Per-cell typography, column inheritance, validation and PDF font selection."""

import json
import re
from io import BytesIO

import pytest
from pydantic import ValidationError

from smd_reports import ReportLoader, ReportRenderer


def matrix(kind):
    section = {
        "kind": kind,
        "key": "formatted",
        "columns": {"en": ["Gene", "Classification"]},
        "rows": [["BRAF", "FIRST"], ["EXAMPLE", "SECOND"], ["OTHER", "THIRD"]],
        "column_options": {"1": {"emphasis": True, "italic": True}},
        "cell_options": {
            "0": {"0": {"italic": True}, "1": {"font_weight": "bold"}},
            "1": {"1": {"font_weight": "normal", "italic": False}},
        },
    }
    if kind == "grid":
        section.update(
            grid_columns=4,
            layout=[{"cells": [{"column": 0, "span": 2}, {"column": 1, "span": 2}]}],
        )
    return section


def cell_tag(html, value):
    return re.search(r"<td\b[^>]*>" + value + r"</td>", html)[0]


@pytest.mark.parametrize("kind", ["table", "details", "grid"])
def test_individual_cells_override_defaults_without_changing_values(payloads, load, kind):
    data = payloads["pgx"]
    definition = matrix(kind)
    data["sections"] = [definition]
    report = load(data)
    html = ReportRenderer().render_html(report)
    assert "font-weight: 700;" in cell_tag(html, "FIRST")
    assert "font-style: italic;" in cell_tag(html, "FIRST")
    assert "font-weight: 400; font-style: normal;" in cell_tag(html, "SECOND")
    assert "font-style: italic;" in cell_tag(html, "BRAF")
    assert "font-style:" not in cell_tag(html, "EXAMPLE")
    assert "emphasis" in cell_tag(html, "THIRD")
    assert "font-weight: 700;" not in cell_tag(html, "THIRD")
    assert report.sections[0].rows == definition["rows"]
    assert report.sections[0].render_columns[1].font_weight is None
    encoded = report.model_dump_json()
    restored = ReportLoader().loads(encoded)
    assert restored == report
    assert ReportRenderer().render_html(restored) == html
    assert json.loads(encoded)["sections"][0]["cell_options"]["1"]["1"]["italic"] is False


def test_null_cells_inherit_explicit_column_styles(payloads, load):
    definition = matrix("table")
    definition["column_options"]["1"].update(font_weight="semibold", italic=False)
    definition["cell_options"]["2"] = {"1": {"font_weight": None, "italic": None}}
    payloads["pgx"]["sections"] = [definition]
    html = ReportRenderer().render_html(load(payloads["pgx"]))
    assert "font-weight: 600; font-style: normal;" in cell_tag(html, "THIRD")


def test_cell_typography_applies_to_badges_and_escapes_text(payloads, load):
    definition = matrix("table")
    definition["column_options"]["1"]["badge"] = {}
    definition["rows"][0][1] = "<FIRST>"
    payloads["pgx"]["sections"] = [definition]
    html = ReportRenderer().render_html(load(payloads["pgx"]))
    assert re.search(r'<span class="report-badge"[^>]*font-weight: 700;[^>]*>&lt;FIRST&gt;', html)
    assert re.search(r'<span class="report-badge"[^>]*font-weight: 400; font-style: normal;', html)
    assert "<FIRST>" not in html


@pytest.mark.parametrize(
    "options",
    [
        {"3": {"0": {"italic": True}}},
        {"0": {"2": {"italic": True}}},
        {"-1": {"0": {"italic": True}}},
        {"01": {"0": {"italic": True}}},
        {"0": {"01": {"italic": True}}},
        {"0": {"0": {"font_weight": "700"}}},
        {"0": {"0": {"font_weight": "bold; color: red"}}},
        {"0": {"0": {"italic": "italic"}}},
        {"0": {"0": {"style": "color:red"}}},
        {"0": {"0": {"width": 3}}},
        {"0": {"0": None}},
        {"0": []},
    ],
)
def test_invalid_cell_options_are_rejected(payloads, load, options):
    definition = matrix("table")
    definition["cell_options"] = options
    payloads["pgx"]["sections"] = [definition]
    with pytest.raises(ValidationError):
        load(payloads["pgx"])


@pytest.mark.parametrize("kind", ["table", "details", "grid"])
def test_pdf_uses_distinct_font_faces_for_individual_cells(payloads, load, kind):
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    definition = matrix(kind)
    definition["rows"] = [["REGULAR", "SEMIBOLD"], ["BOLD", "ITALIC"], ["BOLDITALIC", "SEMIITALIC"]]
    definition["column_options"] = {}
    definition["cell_options"] = {
        "0": {"1": {"font_weight": "semibold"}},
        "1": {"0": {"font_weight": "bold"}, "1": {"italic": True}},
        "2": {
            "0": {"font_weight": "bold", "italic": True},
            "1": {"font_weight": "semibold", "italic": True},
        },
    }
    payloads["pgx"]["sections"] = [definition]
    doc = pymupdf.open(stream=ReportRenderer().render_pdf(load(payloads["pgx"])), filetype="pdf")
    spans = {
        span["text"]: span["font"]
        for page in doc
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
    }
    from fontTools.ttLib import TTFont

    embedded_faces = {}
    for xref, _, _, name, *_ in doc[0].get_fonts():
        font = TTFont(BytesIO(doc.extract_font(xref)[3]))
        signature = (font["OS/2"].usWeightClass, bool(font["OS/2"].fsSelection & 1))
        if "Source-Sans-3" in name:
            embedded_faces[signature] = name.split("+", 1)[-1]
    for text, signature in {
        "REGULAR": (400, False),
        "SEMIBOLD": (600, False),
        "BOLD": (700, False),
        "ITALIC": (400, True),
        "BOLDITALIC": (700, True),
        "SEMIITALIC": (600, True),
    }.items():
        assert embedded_faces[signature].startswith(spans[text]), (text, spans[text])
    assert (
        len(
            {
                spans[text]
                for text in definition["rows"][0] + definition["rows"][1] + definition["rows"][2]
            }
        )
        == 6
    )


@pytest.mark.parametrize("kind", ["table", "details", "grid"])
@pytest.mark.parametrize("media", ["screen", "print"])
def test_markdown_cell_spacing_preserves_internal_and_narrative_paragraphs(
    payloads, load, kind, media
):
    weasyprint = pytest.importorskip("weasyprint")
    from smd_reports.rendering import _offline_url_fetcher

    definition = matrix(kind)
    definition["column_options"] = {"1": {"format": "markdown"}}
    definition["cell_options"] = {}
    definition["rows"] = [["EXAMPLE1", "**SINGLE**"], ["EXAMPLE2", "FIRST\n\nMIDDLE\n\nLAST"]]
    payloads["pgx"]["sections"] = [
        definition,
        {"kind": "text", "key": "narrative", "format": "markdown", "text": "OPEN\n\nBODY\n\nEND"},
    ]
    html = ReportRenderer().render_html(load(payloads["pgx"]))
    assert "<p><strong>SINGLE</strong></p>" in html
    document = weasyprint.HTML(
        string=html, media_type=media, url_fetcher=_offline_url_fetcher()
    ).render()
    paragraphs = {
        "".join(box.element.itertext()): box
        for page in document.pages
        for box in page._page_box.descendants()
        if type(box).__name__ == "BlockBox" and box.element_tag == "p"
    }
    assert paragraphs["SINGLE"].margin_top == paragraphs["SINGLE"].margin_bottom == 0
    assert paragraphs["FIRST"].margin_top == 0
    assert paragraphs["LAST"].margin_bottom == 0
    assert paragraphs["MIDDLE"].margin_top > 0
    assert paragraphs["MIDDLE"].margin_bottom > 0
    assert paragraphs["BODY"].margin_top > 0
    assert paragraphs["BODY"].margin_bottom > 0
