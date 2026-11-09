"""Visible placeholders survive escaping, Markdown and later HTML replacement."""

from html import escape

import pytest

from smd_reports import ReportRenderer
from smd_reports.rendering import format_markdown


@pytest.mark.parametrize(
    "source,expected",
    [
        ("<PATIENT_NAME>", "<p>&lt;PATIENT_NAME&gt;</p>"),
        ("<PERSONAL_IDENTITY_NUMBER>", "<p>&lt;PERSONAL_IDENTITY_NUMBER&gt;</p>"),
        ("<REGISTRATION_DATE>", "<p>&lt;REGISTRATION_DATE&gt;</p>"),
        ("<SAMPLE_TYPE>", "<p>&lt;SAMPLE_TYPE&gt;</p>"),
        ("<NAME>", "<p>&lt;NAME&gt;</p>"),
        ("<SAMPLE_2_ID>", "<p>&lt;SAMPLE_2_ID&gt;</p>"),
        ("**<PATIENT_NAME>**", "<strong>&lt;PATIENT_NAME&gt;</strong>"),
        ("`<PATIENT_NAME>`", "<code>&lt;PATIENT_NAME&gt;</code>"),
        ("    <PATIENT_NAME>", "<pre><code>&lt;PATIENT_NAME&gt;"),
        ("&lt;PATIENT_NAME&gt;", "<p>&lt;PATIENT_NAME&gt;</p>"),
        ("| Patient |\n| --- |\n| <PATIENT_NAME> |", "<td>&lt;PATIENT_NAME&gt;</td>"),
    ],
)
def test_markdown_preserves_placeholder_text_without_double_escaping(source, expected):
    html = str(format_markdown(source))
    assert expected in html
    assert "&amp;lt;" not in html
    assert "<PATIENT_NAME>" not in html


@pytest.mark.parametrize(
    "source,expected",
    [
        ("<H1>Heading</H1>", "<h1>Heading</h1>"),
        ('<STRONG onclick="alert(1)">Reviewed</STRONG>', "<strong>Reviewed</strong>"),
    ],
)
def test_placeholder_handling_preserves_allowed_html_and_removes_attributes(source, expected):
    html = str(format_markdown(source))
    assert expected in html
    assert "onclick" not in html


def test_placeholder_handling_does_not_allow_html_or_script_injection():
    html = str(
        format_markdown(
            "<PATIENT_NAME><script>alert(1)</script><img src=x onerror=alert(1)>"
            '<PATIENT_NAME onclick="alert(1)">'
        )
    )
    assert "&lt;PATIENT_NAME&gt;" in html
    assert "<script" not in html.lower() and "<img" not in html.lower()
    assert "onclick" not in html and "onerror" not in html


@pytest.mark.parametrize("kind", ["table", "details", "grid"])
def test_placeholders_survive_markdown_column_values(payloads, load, kind):
    data = payloads["pgx"]
    section = {
        "kind": kind,
        "key": "placeholders",
        "columns": {"en": ["Patient"]},
        "column_options": {"0": {"format": "markdown"}},
        "rows": [["**<PATIENT_NAME>**"]],
    }
    if kind == "grid":
        section.update(grid_columns=2, layout=[{"cells": [{"column": 0, "span": 2}]}])
    data["sections"] = [section]
    html = ReportRenderer().render_html(load(data))
    assert "<strong>&lt;PATIENT_NAME&gt;</strong>" in html


@pytest.mark.parametrize("application", ["generic", "coyote3", "genexus", "cll_genie", "pgx"])
@pytest.mark.parametrize("format", ["plain", "markdown"])
def test_metadata_and_summary_placeholders_use_the_same_html_token(
    payloads, load, application, format
):
    data = payloads["pgx"]
    data["application"] = application
    data["sections"] = [
        {
            "kind": "summary",
            "key": "summary",
            "format": format,
            "text": {"en": "Patient: <PATIENT_NAME>", "sv": "Patient: <PATIENT_NAME>"},
        }
    ]
    report = load(data)
    html = ReportRenderer().render_html(report)
    assert html.count("&lt;PATIENT_NAME&gt;") == 3
    assert "&amp;lt;PATIENT_NAME" not in html and "<PATIENT_NAME>" not in html
    assert report.metadata.fields[0].value == "<PATIENT_NAME>"


def test_supplied_patient_value_is_displayed_without_adding_placeholders(payloads, load):
    data = payloads["pgx"]
    data["report"]["fields"][0]["value"] = "Example & Demo"
    data["sections"] = []
    html = ReportRenderer().render_html(load(data))
    assert "Example &amp; Demo" in html
    assert "&lt;PATIENT_NAME&gt;" not in html


def test_markdown_placeholders_can_be_replaced_in_html_before_pdf(payloads, load):
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    from weasyprint import HTML

    from smd_reports.rendering import _offline_url_fetcher

    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "summary",
            "key": "summary",
            "format": "markdown",
            "text": "Patient: **<PATIENT_NAME>**\n\n| Patient |\n| --- |\n| <PATIENT_NAME> |",
        }
    ]
    html = ReportRenderer().render_html(load(data))
    before = HTML(string=html, url_fetcher=_offline_url_fetcher()).write_pdf()
    replacement = "Example & Demo"
    html = html.replace("&lt;PATIENT_NAME&gt;", escape(replacement))
    after = HTML(string=html, url_fetcher=_offline_url_fetcher()).write_pdf()
    with pymupdf.open(stream=before, filetype="pdf") as document:
        page = next(page for page in document if "Patient:" in page.get_text())
        assert page.get_text().count("<PATIENT_NAME>") == 3
    with pymupdf.open(stream=after, filetype="pdf") as document:
        assert all("<PATIENT_NAME>" not in page.get_text() for page in document)
        page = next(page for page in document if "Patient:" in page.get_text())
        text = page.get_text()
        assert text.count(replacement) == 3
