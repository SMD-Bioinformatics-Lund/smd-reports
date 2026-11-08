"""Neutral reports work without an application identity or sample reference."""

import json
import runpy
import sys

import pytest

from smd_reports import ReportLoader, ReportRenderer
from smd_reports.cli import main


@pytest.mark.parametrize(
    "language,heading", [("en", "Report information"), ("sv", "Rapportinformation")]
)
def test_generic_default_round_trip_and_localized_header(payloads, load, language, heading):
    data = payloads["generic"]
    data["language"] = language
    assert "application" not in data and "sample_id" not in data["report"]
    document = load(data)
    assert document.application == "generic"
    assert document.metadata.sample_id == ""
    restored = ReportLoader().loads(document.model_dump_json())
    html = ReportRenderer().render_html(restored)
    assert heading in html
    assert "report-generic" in html and "#435365" in html
    assert 'class="report-sample-reference"' not in html
    assert ReportRenderer().render_html(document) == html


def test_module_entry_point_exports_default_schema(tmp_path, monkeypatch):
    output = tmp_path / "schema.json"
    monkeypatch.setattr(sys, "argv", ["smd-reports", "schema", "--output", str(output)])
    with pytest.raises(SystemExit) as result:
        runpy.run_module("smd_reports", run_name="__main__")
    assert result.value.code == 0
    schema = json.loads(output.read_text())
    assert schema["properties"]["application"]["default"] == "generic"
    assert "sample_id" not in schema["$defs"]["ReportMetadata"]["required"]


def test_cli_generic_pdf_contains_results_and_separate_summary(tmp_path, reports):
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    source = tmp_path / "input.json"
    source.write_text(reports["generic"].model_dump_json())
    output = tmp_path / "report.pdf"
    assert main(["render", str(source), "--format", "pdf", "--output", str(output)]) == 0
    with pymupdf.open(output) as pdf:
        texts = [page.get_text() for page in pdf]
        assert "Example A" in texts[0]
        summary_pages = [i for i, text in enumerate(texts) if "Conclusion" in text]
        assert summary_pages and summary_pages[0] > 0
        assert "Example B" not in texts[summary_pages[0]]
        assert "Method" not in texts[summary_pages[0]]
        assert "Method" in texts[summary_pages[0] + 1]
        assert "Coyote3" not in "".join(texts) and "Genexus" not in "".join(texts)
        assert all("Example Center" in text for text in texts)
        assert "REPORT INFORMATION" in texts[0]
        assert pdf[0].rect.width == pytest.approx(595.28, abs=1)
