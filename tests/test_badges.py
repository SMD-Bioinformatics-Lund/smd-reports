"""Optional tier and custom badges across shared report table components."""

import json

import pytest
from pydantic import ValidationError

from smd_reports import ReportLoader, ReportRenderer
from smd_reports.badges import BadgeStyle, badge_colors

COLORS = {"tier1": "#af6246", "tier2": "#ae8540", "tier3": "#4f7d9f", "tier4": "#4b8b76"}


def badge_report(payloads, load, kind="table", badge=None, *, enabled=True, rows=None, **settings):
    payload = payloads["generic"]
    section = {
        "kind": kind,
        "key": "badges",
        "columns": {"en": ["Assessment"]},
        "rows": rows or [["Strong clinical significance"]],
    }
    if enabled:
        section["column_options"] = {"0": {"badge": badge if badge is not None else {}}}
    if kind == "grid":
        section.update(grid_columns=2, layout=[{"cells": [{"column": 0, "span": 2}]}])
    payload.update(sections=[section], **settings)
    return load(payload)


@pytest.mark.parametrize("kind", ["table", "details", "grid"])
@pytest.mark.parametrize("preset,color", list(COLORS.items()))
def test_tier_styles_preserve_the_display_label_and_json(payloads, load, kind, preset, color):
    report = badge_report(payloads, load, kind, {"preset": preset})
    html = ReportRenderer().render_html(report)
    assert f"background-color: {color};" in html
    assert ">Strong clinical significance</span>" in html
    assert report.sections[0].rows == [["Strong clinical significance"]]
    restored = ReportLoader().loads(report.model_dump_json())
    assert ReportRenderer().render_html(restored) == html


def test_badge_omission_keeps_plain_text(payloads, load):
    html = ReportRenderer().render_html(badge_report(payloads, load, enabled=False))
    assert '<span class="report-badge"' not in html
    assert ">Strong clinical significance</td>" in html


@pytest.mark.parametrize("theme,color", [("cll_genie", "#7B4925"), ("pgx", "#176B68")])
def test_empty_badge_options_follow_the_selected_theme(payloads, load, theme, color):
    report = badge_report(payloads, load, theme=theme)
    assert f"background-color: {color};" in ReportRenderer().render_html(report)
    exported = json.loads(report.model_dump_json())
    assert exported["sections"][0]["column_options"]["0"]["badge"] == {}
    assert f"background-color: {color};" in ReportRenderer().render_html(
        ReportLoader().loads(report.model_dump_json())
    )
    assert "background-color: #665271;" in ReportRenderer().render_html(report, theme="coyote3")


def test_custom_subset_color_and_unlisted_values(payloads, load):
    report = badge_report(
        payloads,
        load,
        badge={"values": {"#2": {"color": "#123456"}}},
        rows=[["#2"], ["#8"], [None]],
    )
    html = ReportRenderer().render_html(report)
    assert html.count('<span class="report-badge"') == 1
    assert "background-color: #123456;" in html and ">#2</span>" in html
    assert ">#8</td>" in html and ">-</td>" in html


def test_value_maps_accept_presets_and_theme_defaults(payloads, load):
    report = badge_report(
        payloads,
        load,
        badge={"values": {"I": "tier1", "II": "tier2", "Reviewed": {}}},
        rows=[["I"], ["II"], ["Reviewed"], ["Unknown"]],
    )
    html = ReportRenderer().render_html(report)
    assert html.count('<span class="report-badge"') == 3
    assert "background-color: #af6246;" in html and "background-color: #ae8540;" in html
    assert "background-color: #435365;" in html
    assert ">Unknown</td>" in html


@pytest.mark.parametrize(
    "language,text,boolean", [("en", "Reviewed", "No"), ("sv", "Granskad", "Nej")]
)
def test_translations_escaping_and_scalar_values(payloads, load, language, text, boolean):
    report = badge_report(
        payloads,
        load,
        language=language,
        rows=[
            [{"en": "Reviewed", "sv": "Granskad"}],
            [False],
            [0],
            ["<PATIENT_NAME><script>"],
            [" "],
            [None],
            [""],
        ],
    )
    html = ReportRenderer().render_html(report)
    assert html.count('<span class="report-badge"') == 4
    assert f">{text}</span>" in html and f">{boolean}</span>" in html
    assert ">0</span>" in html and "&lt;PATIENT_NAME&gt;&lt;script&gt;</span>" in html
    assert "<script>" not in html


@pytest.mark.parametrize(
    "badge",
    [
        {"preset": "tier5"},
        {"color": "red"},
        {"color": "#abc"},
        {"color": "#123456;background:url(https://example.org)"},
        {"color": "url(file:///example)"},
        {"text_color": "red"},
        {"shape": "triangle"},
        {"preset": "tier1", "color": "#123456"},
        {"values": {"I": "unknown"}},
        {"values": {"I": {"preset": "tier9"}}},
        {"values": {"I": "tier1"}, "color": "#123456"},
    ],
)
def test_invalid_badge_options_are_rejected(payloads, load, badge):
    with pytest.raises(ValidationError):
        badge_report(payloads, load, badge=badge)


