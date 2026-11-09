# JSON input format

Reports use one JSON document format. Omit `application` for the neutral `generic` preset,
or select `generic`, `coyote3`, `genexus`, `cll_genie` or `pgx` explicitly.

```json
{
  "application": "genexus",
  "title": {
    "en": "NGS Analysis Report",
    "sv": "NGS-analysrapport"
  },
  "language": "en",
  "report": {
    "report_id": "DEMO-001",
    "sample_id": "SYNTHETIC-001",
    "generated_at": "2026-01-01T12:00:00Z"
  },
  "sections": [
    {
      "kind": "table",
      "key": "variants",
      "columns": {
        "en": ["Gene", "HGVS", "VAF (%)"],
        "sv": ["Gen", "HGVS", "VAF (%)"]
      },
      "rows": [
        [
          "BRAF",
          "p.Val600Glu",
          24
        ],
        [
          "EXAMPLE",
          "p.Example",
          18
        ]
      ],
      "heading": {
        "en": "Detected variants",
        "sv": "Detekterade varianter"
      }
    },
    {
      "kind": "summary",
      "key": "summary",
      "text": "Synthetic example conclusion.",
      "heading": {
        "en": "Conclusion",
        "sv": "Slutsats"
      }
    }
  ]
}
```

Column labels are grouped by language. Each language contains a list of labels in the same
order, and every row contains exactly one value per column. Add a label to each language
list and the corresponding value to each row to extend a report.
Unknown fields, duplicate object keys, mismatched row lengths and non-finite numbers fail
validation. Use `null` for a missing cell; zero and false remain visible.

## Document fields

| Field | Description |
| --- | --- |
| `application` | Optional preset; defaults to `generic` |
| `title` | Report title; plain text or translations |
| `language` | `sv` (default) or `en` |
| `analyte` | Optional heading label, such as `dna` or `rna` |
| `report` | Required report ID and timezone-aware generation timestamp; optional sample ID, author and metadata `fields` |
| `sections` | Ordered list of text, table, compact-table, details, grid or image sections |
| `branding` | Logos and center information; see [branding](branding.md) |
| `presentation` | Paper size/orientation, custom dimensions, reserved header/footer space and accepted image formats |
| `provenance` | Optional application name/version, pipeline name/version and assay name |

Sections appear in JSON order. Include the sections and data you want to show.

## Translations

Titles, metadata labels, text, captions, record headings and cell values accept either a string
or an object such as `{"en": "Gene", "sv": "Gen"}`. The selected language is used
throughout the report. If that translation is missing, English is used when available,
otherwise the supplied Swedish text. This is local text selection and works offline.
Column labels use language-specific lists, as shown below.

## Placeholders for later replacement

Put placeholder tokens directly in JSON string values, using uppercase names such as
`<PATIENT_NAME>`, `<PERSONAL_IDENTITY_NUMBER>`, `<REGISTRATION_DATE>` and `<SAMPLE_TYPE>`.
The Coyote3 DNA example uses `<TUMOR_SAMPLE_TYPE>`; its RNA example uses
`<SAMPLE_TYPE> / RNA`.

```json
{
  "label": {"en": "Patient name", "sv": "Patientnamn"},
  "value": "<PATIENT_NAME>"
}
```

The renderer preserves the token and escapes its angle brackets for HTML:

| Representation | Value |
| --- | --- |
| JSON input | `<PATIENT_NAME>` |
| HTML source | `&lt;PATIENT_NAME&gt;` |
| Browser or PDF text | `<PATIENT_NAME>` |

Use the raw token in JSON, not its HTML-encoded form. The HTML entities include their
semicolons. Tokens also remain visible inside Markdown paragraphs, tables and inline code;
they are not treated as HTML tags or filled automatically by the package.

Another system can replace tokens in the generated HTML before its final PDF conversion.
Match the encoded token in HTML source and HTML-escape the replacement value:

```python
from html import escape

html = renderer.render_html(report)
html = html.replace("&lt;PATIENT_NAME&gt;", escape("Example Person"))
```

This replaces every occurrence, including the screen metadata and repeating print header.
Apply replacements to JSON values or HTML before generating the final PDF; the PDF is the
rendered output. Supplied patient values are displayed as provided and are not replaced
with tokens.

