"""Independent presentation choices and compatibility with existing report presets."""

import json

import pytest
from pydantic import ValidationError

from smd_reports import ReportInputError, ReportLoader, ReportRenderer, Theme
from smd_reports.cli import main


@pytest.mark.parametrize(
    "name", ["generic", "coyote3-dna", "coyote3-rna", "genexus", "cll-genie-positive", "pgx"]
)
def test_named_presets_preserve_legacy_rendering_and_round_trip(payloads, load, name):
    payload = payloads[name]
    legacy = load(payload)
    payload["preset"] = payload.pop("application", "generic")
    current = load(payload)
    renderer = ReportRenderer()
    assert current.preset_name == legacy.preset_name
    assert current.template_version == legacy.template_version
    assert renderer.render_html(current) == renderer.render_html(legacy)
    restored = ReportLoader().loads(current.model_dump_json())
    assert renderer.render_html(restored) == renderer.render_html(current)


@pytest.mark.parametrize(
    "language,name,heading",
    [("en", "Example tool", "Document details"), ("sv", "Exempelverktyg", "Dokumentinformation")],
)
def test_generic_report_can_select_branding_theme_and_layout(
    payloads, load, language, name, heading
):
    payload = payloads["generic"]
    payload.update(
        language=language,
        theme="pgx",
        layout={
            "header": "branded",
            "repeat_title": True,
            "metadata_borders": True,
            "black_title": True,
            "metadata_heading": {"en": "Document details", "sv": "Dokumentinformation"},
            "document_label": {"en": "Custom report", "sv": "Egen rapport"},
        },
    )
    payload["branding"].update(
        application_name={"en": "Example tool", "sv": "Exempelverktyg"},
        application_logo="../assets/center-example.svg",
    )
    report = load(payload)
    html = ReportRenderer().render_html(report)
    assert report.preset_name == "generic" and report.theme_name == "pgx"
    assert f'<strong class="application-name">{name}</strong>' in html
    assert "report-application-logo" in html and "data:image/svg+xml;base64," in html
    assert heading in html and "header-branded repeat-title black-title bordered-metadata" in html
    assert "#176B68" in html and '<meta name="smd-reports:theme" content="pgx">' in html
    restored = ReportLoader().loads(report.model_dump_json())
    assert ReportRenderer().render_html(restored) == html


def test_partial_layout_override_keeps_preset_defaults_after_export(payloads, load):
    payload = payloads["generic"]
    payload.update(
        preset="genexus", theme="cll_genie", layout={"metadata_heading": "Custom fields"}
    )
    report = ReportLoader().loads(load(payload).model_dump_json())
    assert report.resolved_layout.repeat_title is True
    assert report.resolved_layout.black_title is True
    assert report.resolved_layout.metadata_borders is True
    assert report.resolved_layout.metadata_heading == "Custom fields"
    assert report.theme_name == "cll_genie" and report.template_name == "Genexus"


def test_center_only_layout_can_hide_product_branding_for_any_preset(payloads, load):
    payload = payloads["coyote3-dna"]
    payload["layout"] = {"header": "center"}
    html = ReportRenderer().render_html(load(payload))
    assert '<div class="report-product-brand">' not in html
    assert '<div class="report-brand-rule"' in html
    assert 'class="center-logo"' in html
    assert 'class="accreditation"' in html


def test_custom_wordmark_is_escaped_and_does_not_inherit_a_preset_suffix(payloads, load):
    payload = payloads["coyote3-dna"]
    payload["branding"]["application_name"] = "<EXAMPLE_NAME>"
    report = load(payload)
    html = ReportRenderer().render_html(report)
    assert report.application_suffix == ""
    assert "&lt;EXAMPLE_NAME&gt;</strong>" in html
    payload["branding"]["application_suffix"] = "<2>"
    assert "<span>&lt;2&gt;</span>" in ReportRenderer().render_html(load(payload))


