"""PDF content, pagination, typography and deterministic raster output."""

import io
import re

import pytest

from smd_reports import Column, ReportConfig, ReportRenderer, TableSection, TextSection

pytest.importorskip("weasyprint")
pymupdf = pytest.importorskip("pymupdf")
pypdf = pytest.importorskip("pypdf")


def pdf_document(builder):
    return pypdf.PdfReader(io.BytesIO(builder.render_pdf()))


@pytest.mark.parametrize("name", ["coyote3-dna", "genexus", "cll-genie-positive", "pgx"])
@pytest.mark.parametrize("long_summary", [False, True])
def test_yellow_summary_has_page_breaks_before_and_after(reports, name, long_summary):
    document = reports[name].build()
    document.sections = [
        TextSection(key="before", title="Before", text="BEFORE-SUMMARY-MARKER"),
        TextSection(
            key="summary",
            title="Summary",
            conclusion=True,
            text="SUMMARY-BEGIN-MARKER\n"
            + ("Reviewed narrative.\n" * (180 if long_summary else 1))
            + "SUMMARY-END-MARKER",
        ),
        TextSection(key="after", title="After", text="AFTER-SUMMARY-MARKER"),
    ]
    reader = pypdf.PdfReader(io.BytesIO(ReportRenderer().render_pdf(document)))

    def page_for(marker):
        return next(
            index for index, page in enumerate(reader.pages) if marker in page.extract_text()
        )

    assert page_for("SUMMARY-BEGIN-MARKER") > page_for("BEFORE-SUMMARY-MARKER")
    assert page_for("AFTER-SUMMARY-MARKER") > page_for("SUMMARY-END-MARKER")
    if long_summary:
        assert page_for("SUMMARY-END-MARKER") > page_for("SUMMARY-BEGIN-MARKER")


def test_summary_page_breaks_cannot_be_disabled():
    with pytest.raises(ValueError):
        ReportConfig(title="Report", summary_new_page=False)


def footer_images(page):
    """Locate supplied footer artwork in the rendered page."""
    return [rect for rect in page.search_for("PLACEHOLDER") if rect.y0 > page.rect.height - 110] + [
        rect
        for image in page.get_images()
        for rect in page.get_image_rects(image[0])
        if rect.y0 > page.rect.height - 110
    ]


def test_all_application_pdfs_have_identity_content_and_fonts(reports):
    for name, builder in reports.items():
        pdf = pdf_document(builder)
        text = "\n".join(page.extract_text() for page in pdf.pages)
        assert "SYNTHETIC-001" in text, name
        assert "Exempel på granskad slutsats" in text, name
        assert "<PATIENT_NAME>" in text, name
        for index, page in enumerate(pdf.pages):
            assert "SYNTHETIC-001" in page.extract_text(), (name, index)
            assert re.search(rf"Sida\s+{index + 1}\s+av\s+{len(pdf.pages)}", page.extract_text())
            assert round(float(page.mediabox.width)) == 595
            assert round(float(page.mediabox.height)) == 842
        fonts = pdf.pages[0]["/Resources"]["/Font"].get_object()
        assert any(
            "Source-Sans-3" in str(font.get_object().get("/BaseFont")) for font in fonts.values()
        )
        for font in fonts.values():
            descendants = font.get_object().get("/DescendantFonts", [])
            for descendant in descendants:
                descriptor = descendant.get_object()["/FontDescriptor"].get_object()
                assert "/FontFile2" in descriptor or "/FontFile3" in descriptor


def test_long_table_repeats_headings_and_does_not_lose_rows(reports):
    document = reports["coyote3-dna"].build()
    document.sections = [
        TableSection(
            key="long",
            title="Long synthetic table",
            columns=[
                Column(key="id", label="Synthetic row"),
                Column(key="text", label="Description"),
            ],
            rows=[
                {"id": f"ROW-{index:03d}", "text": "LongIdentifier" * 12} for index in range(100)
            ],
        )
    ]
    pdf = pypdf.PdfReader(io.BytesIO(ReportRenderer().render_pdf(document)))
    assert len(pdf.pages) > 2
    all_text = "\n".join(page.extract_text() for page in pdf.pages)
    for index in range(100):
        assert all_text.count(f"ROW-{index:03d}") == 1
    for page in pdf.pages:
        assert "Synthetic row" in page.extract_text()


def test_fixed_inputs_have_identical_pixels(reports):
    builder = reports["cll-genie-positive"]
    first = pymupdf.open(stream=builder.render_pdf(), filetype="pdf")
    second = pymupdf.open(stream=builder.render_pdf(), filetype="pdf")
    assert len(first) == len(second)
    for a, b in zip(first, second):
        assert a.get_pixmap().samples == b.get_pixmap().samples


def test_summary_new_page_and_content_within_print_area(reports):
    document = pymupdf.open(stream=reports["coyote3-dna"].render_pdf(), filetype="pdf")
    summary_pages = [index for index, page in enumerate(document) if "Slutsats" in page.get_text()]
    assert summary_pages and summary_pages[0] > 0
    for page in document:
        for block in page.get_text("blocks"):
            x0, y0, x1, y1 = block[:4]
            assert x0 >= 40 and x1 <= page.rect.width - 39
            assert y0 >= 0 and y1 <= page.rect.height


def test_expanded_center_and_metadata_fit_and_repeat(reports):
    from smd_reports import CoyoteData, CoyoteReport, ReportConfig

    source = reports["coyote3-dna"]
    values = source.data.model_dump()
    values["metadata"]["fields"] += [
        {"label": f"Field {index}", "value": "Synthetic"} for index in range(12)
    ]
    values["summary"] = "\n\n".join(f"Paragraph {i}: reviewed text." for i in range(100))
    report = CoyoteReport(
        CoyoteData.model_validate(values),
        ReportConfig(title="Extended report", header_height_mm=100),
    )
    pdf = pymupdf.open(stream=report.render_pdf(), filetype="pdf")
    text = "\n".join(page.get_text() for page in pdf)
    assert "Paragraph 99" in text
    for page in pdf:
        assert "demo@example.org" in page.get_text()
        assert "Field 11" in page.get_text()
        artwork = footer_images(page)
        assert artwork and all(rect.y1 <= page.rect.height for rect in artwork)
        for block in page.get_text("blocks"):
            assert block[1] >= 0 and block[3] <= page.rect.height


def test_accreditation_footer_is_excluded_when_ineligible(reports):
    document = reports["genexus"].build()
    document.branding.accredited = False
    pdf = pymupdf.open(stream=ReportRenderer().render_pdf(document), filetype="pdf")
    assert all(not footer_images(page) for page in pdf)


def test_clinical_skeleton_preserves_header_and_footer_positions(reports):
    report = reports["coyote3-dna"]
    pdf = pymupdf.open(stream=report.render_pdf(), filetype="pdf")
    for page in pdf:
        positions = [
            page.search_for(label)[0] for label in ("Patientnamn", "Personnummer", "Prov-ID")
        ]
        assert max(rect.y0 for rect in positions) - min(rect.y0 for rect in positions) < 1
        assert positions[0].x0 < positions[1].x0 < positions[2].x0
        logo = footer_images(page)[0]
        assert logo.x0 < 60 and logo.y1 <= page.rect.height
        version = page.search_for("DNA template")[0]
        assert version.x0 > page.rect.width * 0.65
        assert "schema 1" not in page.get_text()
    assert "ANALYSRAPPORT" in pdf[0].get_text()
    assert "PROVINFORMATION" in pdf[0].get_text()