## Table columns

Use `columns` to define the labels once for each language:

```json
{
  "columns": {
    "en": ["Gene", "Copy number"],
    "sv": ["Gen", "Kopietal"]
  },
  "column_options": {
    "1": {
      "width": 2,
      "emphasis": true
    }
  },
  "rows": [
    [
      "EXAMPLE",
      6
    ]
  ]
}
```

Supply `en`, `sv` or both. Language lists must be nonempty and have the same length.
If the selected language is absent, the supplied language is used. `column_options` is
optional and uses zero-based column indexes as JSON string keys. For example, `"1"`
configures the second column. It contains only the settings you want to change:

| Column option | Default | Effect |
| --- | --- | --- |
| `width` | `1` | Relative width for ordinary table columns; `2` gets twice the width of `1` |
| `format` | `plain` | Plain text or sanitized `markdown` |
| `emphasis` | `false` | Bold values |
| `highlight` | `false` | Yellow background |
| `full_width` | `false` | Full-width row within a detail card |

Table widths come from `column_options`; unspecified columns use equal weights. Unknown
settings and options referencing undeclared columns fail validation. The same column
format is used by tables, detail cards and grouped grids.

## Row highlighting

Result tables accept `row_options`, indexed by zero-based row position:

```json
{
  "kind": "table",
  "key": "variants",
  "columns": {"en": ["Gene", "Possible duplication"]},
  "rows": [["EXAMPLE", true], ["OTHER", false]],
  "row_options": {"0": {"highlight": true}}
}
```

`highlight: true` gives every cell in the selected row a pale pink background. Other
rows keep their normal styling. Row indexes must refer to supplied rows; unknown display
options fail validation. Highlight settings are preserved in portable JSON.

## Compact description tables

Use `compact_table` for gene lists, panel contents and haplotype lists. Each item occupies
a bordered cell. Cells use their content width and wrap onto another row when the
available width is filled. There is no separate column-header row.

```json
{
  "kind": "compact_table",
  "key": "covered-genes",
  "heading": {
    "en": "Table 1: Genes included in the panel",
    "sv": "Tabell 1: Gener inkluderade i panelen"
  },
  "items": ["APC", "BRAF", "EGFR", "ERBB2", "KRAS", "MET", "MLH1", "MSH2"]
}
```

Place this section after an analysis description or another narrative section. Supply
items in their display order; repeated values are retained. Labels, item translations,
zero, false and missing values use the same formatting rules as other report cells.
Long values wrap within the available cell width. Long lists continue across PDF pages.
Both HTML and PDF use the available report width, including custom paper dimensions.

Omit `columns` for automatic wrapping. Supply a positive column count to use equal-width
cells, for example `"columns": 10` for a gene panel or `"columns": 5` for longer haplotype
labels. The supported range is 1–64. Item text still wraps within each cell.

`format` defaults to `plain`; `markdown` enables the same sanitized formatting used by
other report sections. An empty `items` list displays `empty_text`, which can contain
English and Swedish translations. Plain items are escaped for HTML.

A haplotype item can combine its display values in a single string, such as
`"EXAMPLE-*2 (rsDEMO)"`. All compact-table options are included in the exported JSON Schema
and preserved when exporting and reloading reports.

## Detailed findings

Use the same column definitions and row matrices for finding cards:

```json
{
  "kind": "details",
  "key": "variant-details",
  "fields_per_row": 3,
  "record_heading": "{0}: {1}",
  "columns": {
    "en": ["Gene", "Variant", "Classification", "Comment"],
    "sv": ["Gen", "Variant", "Klassificering", "Kommentar"]
  },
  "column_options": {
    "2": {
      "full_width": true,
      "emphasis": true
    },
    "3": {
      "full_width": true,
      "format": "markdown"
    }
  },
  "rows": [
    [
      "EXAMPLE1",
      "p.Example",
      "Reviewed example",
      "**First** synthetic comment."
    ],
    [
      "EXAMPLE2",
      "p.Other",
      "Reviewed example",
      "**Second** synthetic comment."
    ]
  ],
  "heading": "Variant details"
}
```

