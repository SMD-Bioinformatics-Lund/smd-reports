"""Continuous description tables, explicit row highlighting and portable JSON."""

import json
from collections import defaultdict

import pytest
from pydantic import ValidationError

from smd_reports import ReportLoader, ReportRenderer
from smd_reports.errors import ReportInputError


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
    assert f">{word}</span></td>" in html
    assert (
        f">{boolean}</span></td>" in html
        and ">0</span></td>" in html
        and ">-</span></td>" not in html
    )
    assert "&lt;PATIENT_NAME&gt;</span></td>" in html
    assert html.count(">BRAF</span></td>") == 2
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
    assert '<table class="compact-table"' not in html


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
    report = document(
        payloads,
        {"kind": "compact_table", "key": "items", "items": items},
        presentation={"page_size": "A5"},
    )
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


def test_oversized_item_is_rejected_instead_of_wrapping_or_overflowing(payloads):
    value = "LONGGENE" * 24
    report = document(
        payloads,
        {"kind": "compact_table", "key": "items", "items": [value]},
        presentation={"page_size": "custom", "custom_width_mm": 100, "custom_height_mm": 210},
    )
    with pytest.raises(ReportInputError, match="cannot fit on one line") as error:
        ReportRenderer().render_html(report)
    assert value not in str(error.value)
    assert report.sections[0].items == [value]


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
        if box.element_tag == "td"
        and type(box).__name__ == "TableCellBox"
        and box.element.get("class") == "compact-cell"
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


@pytest.mark.parametrize("size", [8, 9.25, 12])
def test_matrix_has_touching_rows_smaller_text_and_plain_bold_caption(payloads, size):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML

    from smd_reports.rendering import _offline_url_fetcher
    from smd_reports.themes import Theme, default_themes

    items = [f"GENE-{index:03d}" for index in range(31)]
    report = document(
        payloads,
        {
            "kind": "compact_table",
            "key": "items",
            "heading": "Panel genes",
            "items": [None, "", "   ", *items],
        },
        presentation={"page_size": "custom", "custom_width_mm": 100, "custom_height_mm": 210},
    )
    renderer = ReportRenderer()
    renderer.register_theme(
        Theme(**{**default_themes()["generic"].model_dump(), "name": "sized", "body_pt": size})
    )
    html = renderer.render_html(report, theme="sized")
    assert '<p class="compact-caption"><strong>Panel genes</strong></p>' in html
    assert html.count('<td class="compact-cell"') == len(items)
    rendered = HTML(string=html, url_fetcher=_offline_url_fetcher()).render()
    cells = [
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if box.element_tag == "td"
        and type(box).__name__ == "TableCellBox"
        and box.element.get("class") == "compact-cell"
    ]
    rows = defaultdict(list)
    for cell in cells:
        rows[cell.position_y].append(cell)
        assert 0 < cell.padding_top == cell.padding_bottom <= 1
        assert cell.style["font_size"] == pytest.approx((size - 2.5) * 96 / 72)
        lines = [box for box in cell.descendants() if type(box).__name__ == "LineBox"]
        assert len(lines) == 1
        assert lines[0].width <= cell.width
    assert len(rows) > 1
    positions = sorted(rows)
    for previous, following in zip(positions, positions[1:]):
        assert following == pytest.approx(previous + rows[previous][0].border_height(), abs=0.01)
    assert len(rows[positions[-1]]) < len(rows[positions[0]])
    caption = next(
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if box.element_tag == "strong"
        and type(box).__name__ == "TextBox"
        and box.text == "Panel genes"
    )
    assert caption.style["font_size"] == pytest.approx(size * 96 / 72)
    assert caption.style["font_weight"] == 600
    assert tuple(caption.style["color"].coordinates) == (0, 0, 0)


@pytest.mark.parametrize("item", ["# Heading", "- List item", "text<br>next", "😀"])
def test_content_unsuitable_for_single_line_cells_is_rejected(payloads, item):
    report = document(
        payloads, {"kind": "compact_table", "key": "items", "format": "markdown", "items": [item]}
    )
    with pytest.raises(ReportInputError):
        ReportRenderer().render_html(report)


def test_blank_values_do_not_create_cells(payloads):
    report = document(
        payloads,
        {"kind": "compact_table", "key": "items", "items": [None, "", " ", {"en": "", "sv": ""}]},
    )
    html = ReportRenderer().render_html(report)
    assert '<table class="compact-table"' not in html
    assert '<p class="empty">' in html


@pytest.mark.parametrize("width", [110, 210, 297])
def test_automatic_matrix_equal_widths_fit_mixed_length_names(payloads, width):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML

    from smd_reports.rendering import _offline_url_fetcher

    items = ["A", "BRAF", "C7orf55-LUC7L2", "CALR", "EXAMPLE"] * 9
    report = document(
        payloads,
        {"kind": "compact_table", "key": "genes", "items": items},
        presentation={"page_size": "custom", "custom_width_mm": width, "custom_height_mm": 297},
    )
    rendered = HTML(
        string=ReportRenderer().render_html(report), url_fetcher=_offline_url_fetcher()
    ).render()
    cells = [
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if type(box).__name__ == "TableCellBox" and box.element.get("class") == "compact-cell"
    ]
    assert len(cells) == len(items)
    assert (
        max(cell.border_width() for cell in cells) - min(cell.border_width() for cell in cells)
        < 0.01
    )
    for cell in cells:
        assert cell.position_x + cell.border_width() <= width * 96 / 25.4 - 16 * 96 / 25.4 + 1
        lines = [box for box in cell.descendants() if type(box).__name__ == "LineBox"]
        assert len(lines) == 1 and lines[0].width <= cell.width


def test_a4_matrix_fits_sixteen_equal_columns_without_wasted_cell_space(payloads):
    from smd_reports.rendering import _compact_tables

    renderer = ReportRenderer()
    items = ["SMARCB1", "BRAF", "ALK", "APC"] * 10 + ["TP53", "PTEN", "JAK2"]
    report = document(payloads, {"kind": "compact_table", "key": "genes", "items": items})
    layout = _compact_tables(report, renderer.themes[report.theme_name])["genes"]
    assert [len(row) for row in layout["rows"]] == [16, 16, 11]
    assert max(layout["widths"]) == min(layout["widths"])
    assert 669 <= layout["width"] <= 673
    result = pdf(report)
    assert all(token in result[0].get_text() for token in ["SMARCB1", "TP53", "PTEN", "JAK2"])
