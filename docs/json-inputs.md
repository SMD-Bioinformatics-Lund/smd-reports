# JSON inputs and portable HTML

Install with `python -m pip install smd-reports`, then run `smd-reports --help` or
`python -m smd_reports --help`.
The distribution does not need an application server, database or network connection to render.

## Input envelope

```json
{
  "schema_version": 1,
  "application": "coyote3",
  "title": "Molekylärgenetisk analysrapport",
  "language": "sv",
  "report": {
    "report_id": "SYNTHETIC-REPORT-001",
    "sample_id": "SYNTHETIC-001",
    "generated_at": "2026-01-01T12:00:00Z",
    "author": "Demo User",
    "fields": []
  },
  "branding": {
    "organization": "Demo center",
    "address": "Example address",
    "telephone": "000-000000",
    "center_logo": "logos/center.svg",
    "accreditation_logo": "logos/accreditation.svg",
    "accredited": true
  },
  "data": {
    "analyte": "dna",
    "summary": "Granskad slutsats från applikationen.",
    "description": "Analysbeskrivning från applikationen."
  }
}
```

`schema_version` and `application` are required. Supported application names are `coyote3`,
`genexus`, `cll_genie` and `pgx`. `language` defaults to `sv` and accepts `sv` or `en`.
`presentation` optionally supplies section order, summary page breaks, header height and
the footer space reserved for eligible accreditation artwork.
`provenance` optionally supplies application/configuration/assay/source versions.
Unknown fields, duplicate JSON keys, non-finite numbers and unsupported schema versions fail.

Export each application's full schema with `smd-reports schema --application NAME --output FILE`.
Schema export describes structural fields; the loader additionally checks analysis consistency,
CLL report constraints, local logo availability and SVG safety.

The application-specific `data` contains clinical content, not another copy of identity,
branding or language. Coyote3 requires its DNA/RNA analyte. CLL Genie requires its report type
and reviewed conclusion; positive reports also need submission identity and sequence facts.
PGx accepts typed prepared recommendations, variants and low-depth targets; the Python
`PGxReport.from_files()` interface remains available for its existing TSV preparation pipeline.
Genexus supplies prepared content; upstream source-file parsing remains in its application.

## Logo loading and snapshots

Relative artwork paths resolve against the JSON file's directory, regardless of the current
working directory. Absolute local paths and already embedded data URIs are accepted too.
Paths are only supported for the three branding logo fields; plots must be embedded.
Only explicitly supplied local files are read. HTTP/file URLs are not accepted.
The same restricted static SVG and raster validation applies to file and embedded artwork.
Missing/unreadable artwork fails the command; it is not silently omitted.

`normalize` saves the built document with embedded logos and all selected content. This is
the normalized `Report` format, distinct from the application input envelope. Both can be
loaded by `ReportLoader.load()` and passed to `validate`/`render`/`normalize`. Normalized
snapshots do not rerun application builders or clinical rules; they preserve the supplied
document, language and template provenance. The renderer uses installed templates, so retain
the matching package and environment when regenerating an approved layout.

Commands require an explicit output path and refuse to overwrite the input JSON. Validation
errors return exit code 2 and identify fields/types without printing clinical values. Successful
commands return 0. Application storage, encryption, access control and retention remain outside
this tool; JSON snapshots contain the report's data and require the same controls as reports.

## Swedish and English

The selected language controls built-in metadata labels, generated headings/table labels,
boolean display and page numbering (`Sida X av Y` / `Page X of Y`). It never translates
supplied clinical summaries, recommendations, classifications, details, caller-defined section
titles, or metadata labels. Supply those in the requested language from the application.

## Portable HTML

The HTML embeds one shared stylesheet, print rules, Source Sans 3 font data and all supplied
artwork. It has no external stylesheet/font/image dependency. Moving the HTML does not
require preserving JSON-relative paths or supplying a `base_url` to WeasyPrint.

```sh
smd-reports render report.json --format html --output report.html
weasyprint report.html report.pdf
```

HTML preview uses screen styling; WeasyPrint uses the embedded print styling, repeating headers,
footer artwork and pagination. No JavaScript or browser print interaction is needed. Offline
standalone conversion is covered by a test that removes source JSON/logo files and blocks
imports of this package before running plain WeasyPrint in another directory.

## Synthetic examples

`examples/inputs/` contains JSON for all applications and the CLL no-result cases. Clinical
data is synthetic and all artwork consists of generic placeholders. Supply your chosen
application, center and accreditation logos in production JSON. Regenerate inputs using
`python examples/json_inputs.py` after changing the Python demo inputs.
