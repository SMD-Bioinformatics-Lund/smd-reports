"""JSON files/text, portable normalized output and CLI commands."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from smd_reports import ReportLoader, ReportRenderer
from smd_reports.cli import main

ROOT = Path(__file__).parents[1]


def test_all_committed_json_examples_load():
    for path in (ROOT / "examples/inputs").glob("*.json"):
        assert ReportLoader().load(path).sections


@pytest.mark.parametrize("application", ["coyote3", "genexus", "cll_genie", "pgx", None])
def test_json_schema(application):
    schema = ReportLoader().schema(application)
    assert schema["additionalProperties"] is False
    assert "report" in schema["required"]
    assert "schema_version" not in schema["properties"]
    if application:
        assert schema["properties"]["application"]["const"] == application
    assert schema["$defs"]["TableSection"]["properties"]["rows"]["items"]["type"] == "array"


def test_cli_render_normalize_validate_schema(tmp_path, payloads, load, capsys):
    # Embed artwork using the same JSON format, then write a fully portable input.
    report = load(payloads["genexus"])
    source = tmp_path / "input.json"
    source.write_text(report.model_dump_json())
    html = tmp_path / "report.html"
    snapshot = tmp_path / "snapshot.json"
    schema = tmp_path / "schema.json"
    assert main(["validate", str(source)]) == 0
    assert main(["render", str(source), "--format", "html", "--output", str(html)]) == 0
    assert "<style>" in html.read_text() and "@font-face" in html.read_text()
    assert main(["normalize", str(source), "--output", str(snapshot)]) == 0
    assert ReportLoader().load(snapshot) == report
    assert main(["schema", "--output", str(schema)]) == 0
    assert "TableSection" in schema.read_text()
    assert main(["render", str(source), "--format", "html", "--output", str(source)]) == 2
    assert ReportLoader().load(source) == report


@pytest.mark.parametrize(
    "text",
    [
        '{"application":"pgx","application":"coyote3"}',
        '{"unexpected":"SECRET-REPORT-VALUE"}',
        '{"value":NaN}',
        '{"value":Infinity}',
        '{"value":-Infinity}',
    ],
)
def test_bad_json_does_not_leak_source_values(tmp_path, text, capsys):
    source = tmp_path / "bad.json"
    source.write_text(text)
    assert main(["validate", str(source)]) == 2
    assert "SECRET-REPORT-VALUE" not in capsys.readouterr().err


def test_html_only_rendering_does_not_import_weasyprint(reports):
    script = """
import sys
sys.modules['weasyprint']=None
from smd_reports import ReportLoader, ReportRenderer, PDFUnavailableError
report=ReportLoader().loads(sys.stdin.read())
assert '<html' in ReportRenderer().render_html(report)
try: ReportRenderer().render_pdf(report)
except PDFUnavailableError: pass
else: raise AssertionError('Expected optional PDF dependency error')
"""
    subprocess.run(
        [sys.executable, "-c", script],
        input=reports["pgx"].model_dump_json(),
        text=True,
        check=True,
    )


@pytest.mark.parametrize("name", ["coyote3-dna", "genexus-en", "cll-genie-positive", "pgx"])
def test_standalone_html_converts_without_package_or_source_assets(tmp_path, reports, name):
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    source = tmp_path / "report.html"
    source.write_text(ReportRenderer().render_html(reports[name]))
    output = tmp_path / "report.pdf"
    script = """
import sys
sys.modules['smd_reports']=None
from weasyprint import HTML
HTML(filename=sys.argv[1]).write_pdf(sys.argv[2], custom_metadata=True)
"""
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    subprocess.run(
        [sys.executable, "-c", script, str(source), str(output)],
        check=True,
        cwd=tmp_path,
        env=environment,
    )
    pdf = pymupdf.open(output)
    text = "\n".join(page.get_text() for page in pdf)
    assert "SYNTHETIC-001" in text
    assert "PLACEHOLDER" in text


@pytest.mark.parametrize("value", [True, False, 0, 1, 0.0, 1.25, "0", None, {"en": "Text"}])
def test_json_export_preserves_cell_value_types(payloads, load, value):
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "table",
            "key": "scalars",
            "columns": {"en": ["Value"], "sv": ["Value"]},
            "rows": [[value]],
        }
    ]
    document = load(data)
    serialized = document.model_dump_json()
    exported = json.loads(serialized)["sections"][0]["rows"][0][0]
    assert type(exported) is type(value)
    assert exported == value
    restored = ReportLoader().loads(serialized)
    assert type(restored.sections[0].rows[0][0]) is type(value)
    assert ReportRenderer().render_html(restored) == ReportRenderer().render_html(document)
