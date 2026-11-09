"""Wrapping description tables, explicit row highlighting and portable JSON."""

import json
from collections import defaultdict

import pytest
from pydantic import ValidationError

from smd_reports import ReportLoader, ReportRenderer


def document(payloads, section, **options):
    payload = payloads["generic"]
    payload.update(branding={}, sections=[section], **options)
    return ReportLoader().loads(json.dumps(payload))


@pytest.mark.parametrize("language,word,boolean", [("en", "Gene", "No"), ("sv", "Gen", "Nej")])
def test_items_are_localized_escaped_and_preserved_in_portable_json(
    payloads, language, word, boolean
):
    definition = {
        "kind": "compact_table",
        "key": "genes",
        "heading": {"en": "Analyzed genes", "sv": "Analyserade gener"},
        "items": [{"en": "Gene", "sv": "Gen"}, "<PATIENT_NAME>", 0, False, None, "BRAF", "BRAF"],
    }
    report = document(payloads, definition, language=language)
    html = ReportRenderer().render_html(report)
    assert f">{word}</li>" in html
    assert f">{boolean}</li>" in html and ">0</li>" in html and ">-</li>" in html
    assert "&lt;PATIENT_NAME&gt;</li>" in html
    assert html.count(">BRAF</li>") == 2
    exported = json.loads(report.model_dump_json())["sections"][0]
    assert exported["items"] == definition["items"]
    assert type(exported["items"][2]) is int and type(exported["items"][3]) is bool
    restored = ReportLoader().loads(report.model_dump_json())
    assert ReportRenderer().render_html(restored) == html
    assert "CompactTableSection" in ReportLoader().schema()["$defs"]


def test_compact_markdown_uses_the_existing_sanitizer(payloads):
    report = document(
        payloads,
        {
            "kind": "compact_table",
            "key": "items",
            "format": "markdown",
            "items": ["**Reviewed** <PATIENT_NAME> <script>bad()</script>"],
        },
    )
    html = ReportRenderer().render_html(report)
    assert "<strong>Reviewed</strong>" in html and "&lt;PATIENT_NAME&gt;" in html
    assert "<script>" not in html


@pytest.mark.parametrize(
    "language,text", [("en", "No genes supplied"), ("sv", "Inga gener angivna")]
)
def test_empty_compact_table_uses_its_translated_message(payloads, language, text):
    report = document(
        payloads,
        {
            "kind": "compact_table",
            "key": "items",
            "items": [],
            "empty_text": {"en": "No genes supplied", "sv": "Inga gener angivna"},
        },
        language=language,
    )
    html = ReportRenderer().render_html(report)
    assert f'<p class="empty">{text}</p>' in html
    assert '<ul class="compact-table"' not in html


@pytest.mark.parametrize(
    "changes",
    [
        {"items": "APC,BRAF"},
        {"items": [{"de": "Gen"}]},
        {"items": [{}]},
        {"items": [["APC"]]},
        {"columns": 0},
        {"columns": -1},
        {"columns": 65},
        {"columns": "auto"},
        {"format": "html"},
        {"rows": [["BRAF"]]},
    ],
)
def test_invalid_compact_table_fields_are_rejected(payloads, changes):
    with pytest.raises(ValidationError):
        document(payloads, {"kind": "compact_table", "key": "items", "items": ["BRAF"], **changes})


def pdf(report):
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    return pymupdf.open(stream=ReportRenderer().render_pdf(report), filetype="pdf")


def gene_lines(document):
    lines = defaultdict(list)
    for index, page in enumerate(document):
        for word in page.get_text("words"):
            if word[4].startswith("GENE-"):
                lines[(index, round(word[1], 1))].append(word)
    return list(lines.values())


def test_automatic_cells_wrap_to_the_selected_paper_width(payloads):
    counts = []
    for width in [110, 210]:
        report = document(
            payloads,
            {
                "kind": "compact_table",
                "key": "items",
                "items": [f"GENE-{index:03d}" for index in range(30)],
            },
            presentation={"page_size": "custom", "custom_width_mm": width, "custom_height_mm": 297},
        )
        result = pdf(report)
        lines = gene_lines(result)
        counts.append(max(len(line) for line in lines))
        assert sum(map(len, lines)) == 30
        for page in result:
            words = [word for word in page.get_text("words") if word[4].startswith("GENE-")]
            assert all(45 <= word[0] < word[2] <= page.rect.width - 45 for word in words)
    assert counts[0] < counts[1]