def test_json_theme_and_render_override_select_registered_themes(payloads, load):
    payload = payloads["generic"]
    payload["theme"] = "custom"
    report = load(payload)
    renderer = ReportRenderer()
    with pytest.raises(ReportInputError, match="Unknown theme"):
        renderer.render_html(report)
    renderer.register_theme(
        Theme(
            name="custom", heading="#123456", accent="#234567", tint="#ffffff", rule_end="#345678"
        )
    )
    assert "#123456" in renderer.render_html(report)
    html = renderer.render_html(report, theme="coyote3")
    assert '<meta name="smd-reports:theme" content="coyote3">' in html
    assert "#665271" in html and report.theme == "custom"


@pytest.mark.parametrize(
    "settings",
    [
        {"preset": "unknown"},
        {"theme": ""},
        {"layout": {"header": "coyote3"}},
        {"layout": {"summary_color": "red"}},
        {"application": "pgx", "preset": "coyote3"},
    ],
)
def test_invalid_presentation_settings_are_rejected(payloads, load, settings):
    payload = payloads["generic"]
    payload.update(settings)
    with pytest.raises(ValidationError):
        load(payload)


def test_preset_schema_and_cli_preserve_legacy_schema_calls(tmp_path):
    loader = ReportLoader()
    schema = loader.schema(preset="pgx")
    assert schema["properties"]["preset"]["const"] == "pgx"
    assert "preset" in schema["required"]
    assert loader.schema("pgx")["properties"]["application"]["const"] == "pgx"
    with pytest.raises(ReportInputError):
        loader.schema("pgx", preset="pgx")
    with pytest.raises(ReportInputError):
        loader.schema(preset="unknown")
    output = tmp_path / "schema.json"
    assert main(["schema", "--preset", "coyote3", "--output", str(output)]) == 0
    assert json.loads(output.read_text())["properties"]["preset"]["const"] == "coyote3"


@pytest.mark.parametrize("theme", ["generic", "coyote3", "genexus", "cll_genie", "pgx"])
def test_all_themes_keep_summary_design_and_page_breaks(payloads, load, theme):
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    from weasyprint import HTML

    from smd_reports.rendering import _offline_url_fetcher

    payload = payloads["generic"]
    payload.update(theme=theme, layout={"header": "branded", "repeat_title": True})
    payload["branding"]["application_name"] = "Example tool"
    payload["sections"] = [
        {"kind": "text", "key": "before", "text": "BEFORE-MARKER"},
        {"kind": "summary", "key": "summary", "text": "SUMMARY-MARKER"},
        {"kind": "text", "key": "after", "text": "AFTER-MARKER"},
    ]
    html = ReportRenderer().render_html(load(payload))
    rendered = HTML(string=html, url_fetcher=_offline_url_fetcher()).render()
    box = next(
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if box.element is not None
        and box.element.get("class") == "results_summary plain"
        and type(box).__name__ == "BlockBox"
    )
    assert box.border_left_width == 3
    assert tuple(box.style["background_color"].coordinates) == pytest.approx(
        (1, 249 / 255, 232 / 255)
    )
    assert tuple(box.style["border_left_color"].coordinates) == pytest.approx(
        (189 / 255, 161 / 255, 91 / 255)
    )
    with pymupdf.open(stream=rendered.write_pdf(), filetype="pdf") as pdf:
        pages = [page.get_text() for page in pdf]
        assert len(pages) == 3
        assert "BEFORE-MARKER" in pages[0] and "SUMMARY-MARKER" in pages[1]
        assert "AFTER-MARKER" in pages[2]


@pytest.mark.parametrize("preset", ["generic", "coyote3", "genexus", "cll_genie", "pgx"])
def test_header_separator_is_available_with_every_preset(payloads, load, preset):
    payload = payloads["generic"]
    payload["preset"] = preset
    report = load(payload)
    assert report.resolved_layout.header_rule is True
    html = ReportRenderer().render_html(report)
    assert html.count('<div class="report-brand-rule" aria-hidden="true"></div>') == 2


def test_header_separator_can_be_disabled_without_hiding_branding(payloads, load):
    payload = payloads["coyote3-dna"]
    payload["layout"] = {"header_rule": False}
    report = ReportLoader().loads(load(payload).model_dump_json())
    assert report.resolved_layout.header_rule is False
    html = ReportRenderer().render_html(report)
    assert '<div class="report-brand-rule"' not in html
    assert '<div class="report-product-brand">' in html
    assert 'class="center-logo"' in html