`record_heading` references zero-based column positions. It produces a heading for each
row without repeating column labels or header values. Only simple placeholders such as
`{0}` are accepted. Omit it to use the first cell, or supply `record_titles`, with one
explicit title per row. Headings and explicit titles can also contain translations.

`fields_per_row` accepts 1–6 key/value pairs. Full-width or Markdown fields occupy separate
rows. Set `full_width_last` to true to batch compact fields first, as in the Genexus examples.
Long comments can continue across PDF pages.

## Grouped detail grids

Use `kind: "grid"` for arrangements such as the CLL Genie sequence table. Columns and
values still use the same matrix format. `grid_columns` defines the visual grid width;
`layout` arranges the columns within each record:

```json
{
  "kind": "grid",
  "key": "sequence-details",
  "record_heading": "{0}",
  "grid_columns": 5,
  "columns": {
    "en": ["Sequence", "V-GENE and allele", "Score", "Identity"],
    "sv": ["Sequence", "V-GENE and allele", "Score", "Identity"]
  },
  "column_options": {
    "3": {
      "highlight": true
    }
  },
  "rows": [
    [
      "Seq1",
      "IGHV3-21*01",
      1500,
      "97.5% (313/321)"
    ],
    [
      "Seq2",
      "DEMO-GENE",
      1200,
      "Reviewed example identity"
    ]
  ],
  "layout": [
    {
      "cells": [
        {
          "column": 0,
          "span": 5
        }
      ]
    },
    {
      "cells": [
        {
          "column": 1,
          "span": 2
        },
        {
          "column": 2,
          "span": 1,
          "mode": "inline"
        },
        {
          "column": 3,
          "span": 2,
          "mode": "inline"
        }
      ]
    }
  ]
}
```

Each layout cell references a zero-based `column` index. Its `span` counts visual grid
columns. The default `pair` mode renders a label and value, with `label_span: 1` by default.
`inline` places a bold label and value together; `label` or `value` shows just that part.
An optional `label` overrides the column label for that placement.

The spans in each layout row must add up to `grid_columns`. Add `hide_if_empty: true`
to a layout row to omit it when all referenced values are null or empty strings.
Zero and false do not count as empty. The complete CLL Genie JSON example preserves
sequence, subset, functionality, V/J scores and identities, D-region, FR/CDR, junction
and count rows using this layout.

## Summary, description and references

These sections are text objects with `heading`, `format` and `text`:

```json
{
  "kind": "summary",
  "key": "summary",
  "heading": {
    "en": "Conclusion",
    "sv": "Slutsats"
  },
  "format": "markdown",
  "text": {
    "en": "**Reviewed** example.\n\n| Sample | Status |\n| --- | --- |\n| DEMO | Reviewed |",
    "sv": "**Granskat** exempel.\n\n| Prov | Status |\n| --- | --- |\n| DEMO | Granskat |"
  }
}
```

Use `kind: "description"` or `kind: "references"` with the same fields. `format` accepts
`plain` (default) and `markdown`. Markdown supports headings, paragraphs, lists and tables.
When `heading` is omitted, the package selects the appropriate heading in English or
Swedish. An explicit empty heading hides it. Use `kind: "text"` for other narrative sections.

Summary sections have the yellow box and print/PDF page breaks before and after.
Markdown tables inside summaries use compact natural widths, plain borders and wrapping
cells. Ordinary result tables keep their own full-width layout.

### Markdown tables in summary text

Set the section's `format` to `markdown` to interpret Markdown in its `text` values.
The report's `language: "sv"` selects `text.sv`. In a JSON string, `\n` encodes a newline;
`\n\n` provides the blank line separating the paragraph from the table.

For example, this JSON value:

```json
{
  "sv": "Exempel på granskad slutsats. Endast för demonstration.\n\n| Prov | Status |\n| --- | --- |\n| SYNTHETIC-001 | Granskad |"
}
```

decodes to the following Markdown:

```markdown
Exempel på granskad slutsats. Endast för demonstration.

| Prov | Status |
| --- | --- |
| SYNTHETIC-001 | Granskad |
```

The report displays the paragraph followed by this table:

