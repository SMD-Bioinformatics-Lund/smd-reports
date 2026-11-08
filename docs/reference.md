# Python API reference

The public interface is exported from `smd_reports`.

| Method | Result | Description |
| --- | --- | --- |
| `ReportLoader.load(path: str \| Path)` | Validated document | Read JSON; resolve artwork relative to the file |
| `ReportLoader.loads(source: str \| bytes, *, base_dir=None)` | Validated document | Read JSON text/bytes; resolve artwork relative to `base_dir` |
| `ReportLoader.schema(application=None)` | `dict` | Export JSON Schema; optionally constrain the application identity |
| `ReportRenderer.render_html(report, *, theme=None)` | `str` | Return standalone HTML with embedded styles, fonts and images |
| `ReportRenderer.render_pdf(report, *, theme=None)` | `bytes` | Return a PDF; requires the PDF extra |
| `ReportRenderer.register_theme(theme: Theme)` | `None` | Add a named theme to this renderer |

Loading and rendering return values without saving output files. The document returned
by a loader supports `model_dump_json(indent=2)` for portable JSON export.
Its `template_name` and `template_version` properties identify the selected layout;
`rendering_metadata` includes the installed package version.

## Exceptions

| Exception | Meaning |
| --- | --- |
| `pydantic.ValidationError` | Invalid fields, row lengths, translations or layout references |
| `json.JSONDecodeError` | Invalid JSON syntax |
| `ValueError` | Duplicate JSON keys, non-finite JSON constants or an unknown theme |
| `TypeError` | `loads()` received something other than JSON text/bytes |
| `OSError` | Input/output file could not be read or written |
| `ReportAssetError` | An image could not be loaded; identifies its JSON field |
| `PDFUnavailableError` | PDF Python/native dependencies are unavailable |

`ReportAssetError`, `PDFUnavailableError` and `Theme` are also exported from `smd_reports`.

## Theme

`Theme` requires `name`, `heading`, `accent`, `tint` and `rule_end`. Colors are six-digit
hex strings. Optional `body_pt` defaults to 9.25 and accepts 8–12. See [rendering](rendering.md).

## JSON definitions

The [JSON guide](json-inputs.md) documents the input fields. `schema()` exports their
machine-readable definitions, including table/detail row matrices, grouped grids, paper
sizes, text blocks and images. `report.rendering_metadata` exposes automatically computed
package/template versions alongside the supplied provenance context.
