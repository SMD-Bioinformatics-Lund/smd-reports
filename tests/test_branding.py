"""Offline artwork, generic public previews and configurable header/footer logos."""

import base64
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from smd_reports import ReportAssetError, ReportLoader, ReportRenderer
from smd_reports.assets import embed_image


def test_public_previews_embed_only_example_artwork():
    root = Path(__file__).parents[1]
    allowed = {path.read_bytes() for path in (root / "examples/assets").glob("*-example.svg")}
    assert len(allowed) == 3
    for path in (root / "examples/rendered").glob("*.html"):
        images = re.findall(r'src="data:image/[^,]+,([^\"]+)"', path.read_text())
        assert images
        assert all(base64.b64decode(image) in allowed for image in images)


@pytest.mark.parametrize("name", ["coyote3-dna", "cll-genie-positive", "genexus", "pgx"])
@pytest.mark.parametrize("with_logo", [True, False])
def test_application_identity_and_optional_logo(payloads, load, name, with_logo):
    data = payloads[name]
    data["branding"]["application_logo"] = data["branding"]["center_logo"] if with_logo else None
    report = load(data)
    html = ReportRenderer().render_html(report)
    branded = report.application in {"coyote3", "cll_genie"}
    assert ('class="report-product-brand"' in html) is branded
    assert ('class="report-application-logo"' in html) is (branded and with_logo)
    assert 'class="center-logo"' in html


@pytest.mark.parametrize("eligible", [False, True])
def test_accreditation_requires_both_flag_and_logo(payloads, load, eligible):
    data = payloads["pgx"]
    data["branding"]["accredited"] = eligible
    assert ('class="accreditation"' in ReportRenderer().render_html(load(data))) is eligible
    data["branding"]["accreditation_logo"] = None
    assert 'class="accreditation"' not in ReportRenderer().render_html(load(data))


@pytest.mark.parametrize(
    "content",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.org/a"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:url(file:///a)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><g onload="alert(1)"/></svg>',
        '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg>&x;</svg>',
        '<?xml-stylesheet href="https://example.org/a.css"?><svg/>',
    ],
)
def test_active_svg_rejected(payloads, load, content):
    data = payloads["pgx"]
    data["branding"]["center_logo"] = (
        "data:image/svg+xml;base64," + base64.b64encode(content.encode()).decode()
    )
    with pytest.raises(ValidationError):
        load(data)


def test_logo_paths_resolve_from_json_and_normalize_to_data_uris(tmp_path, payloads):
    data = payloads["pgx"]
    data["branding"] = {"center_logo": "logo.svg"}
    source = Path(__file__).parents[1] / "examples/assets/center-example.svg"
    (tmp_path / "logo.svg").write_bytes(source.read_bytes())
    import json

    path = tmp_path / "report.json"
    path.write_text(json.dumps(data))
    report = ReportLoader().load(path)
    (tmp_path / "logo.svg").unlink()
    restored = ReportLoader().loads(report.model_dump_json())
    assert restored == report
    assert report.branding.center_logo == embed_image(source)
    assert "data:image/svg+xml;base64," in ReportRenderer().render_html(restored)


def test_missing_and_relative_in_memory_assets_have_clear_errors(payloads):
    import json

    with pytest.raises(ReportAssetError, match="branding.center_logo"):
        ReportLoader().loads(json.dumps(payloads["pgx"]))