Exempel på granskad slutsats. Endast för demonstration.

| Prov | Status |
| --- | --- |
| SYNTHETIC-001 | Granskad |

The first pipe-delimited line supplies the column headings. The dashed line separates
the headings from data and is not printed. Each following line adds a row. The newline
escapes and pipe characters are not shown as text in the rendered table.

Markdown tables define their headings and rows in the text itself. `columns` and
`column_options` apply to structured `table`, `details` and `grid` sections instead.

Both the paragraph and table appear inside the yellow summary box. The table uses only
the width its contents need, up to the available width; long cell text wraps. The summary
starts on a new print/PDF page, and the next section starts on another page.
The [Coyote3 example PDF](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/0d5397f1273e39704003bcf00373ef6523a28695/examples/rendered/coyote3.pdf)
shows this summary on page 2.

With `format: "plain"`, or when `format` is omitted, the same content is displayed as text
with its pipe and dash characters. It does not become a table.

## Images and plots

Attach images to any section through `images`:

```json
{
  "kind": "table",
  "key": "qc",
  "heading": {
    "en": "Quality control",
    "sv": "Kvalitetskontroll"
  },
  "columns": {
    "en": ["Metric", "Result"],
    "sv": ["Mätvärde", "Resultat"]
  },
  "rows": [
    [
      {
        "en": "Coverage (%)",
        "sv": "Täckning (%)"
      },
      98
    ]
  ],
  "images": [
    {
      "source": "plots/coverage.tiff",
      "frame": 0,
      "caption": {
        "en": "Coverage profile",
        "sv": "Täckningsprofil"
      },
      "width_percent": 100,
      "max_height_mm": 120
    }
  ]
}
```

For a separate plot section, use `kind: "image"`, `key`, optional `heading`, and the same
image fields. Set `page_break_before: true` when it should start on a separate page.

For a full-page CNV overview, place an image section after the summary and before the
detailed findings:

```json
{
  "kind": "image",
  "key": "cnv-profile",
  "heading": {
    "en": "Copy-number profile, genome-wide overview",
    "sv": "Kopietalsprofil, genomisk översikt"
  },
  "source": "plots/cnv-profile.tiff",
  "page_break_before": true,
  "width_percent": 100
}
```

Set `page_break_before: true` on the following detail section as well. This keeps the
overview on its own page, independently of image dimensions. Omit the image section when
no profile is available. Section order and page breaks are controlled by the JSON input.

| Image field | Default | Description |
| --- | --- | --- |
| `source` | Required | Local path or embedded base64 image URI |
| `caption` | Empty | Caption text or English/Swedish translations |
| `alt` | Caption | Alternative text or translations |
| `frame` | `0` | Zero-based GIF/TIFF/APNG frame or page |
| `width_percent` | `100` | Image width relative to available content width |
| `max_height_mm` | Available page height | Additional height limit; aspect ratio is preserved |

PNG, JPEG, static SVG, WebP, GIF, TIFF and BMP are supported. Restrict report images with
`presentation.accepted_image_formats`, for example `["png", "jpeg", "svg"]`.
The selected frame is used for multi-frame files. WebP/GIF/TIFF/BMP and multi-frame PNG
are converted to a static PNG for portable HTML; SVG stays vector. Portable JSON retains
the original embedded image and frame selection. Logo loading uses the same supported
formats independently of the report-image restriction.

## Provenance

Input contains only the optional context supplied alongside the report:

```json
{
  "provenance": {
    "application_name": "Example application",
    "application_version": "1.2.0",
    "pipeline_name": "Example pipeline",
    "pipeline_version": "3.1.0",
    "assay_name": "Example assay"
  }
}
```

The package computes its own name, installed package version and template revision.
These values are recorded in HTML metadata and exposed through `report.rendering_metadata`;
they are not input fields. Portable JSON retains the supplied context without requiring
manual renderer-version values.

## Page size

See [page settings](rendering.md#page-size) for presets, landscape orientation and custom
width/height in millimetres.

## JSON Schema

```sh
smd-reports schema --output report.schema.json
```

The exported JSON Schema describes the format supported by the installed package and can
be used by editors or validators. Pin the package version when you need a fixed input format.