def test_foreground_uses_the_more_legible_black_or_white():
    assert badge_colors(BadgeStyle(color="#ffffff"), "#123456") == ("#ffffff", "#000000")
    assert badge_colors(BadgeStyle(color="#000000"), "#123456") == ("#000000", "#ffffff")


def test_badges_wrap_on_narrow_pages_and_render_as_pdf_text(payloads, load, caplog):
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    report = badge_report(
        payloads,
        load,
        badge={"preset": "tier1"},
        rows=[["Strong clinical significance with a longer supplied label"]],
        presentation={"page_size": "custom", "custom_width_mm": 100, "custom_height_mm": 210},
    )
    html = ReportRenderer().render_html(report)
    assert 'class="report-badge"' in html
    with caplog.at_level("WARNING", logger="weasyprint"):
        output = ReportRenderer().render_pdf(report)
    assert not any("unknown property" in record.getMessage() for record in caplog.records)
    with pymupdf.open(stream=output, filetype="pdf") as doc:
        assert "Strong clinical significance" in " ".join(doc[0].get_text().split())
        words = doc[0].get_text("words")
        assert all(40 <= word[0] < word[2] <= doc[0].rect.width - 40 for word in words)
        assert any(
            drawing.get("fill")
            and tuple(round(channel * 255) for channel in drawing["fill"]) == (175, 98, 70)
            for drawing in doc[0].get_drawings()
        )


def test_badges_are_literal_and_unmatched_values_keep_markdown(payloads, load):
    report = badge_report(
        payloads,
        load,
        badge={"values": {"**Reviewed**": "tier1"}},
        rows=[["**Reviewed**"], ["**Unlisted**"]],
    )
    report.sections[0].column_options["0"].format = "markdown"
    html = ReportRenderer().render_html(report)
    assert ">**Reviewed**</span>" in html
    assert "<strong>Unlisted</strong>" in html
    assert "<strong>Reviewed</strong>" not in html


@pytest.mark.parametrize("kind", ["table", "details", "grid"])
def test_badge_shape_defaults_and_per_value_overrides_round_trip(payloads, load, kind):
    report = badge_report(
        payloads,
        load,
        kind,
        {
            "shape": "circle",
            "values": {
                "I": "tier1",
                "II": {"preset": "tier2", "shape": "square"},
                "III": {"preset": "tier3", "shape": "rounded"},
                "IV": {"preset": "tier4"},
            },
        },
        rows=[["I"], ["II"], ["III"], ["IV"], ["Other"]],
    )
    renderer = ReportRenderer()
    html = renderer.render_html(report)
    assert html.count('class="report-badge report-badge-circle"') == 2
    assert (
        'class="report-badge report-badge-square" style="background-color: #ae8540; color: #ffffff;'
        in html
    )
    assert 'class="report-badge" style="background-color: #4f7d9f;' in html
    assert html.count(">Other</span>") == 0
    restored = ReportLoader().loads(report.model_dump_json())
    assert renderer.render_html(restored) == html


@pytest.mark.parametrize("shape", ["circle", "square"])
def test_short_tier_badges_render_with_equal_dimensions_in_print(payloads, load, shape):
    from smd_reports.rendering import _offline_url_fetcher

    weasyprint = pytest.importorskip("weasyprint")
    report = badge_report(payloads, load, badge={"preset": "tier3", "shape": shape}, rows=[["III"]])
    html = ReportRenderer().render_html(report)
    rendered = weasyprint.HTML(string=html, url_fetcher=_offline_url_fetcher()).render()
    (badge,) = [
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if type(box).__name__ == "InlineBlockBox"
        and box.element.get("class") == f"report-badge report-badge-{shape}"
    ]
    assert badge.border_width() == pytest.approx(badge.border_height())
    radius = badge.style["border_top_left_radius"][0]
    assert radius.value == (50 if shape == "circle" else 0)


@pytest.mark.parametrize("shape", ["circle", "square"])
def test_shaped_tier_badge_defaults_and_accepts_custom_text_color(shape):
    assert badge_colors(BadgeStyle(preset="tier2", shape=shape), "#123456") == (
        "#ae8540",
        "#ffffff",
    )
    assert badge_colors(
        BadgeStyle(preset="tier2", shape=shape, text_color="#112233"), "#123456"
    ) == ("#ae8540", "#112233")


def test_badge_map_inherits_and_overrides_text_color(payloads, load):
    report = badge_report(
        payloads,
        load,
        badge={
            "shape": "circle",
            "text_color": "#112233",
            "values": {"I": "tier1", "II": {"preset": "tier2", "text_color": "#223344"}},
        },
        rows=[["I"], ["II"]],
    )
    html = ReportRenderer().render_html(report)
    assert 'background-color: #af6246; color: #112233;">I' in html
    assert 'background-color: #ae8540; color: #223344;">II' in html
    assert ReportLoader().loads(report.model_dump_json()) == report
