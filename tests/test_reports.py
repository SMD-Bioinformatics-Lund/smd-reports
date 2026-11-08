"""JSON document composition, validation, localization and offline output."""

import json

import pytest
from pydantic import ValidationError

from smd_reports import ReportLoader, ReportRenderer, Theme
from smd_reports.rendering import offline_fetcher


@pytest.mark.parametrize(
    "name", ["coyote3-dna", "coyote3-rna", "genexus", "cll-genie-positive", "pgx"]
)
def test_examples_preserve_content_and_round_trip(reports, name):
    document = reports[name]
    renderer = ReportRenderer()
    html = renderer.render_html(document)
    assert document.metadata.report_id in html
    assert "&lt;PATIENT_NAME&gt;" in html
    assert "Exempel på granskad slutsats" in html
    assert "data:font/woff2;base64," in html
    assert "fetch(" not in html
    if name == "cll-genie-positive":
        assert "submission_demo" in html and "Rapporttyp" in html
    restored = ReportLoader().loads(document.model_dump_json())
    assert restored == document
    assert renderer.render_html(restored) == html


def test_enabled_analyses_and_sections_are_independent(payloads, load):
    payload = payloads["coyote3-dna"]
    payload["enabled_analyses"] = ["SNV"]
    payload["sections"][0]["enabled"] = False
    document = load(payload)
    html = ReportRenderer().render_html(document)
    assert 'id="snvs"' not in html
    assert 'id="cnvs"' not in html
    assert 'id="snv-details"' in html
    assert 'id="summary"' in html
    # Normalizing retains disabled data and its configuration.
    assert any(section.key == "cnvs" for section in document.sections)


@pytest.mark.parametrize("change", ["unsupported", "duplicate", "section", "timezone", "schema"])
def test_invalid_document_rejected(payloads, load, change):
    data = payloads["coyote3-dna"]
    if change == "unsupported":
        data["enabled_analyses"] = ["UNKNOWN"]
    elif change == "duplicate":
        data["supported_analyses"] = ["SNV", "SNV"]
    elif change == "section":
        data["sections"].append(data["sections"][0])
    elif change == "timezone":
        data["report"]["generated_at"] = "2026-01-01T00:00:00"
    else:
        data["schema_version"] = 1
    with pytest.raises(ValidationError):
        load(data)


@pytest.mark.parametrize("language", ["en", "sv"])
def test_custom_labels_titles_and_values_are_localized(payloads, load, language):
    data = payloads["pgx"]
    data["language"] = language
    data["title"] = {"en": "English title", "sv": "Svensk titel"}
    data["sections"] = [
        {
            "kind": "table",
            "key": "custom",
            "title": {"en": "Results", "sv": "Resultat"},
            "columns": [{"label": {"en": "New column", "sv": "Ny kolumn"}}],
            "rows": [[{"en": "English value", "sv": "Svenskt värde"}]],
        }
    ]
    html = ReportRenderer().render_html(load(data))
    expected = (
        ["English title", "New column", "English value", "Page "]
        if language == "en"
        else ["Svensk titel", "Ny kolumn", "Svenskt värde", "Sida "]
    )
    assert all(value in html for value in expected)


def test_missing_translation_falls_back_to_english(payloads, load):
    data = payloads["pgx"]
    data["title"] = {"en": "Fallback title"}
    assert "Fallback title" in ReportRenderer().render_html(load(data))


def test_markdown_and_plain_text_are_safe(payloads, load):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "text",
            "key": "text",
            "text": {"sv": '**Granskad** <script>bad()</script><img src="https://example.org/a">'},
            "format": "markdown",
        },
        {
            "kind": "table",
            "key": "table",
            "columns": [{"label": "<HEADER>"}],
            "rows": [["<VALUE>"]],
        },
    ]
    html = ReportRenderer().render_html(load(data))
    assert "<strong>Granskad</strong>" in html
    assert "<script>" not in html and '<img src="https:' not in html
    assert "&lt;HEADER&gt;" in html and "&lt;VALUE&gt;" in html


def test_theme_registry_is_isolated(reports):
    first, second = ReportRenderer(), ReportRenderer()
    custom = Theme(
        name="custom", heading="#176B68", accent="#176B68", tint="#edf7f5", rule_end="#176B68"
    )
    first.register_theme(custom)
    with pytest.raises(ValueError):
        first.register_theme(custom)
    with pytest.raises(ValueError):
        second.render_html(reports["pgx"], theme="custom")
    assert "#176B68" in first.render_html(reports["pgx"], theme="custom")


@pytest.mark.parametrize(
    "url", ["https://example.org/a.png", "file:///etc/passwd", "ftp://example.org/a"]
)
def test_renderer_rejects_external_resources(url):
    with pytest.raises(ValueError):
        offline_fetcher(url)


def test_public_input_is_json_only(payloads):
    with pytest.raises(TypeError):
        ReportLoader().loads(payloads["pgx"])
    import smd_reports

    assert not hasattr(smd_reports, "PGxFiles")
    assert not hasattr(smd_reports, "CoyoteData")
    assert "schema_version" not in json.dumps(ReportLoader().schema())
