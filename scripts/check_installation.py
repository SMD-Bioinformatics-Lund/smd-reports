"""Check package installation, HTML rendering, and CLI commands in a clean environment."""

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path

CHECK = """
import importlib.util
import json
import base64
from io import BytesIO
from PIL import Image
from smd_reports import ReportLoader, ReportRenderer
assert importlib.util.find_spec('weasyprint') is None
image = BytesIO()
Image.new("RGB", (10, 3), (20, 60, 120)).save(image, format="PNG")
plot = "data:image/png;base64," + base64.b64encode(image.getvalue()).decode()
payload = {
    "application": "coyote3", "analyte": "dna", "title": "Installed distribution",
    "language": "en", "report": {"report_id": "DEMO", "sample_id": "SYNTHETIC",
                                   "generated_at": "2026-01-01T12:00:00Z"},
    "presentation": {"page_size": "custom", "custom_width_mm": 300, "custom_height_mm": 200},
    "provenance": {"application_name": "Example", "pipeline_name": "Example pipeline"},
    "sections": [{"kind": "details", "key": "details", "record_heading": "{0}",
                  "columns": {
                      "en": ["Gene", "Added field", "Flag", "Count", "Rate"],
                      "sv": ["Gen", "Nytt fält", "Flagga", "Antal", "Frekvens"],
                  },
                  "column_options": {"1": {"emphasis": True}},
                  "rows": [["EXAMPLE", "DYNAMIC-VALUE", False, 0, 0.0]],
                  "images": [{"source": plot, "caption": "Example plot"}]},
                 {"kind": "summary", "key": "summary",
                  "format": "markdown", "text": "**Reviewed** <PATIENT_NAME>"},
                 {"kind": "compact_table", "key": "items",
                  "items": ["COMPACT-FIRST", {"en": "COMPACT-LAST", "sv": "KOMPAKT-SISTA"}]},
                 {"kind": "table", "key": "highlight", "columns": {"en": ["Value"]},
                  "rows": [["HIGHLIGHTED-VALUE"]], "row_options": {"0": {"highlight": True}}}],
}
report = ReportLoader().loads(json.dumps(payload))
html = ReportRenderer().render_html(report)
assert 'data:font/woff2;base64,' in html
assert 'Installed distribution' in html
assert 'Conclusion' in html and '<strong>Reviewed</strong>' in html
assert '&lt;PATIENT_NAME&gt;' in html and '<PATIENT_NAME>' not in html
assert 'data:image/png;base64,' in html
assert report.presentation.dimensions_mm == (300, 200)
assert 'package_version' in report.rendering_metadata
assert 'Added field' in html and 'DYNAMIC-VALUE' in html
assert 'COMPACT-FIRST' in html and 'COMPACT-LAST' in html
assert '<tr class="row-highlight">' in html and 'HIGHLIGHTED-VALUE' in html
serialized = report.model_dump_json()
assert json.loads(serialized)['sections'][0]['columns']['en'][1] == 'Added field'
assert json.loads(serialized)['sections'][0]['column_options'] == {'1': {'emphasis': True}}
assert json.loads(serialized)['sections'][0]['rows'][0][2] is False
restored = ReportLoader().loads(serialized)
assert type(restored.sections[0].rows[0][3]) is int
assert type(restored.sections[0].rows[0][4]) is float
assert ReportRenderer().render_html(restored) == html
assert 'schema_version' not in serialized and 'package_version' not in serialized
print('Installation and HTML rendering checks passed')
"""


def main():
    """Install and test a wheel or source distribution in a temporary virtual environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true", help="Install the source distribution")
    args = parser.parse_args()
    pattern = "*.tar.gz" if args.source else "*.whl"
    distributions = list(Path("dist").resolve().glob(pattern))
    if len(distributions) != 1:
        raise SystemExit("Expected exactly one matching distribution in dist/")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        venv.create(root / "venv", with_pip=True)
        python = root / "venv/bin/python"
        environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        subprocess.run(
            [str(python), "-m", "pip", "install", str(distributions[0])],
            check=True,
            cwd=root,
            env=environment,
        )
        subprocess.run([str(python), "-c", CHECK], check=True, cwd=root, env=environment)
        subprocess.run(
            [
                str(python),
                "-m",
                "smd_reports",
                "schema",
                "--output",
                str(root / "report.schema.json"),
            ],
            check=True,
            cwd=root,
            env=environment,
        )
        subprocess.run(
            [str(root / "venv/bin/smd-reports"), "--help"],
            check=True,
            cwd=root,
            env=environment,
            stdout=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    main()