def test_fixed_columns_use_equal_width_cells(payloads):
    report = document(
        payloads,
        {
            "kind": "compact_table",
            "key": "items",
            "columns": 5,
            "items": [f"GENE-{index:03d}" for index in range(10)],
        },
    )
    result = pdf(report)
    lines = gene_lines(result)
    assert list(map(len, lines)) == [5, 5]
    assert [word[0] for word in lines[0]] == pytest.approx([word[0] for word in lines[1]], abs=0.1)


def test_compact_items_continue_across_pages_without_loss_or_reordering(payloads):
    items = [f"GENE-{index:04d}" for index in range(500)]
    report = document(payloads, {"kind": "compact_table", "key": "items", "items": items})
    result = pdf(report)
    assert len(result) > 1
    words = [
        word for page in result for word in page.get_text("words") if word[4].startswith("GENE-")
    ]
    assert [word[4] for word in words] == items
    for page in result:
        assert all(
            report.header_height_mm * 72 / 25.4 - 1
            <= word[1]
            < word[3]
            <= page.rect.height - 22 * 72 / 25.4 + 1
            for word in page.get_text("words")
            if word[4].startswith("GENE-")
        )


def test_wide_item_wraps_inside_its_cell(payloads):
    value = "LONGGENE" * 24
    report = document(
        payloads,
        {"kind": "compact_table", "key": "items", "items": [value]},
        presentation={"page_size": "custom", "custom_width_mm": 100, "custom_height_mm": 210},
    )
    result = pdf(report)
    text = "".join(result[0].get_text().split())
    assert value in text
    assert all(
        40 <= word[0] < word[2] <= result[0].rect.width - 40
        for word in result[0].get_text("words")
        if "LONG" in word[4]
    )


def test_single_row_cells_are_compact(payloads):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML

    from smd_reports.rendering import _offline_url_fetcher

    report = document(
        payloads, {"kind": "compact_table", "key": "items", "items": ["APC", "BRAF", "KRAS"]}
    )
    rendered = HTML(
        string=ReportRenderer().render_html(report), url_fetcher=_offline_url_fetcher()
    ).render()
    cells = [
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if box.element_tag == "li" and type(box).__name__ == "BlockBox"
    ]
    assert len(cells) == 3
    assert all(box.border_height() < 24 for box in cells)


def test_row_highlighting_is_explicit_and_survives_json_export(payloads):
    section = {
        "kind": "table",
        "key": "variants",
        "columns": {"en": ["Gene", "Flag"]},
        "rows": [["FIRST", False], ["SECOND", True]],
        "row_options": {"1": {"highlight": True}},
    }
    report = document(payloads, section)
    html = ReportRenderer().render_html(report)
    assert html.count('<tr class="row-highlight">') == 1
    assert (
        json.loads(report.model_dump_json())["sections"][0]["row_options"] == section["row_options"]
    )
    assert ReportRenderer().render_html(ReportLoader().loads(report.model_dump_json())) == html
    result = pdf(report)
    fills = [
        drawing
        for drawing in result[0].get_drawings()
        if drawing.get("fill")
        and tuple(round(part * 255) for part in drawing["fill"]) == (255, 230, 230)
    ]
    assert fills
    second = result[0].search_for("SECOND")[0]
    first = result[0].search_for("FIRST")[0]
    assert any(drawing["rect"].intersects(second) for drawing in fills)
    assert not any(drawing["rect"].intersects(first) for drawing in fills)


@pytest.mark.parametrize(
    "options", [{"1": {"highlight": True}}, {"-1": {}}, {"01": {}}, {"0": {"color": "red"}}]
)
def test_row_options_require_valid_indexes_and_fields(payloads, options):
    with pytest.raises(ValidationError):
        document(
            payloads,
            {
                "kind": "table",
                "key": "data",
                "columns": {"en": ["Value"]},
                "rows": [["DEMO"]],
                "row_options": options,
            },
        )
