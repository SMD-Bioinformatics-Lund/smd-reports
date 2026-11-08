# JSON input format

All applications use the same JSON document format. Set `application` to `coyote3`,
`genexus`, `cll_genie` or `pgx` to select the report identity and theme.

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
      "columns": [
        {
          "label": {
            "en": "Gene",
            "sv": "Gen"
          }
        },
        {
          "label": "HGVS"
        },
        {
          "label": "VAF (%)"
        }
      ],
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

Columns are declared once. Every row is a list containing exactly one value per column,
in column order. Add a column and the corresponding value to each row to extend a report.
Unknown fields, duplicate object keys, mismatched row lengths and non-finite numbers fail
validation. Use `null` for a missing cell; zero and false remain visible.

## Document fields

| Field | Description |
| --- | --- |
| `application` | One of the four report identities |
| `title` | Report title; plain text or translations |
| `language` | `sv` (default) or `en` |
| `analyte` | Optional heading label, such as `dna` or `rna` |
| `report` | Required report ID, sample ID and timezone-aware generation timestamp; optional author and metadata `fields` |
| `sections` | Ordered list of text, table, details, grid or image sections |
| `branding` | Logos and center information; see [branding](branding.md) |
| `presentation` | Paper size/orientation, custom dimensions, reserved header/footer space and accepted image formats |
| `provenance` | Optional application name/version, pipeline name/version and assay name |

Sections appear in JSON order. Include the sections and data you want to show.

## Translations

Titles, labels, text, captions, record headings and cell values accept either a string
or an object such as `{"en": "Gene", "sv": "Gen"}`. The selected language is used
throughout the report. If that translation is missing, English is used when available,
otherwise the supplied Swedish text. This is local text selection and works offline.

## Table columns

| Column field | Default | Effect |
| --- | --- | --- |
| `label` | Required | Column header or detail-field label |
| `width` | `1` | Relative width for ordinary table columns; `2` gets twice the width of `1` |
| `format` | `plain` | Plain text or sanitized `markdown` |
| `emphasis` | `false` | Bold values |
| `highlight` | `false` | Yellow background |
| `full_width` | `false` | Full-width row within a detail card |

Table widths come from the JSON columns. There are no gene-, assay- or application-specific
column positions in the renderer.

## Detailed findings

Use the same column definitions and row matrices for finding cards:

```json
{
  "kind": "details",
  "key": "variant-details",
  "fields_per_row": 3,
  "record_heading": "{0}: {1}",
  "columns": [
    {
      "label": {
        "en": "Gene",
        "sv": "Gen"
      }
    },
    {
      "label": "Variant"
    },
    {
      "label": "Classification",
      "full_width": true,
      "emphasis": true
    },
    {
      "label": "Comment",
      "full_width": true,
      "format": "markdown"
    }
  ],
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
  "columns": [
    {
      "label": "Sequence"
    },
    {
      "label": "V-GENE and allele"
    },
    {
      "label": "Score"
    },
    {
      "label": "Identity",
      "highlight": true
    }
  ],
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
  "heading": {"en": "Conclusion", "sv": "Slutsats"},
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

## Images and plots

Attach images to any section through `images`:

```json
{
  "kind": "table",
  "key": "cnvs",
  "heading": {"en": "Copy-number changes", "sv": "Kopietalsförändringar"},
  "columns": [{"label": {"en": "Gene", "sv": "Gen"}}, {"label": "CN"}],
  "rows": [["EXAMPLE", 6]],
  "images": [{
    "source": "plots/cnv-profile.tiff",
    "frame": 0,
    "caption": {"en": "Copy-number profile", "sv": "Kopietalsprofil"},
    "width_percent": 100,
    "max_height_mm": 120
  }]
}
```

For a separate plot section, use `kind: "image"`, `key`, optional `heading`, and the same
image fields. Set `page_break_before: true` when it should start on a separate page.

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
