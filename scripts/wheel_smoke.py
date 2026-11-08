"""Install a distribution into a fresh environment and render JSON without PDF extras."""

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path

CHECK = """
import importlib.util
import json
from smd_reports import ReportLoader, ReportRenderer
assert importlib.util.find_spec('weasyprint') is None
payload = {
    "application": "coyote3", "analyte": "dna", "title": "Installed distribution",
    "language": "en", "report": {"report_id": "DEMO", "sample_id": "SYNTHETIC",
                                   "generated_at": "2026-01-01T12:00:00Z"},
    "sections": [{"kind": "details", "key": "details", "record_heading": "{0}",
                  "columns": [{"label": "Gene"}, {"label": "Added field"}, {"label": "Flag"},
                              {"label": "Count"}, {"label": "Rate"}],
                  "rows": [["EXAMPLE", "DYNAMIC-VALUE", False, 0, 0.0]]}],
}
report = ReportLoader().loads(json.dumps(payload))
html = ReportRenderer().render_html(report)
assert 'data:font/woff2;base64,' in html
assert 'Installed distribution' in html
assert 'Added field' in html and 'DYNAMIC-VALUE' in html
serialized = report.model_dump_json()
assert json.loads(serialized)['sections'][0]['rows'][0][2] is False
restored = ReportLoader().loads(serialized)
assert type(restored.sections[0].rows[0][3]) is int
assert type(restored.sections[0].rows[0][4]) is float
assert ReportRenderer().render_html(restored) == html
assert 'schema_version' not in serialized
print('Isolated JSON/HTML installation passed')
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true", help="Install the source distribution")
    args = parser.parse_args()
    pattern = "*.tar.gz" if args.source else "*.whl"
    candidates = list(Path("dist").resolve().glob(pattern))
    if len(candidates) != 1:
        raise SystemExit("Expected exactly one matching distribution in dist/")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        venv.create(root / "venv", with_pip=True)
        python = root / "venv/bin/python"
        environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        subprocess.run(
            [str(python), "-m", "pip", "install", str(candidates[0])],
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
