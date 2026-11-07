# Quickstart

This example creates an HTML report without a JSON file or logo assets. It uses
synthetic data and requires only the core package.

## Build a report in Python

Save the following as `create_report.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

from smd_reports import (
    Analysis, Branding, Column, CoyoteData, CoyoteReport,
    FieldValue, ReportConfig, ReportMetadata, TableSection,
)

report = CoyoteReport(
    data=CoyoteData(
        analyte="dna",
        metadata=ReportMetadata(
            report_id="SYNTHETIC-REPORT-001",
            sample_id="SYNTHETIC-001",
            generated_at=datetime.now(timezone.utc),
            author="Demo User",
            fields=[FieldValue(label="Sample type", value="Synthetic sample")],
        ),
        branding=Branding(organization="Example Molecular Diagnostics Center"),
        supported_analyses=["SNV"],
        enabled_analyses=["SNV"],
        analyses=[Analysis(
            name="SNV",
            sections=[TableSection(
                key="snvs",
                title="Reported variants",
                columns=[Column(key="gene", label="Gene"),
                         Column(key="variant", label="Variant")],
                rows=[{"gene": "BRAF", "variant": "p.Val600Glu"}],
            )],
        )],
        summary="Reviewed synthetic conclusion. For demonstration only.",
    ),
    config=ReportConfig(title="Molecular Genetics Report", language="en"),
)

Path("report.html").write_text(report.render_html(), encoding="utf-8")
Path("report.snapshot.json").write_text(
    report.build().model_dump_json(indent=2), encoding="utf-8",
)
```

Run `python create_report.py`. Open `report.html` in a browser. It includes the CSS,
print rules and fonts; no separate stylesheet directory is needed.

## Generate a PDF

With the PDF extra and native dependencies installed, add:

```python
Path("report.pdf").write_bytes(report.render_pdf())
```

The HTML can also be copied to another machine and converted there:

```sh
weasyprint report.html report.pdf
```

## Load an application JSON file

```python
from pathlib import Path
from smd_reports import ReportLoader, ReportRenderer

document = ReportLoader().load("report.json")
html = ReportRenderer().render_html(document)
Path("report.html").write_text(html, encoding="utf-8")
```

Use the [JSON format guide](json-inputs.md) to construct `report.json`.
The same file can be rendered from a shell:

```sh
smd-reports validate report.json
smd-reports render report.json --format html --output report.html
```

Next, configure [center branding](branding.md), explore [Python usage](python-api.md),
or choose an [application data model](integration.md).
