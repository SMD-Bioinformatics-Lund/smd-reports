"""Reject malformed assets and layout settings before producing report output."""

import base64
import json

import pytest
from pydantic import ValidationError

from smd_reports import ReportAssetError, ReportLoader, Theme
from smd_reports.cli import main


@pytest.mark.parametrize(
    "reference", ["", " ", "https://example.org/a.png", "file:a.png", "a\0.png"]
)
def test_image_references_reject_empty_remote_and_invalid_paths(payloads, load, reference):
    data = payloads["generic"]
    data["sections"] = [{"kind": "image", "key": "plot", "source": reference}]
    with pytest.raises(ValidationError):
        load(data)


@pytest.mark.parametrize(
    "source",
    [
        "data:image/png;base64,",
        "data:image/png;base64,%%%%",
        "data:application/pdf;base64,AAAA",
        "data:image/png;base64",
        "data:image/svg+xml;base64," + base64.b64encode(b"<svg>").decode(),
        "data:image/svg+xml;base64," + base64.b64encode(b"<html/>").decode(),
        "data:image/svg+xml;base64," + base64.b64encode(b"<svg><script/></svg>").decode(),
    ],
)
def test_malformed_embedded_images_fail_at_json_boundary(payloads, load, source):
    data = payloads["generic"]
    data["sections"] = [{"kind": "image", "key": "plot", "source": source}]
    with pytest.raises(ValidationError):
        load(data)


def test_svg_frame_selection_reports_the_field(payloads, load):
    data = payloads["generic"]
    data["sections"] = [
        {"kind": "image", "key": "plot", "source": "../assets/cnv-example.svg", "frame": 1}
    ]
    with pytest.raises(ReportAssetError, match=r"sections\[0\]\.source"):
        load(data)


def test_unsupported_asset_extension_and_cli_errors_do_not_leak_paths(tmp_path, payloads, capsys):
    data = payloads["generic"]
    data["branding"] = {"center_logo": "/PRIVATE-CENTER/logo.pdf"}
    source = tmp_path / "input.json"
    source.write_text(json.dumps(data))
    assert main(["validate", str(source)]) == 2
    error = capsys.readouterr().err
    assert "branding.center_logo" in error
    assert "PRIVATE-CENTER" not in error and "logo.pdf" not in error


@pytest.mark.parametrize("setting", ["duplicate-formats", "overflowing-widths"])
def test_invalid_layout_settings_cannot_reach_css(payloads, load, setting):
    data = payloads["generic"]
    if setting == "duplicate-formats":
        data["presentation"] = {"accepted_image_formats": ["png", "png"]}
    else:
        data["sections"] = [
            {
                "kind": "table",
                "key": "results",
                "columns": {"en": ["A", "B"], "sv": ["A", "B"]},
                "column_options": {"0": {"width": 1e308}, "1": {"width": 1e308}},
                "rows": [[1, 2]],
            }
        ]
    with pytest.raises(ValidationError):
        load(data)


@pytest.mark.parametrize("color", ["red", "#123", "#123456;display:none", "#GGGGGG"])
def test_theme_colors_require_hex_and_cannot_inject_css(color):
    with pytest.raises(ValidationError):
        Theme(name="custom", heading=color, accent="#112233", tint="#FFFFFF", rule_end="#112233")


def test_schema_rejects_unknown_preset():
    with pytest.raises(ValueError):
        ReportLoader().schema("unknown")
