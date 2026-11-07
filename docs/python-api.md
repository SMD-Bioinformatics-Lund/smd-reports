# Python usage

Import the installed package as `smd_reports`. Load JSON or build directly from Python models.

## Load JSON and render

```python
from pathlib import Path
from smd_reports import ReportLoader, ReportRenderer

document = ReportLoader().load("report.json")
renderer = ReportRenderer()
Path("report.html").write_text(renderer.render_html(document), encoding="utf-8")
# Requires the PDF extra:
Path("report.pdf").write_bytes(renderer.render_pdf(document))
```

`load()` accepts an application input envelope or a normalized `Report` snapshot.
Relative logo paths resolve against the JSON directory, not the process's working directory.
Model validation, JSON and filesystem errors are propagated to the caller.

## Build from application data

| Builder | Data model |
| --- | --- |
| `CoyoteReport` | `CoyoteData` |
| `GenexusReport` | `GenexusData` |
| `CLLGenieReport` | `CLLGenieData` |
| `PGxReport` | `PGxData` |

Each takes `data=...` and `config=ReportConfig(...)`. The [quickstart](quickstart.md)
contains a complete example; [application inputs](integration.md) covers their differences.

```python
document = report.build()       # Report
html = report.render_html()    # str
pdf = report.render_pdf()      # bytes; optional PDF dependency
```

Builders do not save files. In a web application, return these values through the host's
response mechanism or store them using its artifact storage service.

## Define sections

```python
from smd_reports import Analysis, Column, FieldValue, TableSection, TextSection

analysis = Analysis(
    name="SNV",
    parameters=[FieldValue(label="Reference genome", value="GRCh38")],
    sections=[
        TableSection(
            key="variants", title="Reported variants",
            columns=[Column(key="gene", label="Gene")],
            rows=[{"gene": "BRAF"}],
            empty_text="No reportable variants",
        ),
        TextSection(
            key="notes", title="Notes", text="**Reviewed** explanatory text.",
            format="markdown",
        ),
    ],
)
```

Declare each row's columns explicitly. Unknown row keys fail validation; missing declared
cells display a hyphen. Zero and false are retained. Markdown is sanitized and does not
load external images. `ImageSection` accepts an embedded raster/static SVG plot.

Supply each enabled analysis in `analyses`, even when its result table is empty.
`supported_analyses` describes assay capability; it does not automatically enable sections.

## Configure presentation

```python
from smd_reports import ReportConfig

config = ReportConfig(
    title="Molecular Genetics Report",
    language="en",
    summary_new_page=True,
    header_height_mm=65,
)
```

If `section_order` is provided, it must name every selected analysis section and generated
`parameters-ANALYSIS` section exactly once. Summary, description and references follow.
Application-specific generated tables also have their builder-defined ordering.

Language controls built-in labels, boolean display and page numbering. Supply clinical
text, custom field labels and custom section titles in the desired language yourself.

## Preserve a normalized document

```python
from pathlib import Path
from smd_reports import ReportLoader

Path("report.snapshot.json").write_text(
    document.model_dump_json(indent=2), encoding="utf-8",
)
restored = ReportLoader().load("report.snapshot.json")
```

Snapshots contain embedded logos and selected document content. They do not rerun clinical
rules. Retain the matching rendering environment when regenerating reviewed layouts.
See [Python API reference](reference.md) for signatures, defaults and errors.
