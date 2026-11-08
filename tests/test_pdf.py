"""PDF content, pagination, source layouts and dynamic matrix columns."""

import json
import re

import pytest

from smd_reports import ReportLoader, ReportRenderer

pytest.importorskip("weasyprint")
pymupdf = pytest.importorskip("pymupdf")


def pdf(report):
    return pymupdf.open(stream=ReportRenderer().render_pdf(report), filetype="pdf")


def footer_images(page):
    return [rect for rect in page.search_for("PLACEHOLDER") if rect.y0 > page.rect.height - 110]


@pytest.mark.parametrize("name", ["coyote3-dna", "genexus", "cll-genie-positive", "pgx"])
@pytest.mark.parametrize("long_summary", [False, True])
def test_summary_page_breaks_before_and_after(payloads, load, name, long_summary):
    data = payloads[name]
    data["sections"] = [
        {"kind": "text", "key": "before", "text": "BEFORE-MARKER"},
        {
            "kind": "summary",
            "key": "summary",
            "heading": "Summary",
            "text": "SUMMARY-BEGIN\n"
            + ("Reviewed text.\n" * (180 if long_summary else 1))
            + "SUMMARY-END",
        },
        {"kind": "text", "key": "after", "text": "AFTER-MARKER"},
    ]
    doc = pdf(load(data))

    def page_for(marker):
        return next(i for i, p in enumerate(doc) if marker in p.get_text())

    assert page_for("SUMMARY-BEGIN") > page_for("BEFORE-MARKER")
    assert page_for("AFTER-MARKER") > page_for("SUMMARY-END")
    if long_summary:
        assert page_for("SUMMARY-END") > page_for("SUMMARY-BEGIN")


@pytest.mark.parametrize(
    "name",
    ["coyote3-dna", "coyote3-rna", "genexus", "cll-genie-positive", "cll-genie-no_clone", "pgx"],
)
def test_pdfs_retain_identity_headers_fonts_and_footer(reports, name):
    doc = pdf(reports[name])
    text = "\n".join(p.get_text() for p in doc)
    assert "Exempel på granskad slutsats" in text
    for i, page in enumerate(doc):
        assert "SYNTHETIC-001" in page.get_text()
        assert re.search(rf"Sida\s+{i + 1}\s+av\s+{len(doc)}", page.get_text())
        assert footer_images(page)
        assert round(page.rect.width) == 595 and round(page.rect.height) == 842
        assert any("Source" in str(font) for font in page.get_fonts())
        assert all(
            0 <= block[1] <= block[3] <= page.rect.height for block in page.get_text("blocks")
        )


def test_long_table_keeps_all_rows_and_repeats_headers(payloads, load):
    data = payloads["coyote3-dna"]
    data["sections"] = [
        {
            "kind": "table",
            "key": "long",
            "columns": [{"label": "Synthetic row"}, {"label": "Description"}],
            "rows": [[f"ROW-{i:03d}", "LongIdentifier" * 12] for i in range(100)],
        }
    ]
    doc = pdf(load(data))
    text = "\n".join(p.get_text() for p in doc)
    assert len(doc) > 2
    for i in range(100):
        assert text.count(f"ROW-{i:03d}") == 1
    assert all("Synthetic row" in p.get_text() for p in doc)


@pytest.mark.parametrize("kind", ["details", "grid"])
def test_long_detail_comment_continues_without_truncation(payloads, load, kind):
    data = payloads["cll-genie-positive"]
    section = {
        "kind": kind,
        "key": "details",
        "record_heading": "Detailed finding",
        "columns": [
            {"label": "Gene"},
            {"label": "Comment", "full_width": True, "format": "markdown"},
            {"label": "Final"},
        ],
        "rows": [["EXAMPLE", "\n\n".join(f"PARAGRAPH-{i:03d}" for i in range(100)), "END-MARKER"]],
    }
    if kind == "grid":
        section.update(
            grid_columns=5, layout=[{"cells": [{"column": i, "span": 5}]} for i in range(3)]
        )
    data["sections"] = [section]
    doc = pdf(load(data))
    text = "\n".join(p.get_text() for p in doc)
    assert len(doc) > 2
    for i in range(100):
        assert text.count(f"PARAGRAPH-{i:03d}") == 1
    assert text.count("END-MARKER") == 1
    assert all(footer_images(p) for p in doc)


def test_cll_original_grouping_is_preserved_by_json_grid(reports):
    doc = pdf(reports["cll-genie-positive"])
    text = "\n".join(p.get_text() for p in doc)
    for value in [
        "IGHV3-21*01",
        "1500",
        "313/321",
        "IGHJ6*02",
        "60/60",
        "D-REGION reading frame",
        "FR-IMGT lengths",
        "DEMO-V {N1} DEMO-D {N2} DEMO-J",
        "0.0%",
    ]:
        assert value in text
    page = next(p for p in doc if p.search_for("IGHV3-21*01"))
    gene = page.search_for("IGHV3-21*01")[0]
    score = page.search_for("1500")[0]
    assert abs(gene.y0 - score.y0) < 1 and gene.x0 < score.x0


def test_genexus_all_detail_groups_follow_summary(reports):
    doc = pdf(reports["genexus"])
    conclusion = next(i for i, p in enumerate(doc) if "Slutsats" in p.get_text())
    details = next(i for i, p in enumerate(doc) if "Detekterade mutationer" in p.get_text())
    assert details > conclusion
    text = "\n".join(p.get_text() for p in doc)
    for value in [
        "DEMO-FUSION-001",
        "Unika molekyler",
        "CNV-kvot",
        "Hotspot",
        "Brytpunktsintervall",
    ]:
        assert value in text


