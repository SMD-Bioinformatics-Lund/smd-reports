"""Application JSON schemas, portable snapshots and installer-facing commands."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from smd_reports import ReportLoader, ReportRenderer
from smd_reports.cli import main


def test_committed_json_examples_are_valid():
    for path in (Path(__file__).parents[1] / "examples/inputs").glob("*.json"):
        assert ReportLoader().load(path).sections


def input_json(builder, tmp_path, language="sv"):
    raw = builder.data.model_dump(mode="json")
    branding = raw.pop("branding")
    source = Path(__file__).parents[1] / "examples/assets/center-example.svg"
    (tmp_path / "logo.svg").write_bytes(source.read_bytes())
    branding["center_logo"] = "logo.svg"
    config = builder.config.model_dump()
    payload = {
        "application": builder.application,
        "schema_version": 1,
        "language": language,
        "title": config.pop("title"),
        "presentation": config,
        "report": raw.pop("metadata"),
        "branding": branding,
        "provenance": raw.pop("provenance"),
        "data": raw,
    }
    payload["presentation"].pop("language")
    path = tmp_path / "input.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path, payload


def test_every_application_json_round_trips_to_same_document(reports, tmp_path, monkeypatch):
    for builder in reports.values():
        path, _ = input_json(builder, tmp_path)
        monkeypatch.chdir(tmp_path.parent)
        document = ReportLoader().load(path)
        assert document == builder.build()
        snapshot = tmp_path / "snapshot.json"
        snapshot.write_text(document.model_dump_json(), encoding="utf-8")
        (tmp_path / "logo.svg").unlink()
        assert ReportLoader().load(snapshot) == document


@pytest.mark.parametrize("application", ["coyote3", "genexus", "cll_genie", "pgx"])
def test_application_schema(application):
    schema = ReportLoader().schema(application)
    assert schema["properties"]["application"]["const"] == application
    assert "report" in schema["required"] and "data" in schema["required"]
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize("language", ["sv", "en"])
def test_language_translates_interface_not_supplied_text(reports, tmp_path, language):
    for builder in reports.values():
        path, _ = input_json(builder, tmp_path, language)
        document = ReportLoader().load(path)
        html = ReportRenderer().render_html(document)
        assert ("Sample ID" if language == "en" else "Prov-ID") in html
        assert ("Conclusion" if language == "en" else "Slutsats") in html
        assert "Exempel på granskad slutsats" in html
        if builder.application == "cll_genie" and builder.data.report_type == "positive":
            assert "Borderline (granskad)" in html
        if language == "en":
            assert "Page " in html


def test_cli_validation_render_normalize_schema_and_errors(reports, tmp_path, capsys):
    path, payload = input_json(reports["genexus"], tmp_path)
    output = tmp_path / "report.html"
    assert main(["validate", str(path)]) == 0
    assert main(["render", str(path), "--format", "html", "--output", str(output)]) == 0
    html = output.read_text()
    assert "<style>" in html and "@page" in html and "@font-face" in html
    assert "data:font/woff2;base64," in html and "data:image/svg+xml;base64," in html
    assert "<link " not in html and "@import" not in html
    snapshot = tmp_path / "snapshot.json"
    assert main(["normalize", str(path), "--output", str(snapshot)]) == 0
    schema = tmp_path / "schema.json"
    assert main(["schema", "--application", "genexus", "--output", str(schema)]) == 0
    assert json.loads(schema.read_text())["properties"]["application"]["const"] == "genexus"
    assert main(["normalize", str(path), "--output", str(path)]) == 2
    payload["language"] = "xx"
    path.write_text(json.dumps(payload))
    assert main(["render", str(path), "--format", "html", "--output", str(output)]) == 2
    assert "language" in capsys.readouterr().err


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 9},
        {"application": "unknown"},
        {"data": {"unsupported": "PRIVATE-VALUE"}},
        {"branding": {"center_logo": "https://example.org/private.svg"}},
        {"branding": {"center_logo": "missing.svg"}},
    ],
)
def test_invalid_inputs_fail_without_sensitive_output(reports, tmp_path, capsys, change):
    path, payload = input_json(reports["coyote3-dna"], tmp_path)
    payload.update(change)
    path.write_text(json.dumps(payload))
    assert main(["validate", str(path)]) == 2
    assert "PRIVATE-VALUE" not in capsys.readouterr().err


@pytest.mark.parametrize(
    "text", ['{"application":"pgx","application":"genexus"}', '{"value":NaN}', '{"bad":']
)
def test_bad_json_is_rejected(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text)
    assert main(["validate", str(path)]) == 2


@pytest.mark.parametrize("application", ["genexus", "coyote3-dna", "cll-genie-positive", "pgx"])
def test_exported_html_converts_without_package_or_source_assets(reports, tmp_path, application):
    pytest.importorskip("weasyprint")
    pypdf = pytest.importorskip("pypdf")
    path, _ = input_json(reports[application], tmp_path, "en")
    html = tmp_path / "standalone.html"
    assert main(["render", str(path), "--format", "html", "--output", str(html)]) == 0
    path.unlink()
    (tmp_path / "logo.svg").unlink()
    script = """
import sys
sys.modules['smd_reports'] = None
from weasyprint import HTML
HTML(filename=sys.argv[1]).write_pdf(sys.argv[2])
"""
    pdf = tmp_path / "external.pdf"
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    subprocess.run(
        [sys.executable, "-c", script, str(html), str(pdf)], check=True, cwd=tmp_path, env=env
    )
    reader = pypdf.PdfReader(pdf)
    assert "Sample ID" in reader.pages[0].extract_text()
    assert "SYNTHETIC-001" in reader.pages[0].extract_text()
    pymupdf = pytest.importorskip("pymupdf")
    rendered = pymupdf.open(pdf)
    page = rendered[-1]
    footer_rects = [
        rect for rect in page.search_for("PLACEHOLDER") if rect.y0 > page.rect.height - 110
    ]
    assert footer_rects and all(rect.y1 <= page.rect.height for rect in footer_rects)
