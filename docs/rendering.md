# HTML and PDF rendering

`ReportRenderer` accepts a validated `Report`, usually returned by `ReportLoader.load()`
or an application builder's `build()` method.

```python
from pathlib import Path
from smd_reports import ReportLoader, ReportRenderer

document = ReportLoader().load("report.json")
renderer = ReportRenderer()
Path("report.html").write_text(renderer.render_html(document), encoding="utf-8")
Path("report.pdf").write_bytes(renderer.render_pdf(document))
```

## Portable HTML

Exported HTML includes the shared CSS, print/page rules, embedded Source Sans 3 font data
and supplied artwork. There are no external stylesheet, font or image dependencies.
Plain text is escaped and Markdown is sanitized. Exported reports do not require JavaScript.

Move the HTML to another machine and convert with:

```sh
weasyprint report.html report.pdf
```

The destination needs WeasyPrint and its native runtime, but not `smd-reports`, the input
JSON or the original logo files. No `base_url` is needed for the embedded resources.

## Print layout

Reports use A4 pages and the Coyote3/Genexus clinical layout primitives. Print styling
repeats compact patient metadata and center branding
in headers, places eligible accreditation artwork in footers and includes page numbering.
Tables repeat headings and can span pages. `page_break_before` applies to print/PDF;
HTML preview is a continuous document. Short rows are kept together where feasible.

Yellow conclusion sections start on a new PDF/print page, and subsequent content starts
on another new page. A long conclusion may span multiple pages; its text is not clipped
or forced into a single page. These breaks apply to every application. The
`summary_new_page` setting may be omitted or set to true; false is rejected.

Patient metadata uses two label/value columns in HTML and three compact columns in PDF
headers, with wide values spanning a row. Genexus repeats the report title in its PDF
header; Coyote3 keeps its document heading in the report body. Accreditation artwork is
left aligned in the footer, opposite the template revision and page count. Package and
schema provenance is recorded in HTML meta tags and snapshots, without an extra printed
technical audit line on the clinical report.

`ReportConfig.header_height_mm` reserves header space. The framework does not silently
shrink long metadata to fit. Verify large headers, long interpretations and oversized rows
with the expected data before adopting a layout.

## Language

`language="sv"` uses Swedish built-in labels and `Sida X av Y` numbering.
`language="en"` uses English labels and `Page X of Y`. Supplied clinical text, custom
column labels and custom metadata labels remain unchanged.

## Themes

| Application | Theme |
| --- | --- |
| Coyote3 | Purple/orange |
| Genexus | Blue |
| CLL Genie | Dark orange |
| PGx | Teal |

The default theme follows the application's identity. A renderer can register additional
themes without replacing the built-in names:

```python
from smd_reports import ReportRenderer, Theme

renderer = ReportRenderer()
renderer.register_theme(Theme(
    name="center", heading="#176B68", accent="#278780",
    tint="#edf7f5", rule_end="#9dcac0",
))
# document is a Report returned by a loader or builder:
html = renderer.render_html(document, theme="center")
```

## Reproducibility

Preserve the normalized input snapshot, package version, fonts, renderer version and native
runtime alongside reviewed outputs. Embedded HTML removes asset-path dependencies; it does
not guarantee byte-identical PDFs or identical pagination across rendering environments.

For missing PDF dependencies, see [installation](installation.md). For exceptions and
return types, see the [Python API reference](reference.md).
