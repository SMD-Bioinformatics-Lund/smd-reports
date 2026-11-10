"""Automatically populated metadata, paper settings and explicit text blocks."""

import json

import pytest
from pydantic import ValidationError

from smd_reports import ReportLoader, ReportRenderer, __version__


def test_provenance_accepts_context_but_computes_rendering_versions(payloads, load):
    data = payloads["pgx"]
    data["provenance"] = {
        "application_name": "Example app",
        "application_version": "5.2",
        "pipeline_name": "Example pipeline",
        "pipeline_version": "3.1",
        "assay_name": "Example assay",
    }
    document = load(data)
    assert document.rendering_metadata["package_version"] == __version__
    assert document.rendering_metadata["template_version"] == document.template_version
    assert document.rendering_metadata["pipeline_version"] == "3.1"
    assert json.loads(document.model_dump_json())["provenance"] == data["provenance"]
    assert ReportLoader().loads(document.model_dump_json()) == document
    html = ReportRenderer().render_html(document)
    assert 'name="smd-reports:package_version" content="' + __version__ + '"' in html
    assert 'content="Example pipeline"' in html
    properties = ReportLoader().schema()["$defs"]["Provenance"]["properties"]
    assert set(properties) == set(data["provenance"])


@pytest.mark.parametrize(
    "field",
    [
        "package_version",
        "template_version",
        "plugin_version",
        "schema_version",
        "configuration_version",
        "source_revision",
    ],
)
def test_rendering_metadata_cannot_be_supplied_by_input(payloads, load, field):
    data = payloads["pgx"]
    data["provenance"][field] = "manual"
    with pytest.raises(ValidationError):
        load(data)


@pytest.mark.parametrize("field", ["supported_analyses", "enabled_analyses"])
def test_analysis_selectors_are_not_part_of_input(payloads, load, field):
    data = payloads["pgx"]
    data[field] = ["SNV"]
    with pytest.raises(ValidationError):
        load(data)


@pytest.mark.parametrize("language", ["en", "sv"])
@pytest.mark.parametrize(
    "kind,en,sv",
    [
        ("summary", "Conclusion", "Slutsats"),
        ("description", "Analysis description", "Analysbeskrivning"),
        ("references", "References", "Referenser"),
    ],
)
def test_text_block_default_headings_and_markdown(payloads, load, language, kind, en, sv):
    data = payloads["pgx"]
    data["language"] = language
    data["sections"] = [
        {
            "kind": kind,
            "key": "block",
            "format": "markdown",
            "text": {"en": "### Method\n**Reviewed** text.", "sv": "### Metod\n**Granskad** text."},
        }
    ]
    html = ReportRenderer().render_html(load(data))
    assert f'class="report_header">{en if language == "en" else sv}</h2>' in html
    assert "<h3>" + ("Method" if language == "en" else "Metod") + "</h3>" in html
    assert (
        "<strong>Reviewed</strong>" if language == "en" else "<strong>Granskad</strong>"
    ) in html


def test_plain_blocks_and_custom_heading_are_literal(payloads, load):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "description",
            "key": "description",
            "heading": {"en": "Custom heading", "sv": "Egen rubrik"},
            "format": "plain",
            "text": "**Literal** <script>bad()</script>",
        }
    ]
    html = ReportRenderer().render_html(load(data))
    assert "Egen rubrik" in html and "**Literal**" in html
    assert "&lt;script&gt;" in html and "<script>" not in html


@pytest.mark.parametrize(
    "presentation",
    [
        {"page_size": "custom"},
        {"page_size": "custom", "custom_width_mm": 200},
        {"page_size": "custom", "custom_width_mm": -1, "custom_height_mm": 300},
        {"page_size": "A4", "custom_width_mm": 200, "custom_height_mm": 300},
        {"page_size": "custom", "custom_width_mm": 40, "custom_height_mm": 300},
        {"page_size": "custom", "custom_width_mm": 200, "custom_height_mm": 70},
    ],
)
def test_invalid_paper_dimensions_fail(payloads, load, presentation):
    data = payloads["pgx"]
    data["presentation"] = presentation
    with pytest.raises(ValidationError):
        load(data)


@pytest.mark.parametrize(
    "name,template_name",
    [
        ("generic", "Report"),
        ("coyote3-dna", "Coyote3 DNA"),
        ("coyote3-rna", "Coyote3 RNA"),
        ("genexus", "Genexus"),
        ("cll-genie-positive", "CLL Genie"),
        ("pgx", "PGx"),
    ],
)
@pytest.mark.parametrize("language,label", [("en", "Template"), ("sv", "Mall")])
def test_footer_identifies_template_and_package_versions(
    payloads, load, name, template_name, language, label
):
    data = payloads[name]
    data["language"] = language
    document = load(data)
    assert document.template_name == template_name
    displayed_name = "Rapport" if name == "generic" and language == "sv" else template_name
    expected = f"{displayed_name} · {label} {document.template_version} · smd-reports {__version__}"
    html = ReportRenderer().render_html(document)
    # The screen and repeating PDF footers must show the same version information.
    assert html.count(expected) == 2


def test_coyote_dna_and_rna_template_revisions_are_independent(monkeypatch, reports):
    from copy import deepcopy

    from smd_reports.core import template_versions

    revisions = deepcopy(template_versions())
    revisions["coyote3"] = {"dna": "3.0.0", "rna": "4.2.0"}
    monkeypatch.setattr("smd_reports.core.template_versions", lambda: revisions)
    for name, revision in [("coyote3-dna", "3.0.0"), ("coyote3-rna", "4.2.0")]:
        report = reports[name]
        html = ReportRenderer().render_html(report)
        assert report.template_version == revision
        assert f"Mall {revision}" in html
        assert f"smd-reports {__version__}" in html
        assert report.rendering_metadata["package_version"] == __version__
