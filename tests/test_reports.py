"""Observable contract, content and application-boundary regressions."""

import json
import subprocess
import sys

import pytest
from pydantic import ValidationError

from smd_reports import (
    Branding,
    CLLGenieData,
    CLLGenieReport,
    CoyoteData,
    CoyoteReport,
    Report,
    ReportRenderer,
    Theme,
)
from smd_reports.plugins.prepared import ReportConfig
from smd_reports.rendering import offline_fetcher


def test_all_examples_preserve_identity_and_content(reports):
    for name, builder in reports.items():
        document = builder.build()
        html = builder.render_html()
        assert document.metadata.report_id in html
        assert "SYNTHETIC-001" in html
        assert "&lt;PATIENT_NAME&gt;" in html
        assert "Exempel på granskad slutsats" in html
        assert "data:font/woff2;base64," in html
        assert document == Report.model_validate_json(document.model_dump_json())
        assert "fetch(" not in html, name


def test_supported_does_not_enable_analysis(reports):
    builder = reports["coyote3-dna"]
    assert "FUSION" in builder.data.supported_analyses
    assert "fusions" not in {section.key for section in builder.build().sections}
    assert "fusion-details" not in {section.key for section in builder.build().sections}


@pytest.mark.parametrize(
    "updates",
    [
        {"enabled_analyses": ["UNSUPPORTED"]},
        {"enabled_analyses": ["FUSION"]},
        {"supported_analyses": ["SNV", "SNV"]},
    ],
)
def test_invalid_analysis_inputs_fail(reports, updates):
    values = reports["coyote3-dna"].data.model_dump()
    values.update(updates)
    with pytest.raises(ValidationError):
        CoyoteData.model_validate(values)


def test_order_and_parameter_values(reports):
    builder = reports["coyote3-dna"]
    keys = []
    for section in builder.build().sections:
        if section.key == "summary":
            break
        keys.append(section.key)
    configured = CoyoteReport(
        builder.data,
        ReportConfig(
            title="Ordered",
            section_order=list(reversed(keys)),
        ),
    )
    assert [s.key for s in configured.build().sections][: len(keys)] == list(reversed(keys))
    assert "GRCh38" in configured.render_html()
    with pytest.raises(ValueError, match="section_order"):
        CoyoteReport(builder.data, ReportConfig(title="Bad", section_order=[])).build()


def test_cll_authoritative_facts_and_no_result_cases(reports):
    html = reports["cll-genie-positive"].render_html()
    for text in [
        "Borderline (granskad)",
        "Produktiv",
        "IGHV3-21*01",
        "313/321",
        "97.2% (312/321)",
        "JUNCTION-nt nb",
    ]:
        assert text in html
    for kind in ("nonfunctional", "no_clone"):
        document = reports[f"cll-genie-{kind}"].build()
        assert not any(s.key == "cll-sequences" for s in document.sections)
    values = reports["cll-genie-positive"].data.model_dump()
    values["submission_id"] = None
    with pytest.raises(ValidationError):
        CLLGenieData.model_validate(values)


def test_missing_identity_and_multiple_sequences(reports):
    source = reports["cll-genie-positive"]
    values = source.data.model_dump()
    values["sequences"][0]["identity_percent"] = None
    values["sequences"][0]["identity_nt"] = None
    values["sequences"].append({**values["sequences"][0], "sequence_id": "Seq2"})
    report = CLLGenieReport(CLLGenieData.model_validate(values), source.config)
    assert len(report.build().sections[0].rows) == 2
    assert "Seq2" in report.render_html()


def test_escaping_and_markdown_tables(reports):
    builder = reports["coyote3-dna"]
    values = builder.data.model_dump()
    values["summary_format"] = "markdown"
    values["summary"] = (
        "| Gen | Resultat |\n| --- | --- |\n| ÅÄÖ | 0 |\n\n"
        '<img src="https://example.org/patient"><script>alert(1)</script>'
    )
    values["metadata"]["author"] = '<img src="x" onerror="alert(1)">'
    html = CoyoteReport(CoyoteData.model_validate(values), builder.config).render_html()
    assert "<td>ÅÄÖ</td>" in html
    assert "<script>" not in html
    assert '<img src="https:' not in html
    assert "&lt;img" in html


def test_validation_after_mutation_and_unknown_schema(reports):
    document = reports["coyote3-dna"].build()
    values = document.model_dump()
    values["schema_version"] = 2
    with pytest.raises(ValidationError):
        Report.model_validate(values)
    document.sections.append(document.sections[0])
    with pytest.raises(ValidationError, match="Duplicate section"):
        ReportRenderer().render_html(document)


def test_themes_are_isolated(reports):
    first, second = ReportRenderer(), ReportRenderer()
    custom = Theme(
        name="custom", heading="#176B68", accent="#176B68", tint="#edf7f5", rule_end="#176B68"
    )
    first.register_theme(custom)
    with pytest.raises(ValueError, match="already registered"):
        first.register_theme(custom)
    with pytest.raises(ValueError, match="Unknown theme"):
        second.render_html(reports["pgx"].build(), theme="custom")
    assert "#176B68" in first.render_html(reports["pgx"].build(), theme="custom")


def test_no_network_or_local_file_assets():
    for url in ("https://example.org/a.png", "file:///etc/passwd", "ftp://example.org/a"):
        with pytest.raises(ValueError):
            offline_fetcher(url)
        with pytest.raises(ValidationError):
            Branding(center_logo=url)


def test_html_without_weasyprint():
    script = """
import sys
sys.modules['weasyprint'] = None
from smd_reports import CoyoteReport, CoyoteData, ReportMetadata, PDFUnavailableError
from smd_reports.plugins.prepared import ReportConfig
from datetime import datetime, timezone
report = CoyoteReport(CoyoteData(analyte='dna', metadata=ReportMetadata(
    report_id='DEMO', sample_id='DEMO', generated_at=datetime.now(timezone.utc)
)), ReportConfig(title='Demo'))
assert '<html' in report.render_html()
try:
    report.render_pdf()
except PDFUnavailableError as exc:
    assert 'smd-reports[pdf]' in str(exc)
else:
    raise AssertionError('PDF should require optional dependency')
"""
    subprocess.run([sys.executable, "-c", script], check=True)


def test_fixed_inputs_are_reproducible_and_not_mutated(reports):
    for builder in reports.values():
        before = builder.data.model_dump_json()
        assert builder.render_html() == builder.render_html()
        assert builder.data.model_dump_json() == before
        assert json.loads(builder.build().model_dump_json())["provenance"]["template_version"]