def test_dynamic_column_and_localized_heading_appear_in_pdf(payloads, load):
    data = payloads["pgx"]
    data["language"] = "en"
    data["sections"] = [
        {
            "kind": "table",
            "key": "custom",
            "columns": [{"label": {"en": f"Column {i}", "sv": f"Kolumn {i}"}} for i in range(8)],
            "rows": [[f"VALUE-{i}" for i in range(8)]],
        }
    ]
    doc = pdf(load(data))
    text = "\n".join(p.get_text() for p in doc)
    for i in range(8):
        assert f"VALUE-{i}" in text
    assert "Column 7" in text


def test_fixed_json_has_identical_pixels(reports):
    first = pdf(reports["cll-genie-positive"])
    second = pdf(reports["cll-genie-positive"])
    assert len(first) == len(second)
    assert all(a.get_pixmap().samples == b.get_pixmap().samples for a, b in zip(first, second))


def test_normalized_json_is_portable_for_pdf(reports):
    serialized = reports["pgx"].model_dump_json()
    document = ReportLoader().loads(serialized)
    assert json.loads(serialized)["sections"][0]["rows"]
    assert "DPYD" in "\n".join(p.get_text() for p in pdf(document))


@pytest.mark.parametrize(
    "page_size,width,height",
    [
        ("A1", 594, 841),
        ("A2", 420, 594),
        ("A3", 297, 420),
        ("A4", 210, 297),
        ("Letter", 215.9, 279.4),
        ("Legal", 215.9, 355.6),
    ],
)
def test_named_paper_sizes(payloads, load, page_size, width, height):
    data = payloads["pgx"]
    data["presentation"]["page_size"] = page_size
    data["sections"] = []
    document = pdf(load(data))
    assert document[0].rect.width == pytest.approx(width * 72 / 25.4, abs=0.02)
    assert document[0].rect.height == pytest.approx(height * 72 / 25.4, abs=0.02)


@pytest.mark.parametrize(
    "orientation,width,height", [(None, 320, 200), ("portrait", 200, 320), ("landscape", 320, 200)]
)
def test_custom_paper_dimensions_and_orientation(payloads, load, orientation, width, height):
    data = payloads["pgx"]
    data["presentation"].update(
        page_size="custom", custom_width_mm=320, custom_height_mm=200, orientation=orientation
    )
    data["sections"] = []
    document = pdf(load(data))
    assert document[0].rect.width == pytest.approx(width * 72 / 25.4, abs=0.02)
    assert document[0].rect.height == pytest.approx(height * 72 / 25.4, abs=0.02)


@pytest.mark.parametrize("wide", [False, True])
def test_summary_markdown_table_is_compact_and_wraps(payloads, load, wide):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "summary",
            "key": "summary",
            "format": "markdown",
            "text": "| Label | Value |\n|---|---|\n| x | "
            + ("LongUnbrokenWord" * 80 if wide else "y")
            + " END-MARKER |",
        }
    ]
    from weasyprint import HTML
    from weasyprint.formatting_structure.boxes import TableBox

    from smd_reports.rendering import offline_fetcher

    rendered = HTML(
        string=ReportRenderer().render_html(load(data)), url_fetcher=offline_fetcher
    ).render()
    document = pymupdf.open(stream=rendered.write_pdf(), filetype="pdf")
    assert any("END-MARKER" in page.get_text() for page in document)
    # Inspect the actual Markdown table, excluding header tables and the yellow outer box.
    tables = [
        (page, box)
        for page in rendered.pages
        for box in page._page_box.descendants()
        if isinstance(box, TableBox) and box.element.get("class") is None
    ]
    assert tables
    for page, table in tables:
        assert table.position_x >= 45 / 0.75
        assert table.position_x + table.width <= page.width - 45 / 0.75
        if not wide:
            assert table.width < 180 / 0.75
        else:
            assert table.height > 50 / 0.75


def test_cnv_plot_is_embedded_and_fits_the_report_page(reports):
    document = pdf(reports["coyote3-dna"])
    page = next(page for page in document if "SYNTHETIC COPY-NUMBER PROFILE" in page.get_text())
    assert "Syntetisk kopietalsprofil" in page.get_text()
    for block in page.get_text("blocks"):
        assert block[0] >= 40 and block[2] <= page.rect.width - 39


@pytest.mark.parametrize("format,extension", [("PNG", "png"), ("TIFF", "tif"), ("GIF", "gif")])
def test_raster_plots_fit_page_and_keep_caption(payloads, load, tmp_path, format, extension):
    from PIL import Image

    path = tmp_path / ("portrait." + extension)
    Image.new("RGB", (100, 500), (20, 90, 180)).save(path, format=format)
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "image",
            "key": "plot",
            "heading": "Plot",
            "source": str(path),
            "caption": "PLOT-CAPTION",
            "max_height_mm": 100,
        }
    ]
    document = pdf(load(data))
    page = next(page for page in document if "PLOT-CAPTION" in page.get_text())
    rectangles = [rect for item in page.get_images() for rect in page.get_image_rects(item[0])]
    assert rectangles
    assert all(rect.x0 >= 45 and rect.x1 <= page.rect.width - 45 for rect in rectangles)
    assert all(rect.height <= 100 * 72 / 25.4 + 1 for rect in rectangles)


def test_pdf_includes_automatically_computed_rendering_metadata(reports):
    document = pdf(reports["pgx"])
    kind, reference = document.xref_get_key(-1, "Info")
    assert kind == "xref"
    metadata = document.xref_object(int(reference.split()[0]))
    assert "smd-reports" in metadata
    assert reports["pgx"].template_version in metadata
