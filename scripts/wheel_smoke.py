"""Verify a built wheel in a fresh environment outside the source tree."""

import os
import subprocess
import tempfile
import venv
from pathlib import Path


def main():
    """Install the wheel and render with WeasyPrint deliberately unavailable."""
    wheel = next(Path("dist").resolve().glob("*.whl"))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        venv.create(root / "venv", with_pip=True)
        python = root / "venv" / "bin" / "python"
        subprocess.run([str(python), "-m", "pip", "install", str(wheel)], check=True)
        environment = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        subprocess.run(
            [
                str(python),
                "-c",
                """
import importlib.util
from datetime import datetime, timezone
from smd_reports import CoyoteData, CoyoteReport, ReportMetadata
from smd_reports.plugins.prepared import ReportConfig
assert importlib.util.find_spec('weasyprint') is None
report = CoyoteReport(CoyoteData(analyte='dna', metadata=ReportMetadata(
    report_id='SYNTHETIC', sample_id='SYNTHETIC', generated_at=datetime.now(timezone.utc)
)), ReportConfig(title='Installed wheel'))
html = report.render_html()
assert 'data:font/woff2;base64,' in html
assert 'Installed wheel' in html
assert 'template v1.7.0' in html
print('Isolated HTML-only wheel smoke check passed')
""",
            ],
            check=True,
            cwd=root,
            env=environment,
        )
        subprocess.run(
            [
                str(python),
                "-m",
                "smd_reports",
                "schema",
                "--application",
                "pgx",
                "--output",
                str(root / "pgx.schema.json"),
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
