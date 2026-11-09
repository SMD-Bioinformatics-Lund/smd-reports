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
    report.model_dump_json(indent=2),
    encoding="utf-8",
)
```

The saved document embeds artwork and uses the same JSON format as the original input.
Reload it with `ReportLoader.load()` or `loads()`. Automatically computed package/template
versions are available separately through `report.rendering_metadata`.

## Export validation rules

```python
from smd_reports import ReportLoader

schema = ReportLoader().schema()
```

See the [JSON guide](json-inputs.md) for dynamic columns, localized labels, detailed
finding cards and grouped grids. Method signatures and exceptions are listed in the
[Python API reference](reference.md).

## Handle errors

Loading preserves standard Python exceptions for file access and JSON syntax, and
Pydantic's `ValidationError` for invalid fields. Use `format_validation_error()` to turn
validation errors into readable field messages without including report values.

```python
import json
from pydantic import ValidationError
from smd_reports import (
    ReportInputError,
    ReportLoader,
    ReportRenderError,
    ReportRenderer,
    format_validation_error,
)

try:
    report = ReportLoader().load("report.json")
    html = ReportRenderer().render_html(report)
except ValidationError as error:
    message = format_validation_error(error)
except json.JSONDecodeError as error:
    message = f"Invalid JSON at line {error.lineno}, column {error.colno}."
except ReportInputError as error:
    message = str(error)
except ReportRenderError as error:
    message = str(error)
except UnicodeError:
    message = "Save report JSON with UTF-8 encoding."
except OSError:
    message = "Cannot read the report file; check its location and permissions."
```

`ReportAssetError` is a `ReportInputError` with `field` and `reason` attributes. Field paths
use array indexes, for example `sections[2].images[0].source`. `PDFUnavailableError` is a
`ReportRenderError` that explains which optional dependencies are needed. Rendering errors
preserve the original exception as `__cause__` for debugging.

## Enable event logging

The package uses Python's standard `logging` module and installs a `NullHandler`. It does
not configure the root logger or write log files. Enable events through your application's
logging configuration, for example:

```python
import logging

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
logger = logging.getLogger("smd_reports")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False
```

`INFO` records mark JSON loading, completed validation, schema export and HTML/PDF
rendering. `ERROR` records identify failed stages. Package events omit report values,
image contents and file paths. Dependency loggers, including `weasyprint`, can be configured
separately with Python logging.
