# Python usage

Install `smd-reports` and import it as `smd_reports`. Report data is supplied as JSON.

## Load a file

```python
from pathlib import Path
from smd_reports import ReportLoader, ReportRenderer

report = ReportLoader().load("report.json")
renderer = ReportRenderer()
Path("report.html").write_text(renderer.render_html(report), encoding="utf-8")
Path("report.pdf").write_bytes(renderer.render_pdf(report))
```

PDF generation requires `pip install "smd-reports[pdf]"` and the native runtime.

## Load JSON text

```python
from smd_reports import ReportLoader, ReportRenderer

report = ReportLoader().loads(json_text, base_dir="/path/to/assets")
html = ReportRenderer().render_html(report)
```

`loads()` accepts JSON text or UTF-8 bytes. `base_dir` is required when that JSON contains
relative artwork paths. Embedded data URIs need no base directory.

If your application already has a dictionary, serialize it with `json.dumps(payload)`
and pass the resulting JSON text to `loads()`. Both loading methods use the same format
and validation.

## Save a portable JSON document

```python
from pathlib import Path

Path("report.portable.json").write_text(
    report.model_dump_json(indent=2), encoding="utf-8",
)
```

The saved document embeds artwork and uses the same JSON format as the original input.
Reload it with `ReportLoader.load()` or `loads()`.

## Export validation rules

```python
from smd_reports import ReportLoader

schema = ReportLoader().schema()
```

See the [JSON guide](json-inputs.md) for dynamic columns, localized labels, detailed
finding cards and grouped grids. Method signatures and exceptions are listed in the
[Python API reference](reference.md).
