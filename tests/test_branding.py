"""Center configuration, offline artwork and realistic report content."""

import base64
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from smd_reports import Branding, CoyoteData, CoyoteReport, FieldValue, ReportConfig
from smd_reports.assets import embed_image


def test_branding_has_no_institutional_defaults():
    branding = Branding()
    assert branding.organization == ""
    assert branding.application_logo is None
    assert branding.center_logo is None
    assert branding.accreditation_logo is None
    assert branding.accredited is False


def test_public_previews_embed_only_example_artwork():
    root = Path(__file__).parents[1]
    allowed = {path.read_bytes() for path in (root / "examples/assets").glob("*-example.svg")}
    assert len(allowed) == 3
    for path in (root / "examples/rendered").glob("*.html"):
        images = re.findall(r'src="data:image/[^,]+,([^\"]+)"', path.read_text())
        assert images
        assert all(base64.b64decode(image) in allowed for image in images), path.name


@pytest.mark.parametrize("name", ["coyote3-dna", "cll-genie-positive", "genexus", "pgx"])
@pytest.mark.parametrize("with_logo", [True, False])
def test_application_identity_and_optional_logo(reports, name, with_logo):
    report = reports[name].build()
    report.branding.application_logo = report.branding.center_logo if with_logo else None
    from smd_reports import ReportRenderer

    html = ReportRenderer().render_html(report)
    branded = report.application in {"coyote3", "cll_genie"}
    assert ('class="report-product-brand"' in html) is branded
    assert ('class="report-application-logo"' in html) is (branded and with_logo)
    if report.application == "coyote3":
        assert "Coyote<span>3</span>" in html
    elif report.application == "cll_genie":
        assert "<strong>CLL Genie</strong>" in html
    assert 'class="center-logo"' in html


def test_center_files_and_information_are_embedded(reports):
    source = reports["coyote3-dna"]
    assert source.data.branding.center_logo.startswith("data:image/svg+xml;base64,")
    for report in reports.values():
        html = report.render_html()
        for text in [
            "Example Diagnostics Center",
            "Molekylär diagnostik",
            "Exempeladress 1",
            "000-000000",
            "demo@example.org",
        ]:
            assert text in html
        assert 'class="accreditation"' in html
        assert "<script" not in html


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
def test_active_svg_is_rejected(content):
    logo = "data:image/svg+xml;base64," + base64.b64encode(content.encode()).decode()
    with pytest.raises(ValueError):
        Branding(center_logo=logo)


def test_optional_center_info_and_file_failures(tmp_path, reports):
    report = reports["genexus"].build()
    report.branding = Branding(organization="Only center")
    from smd_reports import ReportRenderer

    html = ReportRenderer().render_html(report)
    assert "Only center" in html and "Tel." not in html
    assert 'class="center-logo"' not in html
    with pytest.raises(FileNotFoundError):
        Branding.from_files(center_logo=tmp_path / "missing.svg")
    with pytest.raises(ValueError):
        embed_image(tmp_path / "unknown.html")
    with pytest.raises(ValidationError):
        Branding(center_logo_width_mm=1000)


def test_long_summary_and_metadata_inputs_are_preserved(reports):
    source = reports["coyote3-dna"]
    values = source.data.model_dump()
    values["summary"] = "\n\n".join(f"Paragraph {i}: granskad text ÅÄÖ." for i in range(100))
    values["metadata"]["fields"] += [
        {"label": f"Parameter {i}", "value": "Synthetic metadata"} for i in range(12)
    ]
    report = CoyoteReport(
        CoyoteData.model_validate(values),
        ReportConfig(title="Extended synthetic report", header_height_mm=100),
    )
    assert "Paragraph 99" in report.render_html()
    assert "Parameter 11" in report.render_html()
    assert report.build().header_height_mm == 100


def test_cll_multiple_sequences_preserve_supplied_decisions(reports):
    from smd_reports import CLLGenieData, CLLGenieReport

    source = reports["cll-genie-positive"]
    values = source.data.model_dump()
    sequence = dict(values["sequences"][0])
    sequence.update(
        sequence_id="Seq2", mutation_status="Application reviewed", productivity="Nonproductive"
    )
    values["sequences"].append(sequence)
    report = CLLGenieReport(CLLGenieData.model_validate(values), source.config)
    assert "Application reviewed" in report.render_html()
    assert "Nonproductive" in report.render_html()


def test_assay_and_run_mapping_does_not_change_source(reports):
    source = reports["genexus"]
    assert FieldValue(label="Assay", value="Demonstrationspanel") in source.build().metadata.fields
    assert source.data.metadata.fields == reports["coyote3-dna"].data.metadata.fields
    document = source.build()
    document.metadata.fields[-1].value = "Changed output"
    assert source.data.run[0].value == "SYNTHETIC-RUN"
