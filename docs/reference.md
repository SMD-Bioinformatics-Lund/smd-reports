# Python API reference

Public classes below are exported from `smd_reports` unless another import path is stated.
Models use Pydantic 2, reject unknown fields and support `model_dump()`,
`model_dump_json()` and `model_validate()`.

## Loading and rendering

| Method | Returns | Behavior |
| --- | --- | --- |
| `ReportLoader.load(path: str \| Path)` | `Report` | Load application JSON or normalized snapshot; embed referenced logos |
| `ReportLoader.schema(application: str)` | `dict` | Export one application's JSON Schema |
| `ReportRenderer.render_html(report: Report, *, theme=None)` | `str` | Render self-contained HTML |
| `ReportRenderer.render_pdf(report: Report, *, theme=None)` | `bytes` | Render PDF using optional WeasyPrint |
| `ReportRenderer.register_theme(theme: Theme)` | `None` | Register a new theme name; duplicates fail |

Loading and rendering do not persist artifacts. JSON parsing, filesystem and Pydantic
validation errors propagate to Python callers. `ReportAssetError`, imported from
`smd_reports.loading`, identifies a logo field that could not be loaded.
Missing PDF Python/native dependencies raise `PDFUnavailableError`.

## Application builders

`CoyoteReport(data: CoyoteData, config: ReportConfig)`,
`GenexusReport(data: GenexusData, config: ReportConfig)`,
`CLLGenieReport(data: CLLGenieData, config: ReportConfig)` and
`PGxReport(data: PGxData, config: ReportConfig)` implement the `ClinicalReport` interface:

| Method | Returns |
| --- | --- |
| `build()` | Validated `Report` |
| `render_html(*, renderer=None)` | HTML `str` |
| `render_pdf(*, renderer=None)` | PDF `bytes` |

`PGxReport.from_files(inputs: PGxFiles, *, data: PGxData, config: ReportConfig)` returns a
`PGxReport` after local TSV preparation. See [application inputs](integration.md).

## Shared models

### ReportMetadata

Required fields: `report_id`, `sample_id`, `generated_at`. IDs must be nonempty;
`generated_at` must include a timezone. Optional fields are `author` (empty by default)
and ordered `fields: list[FieldValue]` (empty by default).

`FieldValue(label, value)` accepts string, integer, finite float, boolean or null values.

### ReportConfig

| Field | Type | Default |
| --- | --- | --- |
| `title` | `str` | Required |
| `language` | `"sv"` or `"en"` | `"sv"` |
| `section_order` | `list[str]` or `None` | `None` |
| `summary_new_page` | `True` only; conclusions always have page breaks before and after | `True` |
| `header_height_mm` | Finite float, 40–120 | `65` |
| `footer_height_mm` | Finite float, 22–50; used with accreditation artwork | `38` |

### Analysis and sections

`Analysis(name, parameters=[], sections=[], details=[])` groups prepared sections for one analysis.
Section keys must be unique within a built document. All sections have `key`, `title` and
`page_break_before=False`.

| Section | Specific fields |
| --- | --- |
| `TextSection` | `text`; `format="plain"` or `"markdown"`; `conclusion=False` |
| `TableSection` | Nonempty `columns: list[Column]`; `rows=[]`; `empty_text`; optional `emphasis_column`/`emphasis_value` |
| `DetailSection` | `records: list[DetailRecord]=[]`; `fields_per_row=3` (1, 2 or 3); `empty_text` |
| `CLLSequenceSection` | `kind="cll_sequences"`; nonempty `sequences: list[CLLSequence]` with unique identifiers |
| `ImageSection` | Embedded `source` data URI; `caption=""` |

`Column(key, label)` declares a table column. Row keys must be declared columns.
`ReportSection` is the discriminated union of the five section types; JSON uses `kind`
values `text`, `table`, `details`, `cll_sequences` and `image`.

`DetailRecord(key, title, fields)` defines a finding card with a nonempty ordered list of
`DetailField` values. Record keys must be unique within a detail section.
`DetailField(label, value, full_width=False, format="plain", emphasis=False)` accepts the
same scalar values as `FieldValue`. Markdown and full-width fields occupy their own row;
long comments can continue across PDF pages. Genexus renders compact fields first, then
full-width fields, matching its configured source layout.

`CLLSequenceSection` renders the dedicated grouped CLL Genie sequence layout. See
[CLL Genie inputs](integration.md#cll-genie) for the typed gene, identity, functionality,
indel, junction and read-count fields. This section is automatically built by
`CLLGenieReport`; normalized snapshots retain its full prepared sequence data.

Analysis `sections` and parameters precede the summary; enabled analyses' `details` follow
it. The method description, `supporting_sections` and references follow the details.
The application supplies clinical values, classifications, labels and commentary.

### Branding

`Branding` holds embedded artwork and center information.
`Branding.from_files(*, center_logo=None, application_logo=None, accreditation_logo=None,
**information)` reads explicit local logo files and returns a validated `Branding`.
See [branding](branding.md) for fields, dimensions and image restrictions.

### Report and provenance

`Report` is the normalized document: application identity, title, language, analyte,
header height, metadata, branding, provenance and ordered sections. Its schema version is 1.
Normalized snapshots use this format; application envelopes use the [JSON input format](json-inputs.md).

`Provenance` contains application/configuration/assay/source revisions plus package, plugin,
schema and template versions. Builders attach the installed package/template revisions.
Applications provide their own contextual revisions and preserve artifacts.

### Theme

`Theme` requires `name`, `heading`, `accent`, `tint` and `rule_end`. Colors must be six-digit
hex values. `body_pt` defaults to 9.25 and accepts 8–12. See [rendering](rendering.md).
