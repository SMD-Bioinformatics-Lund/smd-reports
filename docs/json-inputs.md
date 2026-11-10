# JSON input format

See the [configuration reference](configuration.md) for every supported field, default,
allowed value and cross-field constraint. This guide provides worked examples.

Reports use one JSON document format. Themes, layout settings and sections can be selected
independently. Omit `preset` for neutral defaults, or select `generic`, `coyote3`, `genexus`,
`cll_genie` or `pgx` for a predefined combination. The legacy `application` selector remains supported.

```json
{
  "preset": "genexus",
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

## Themes, layouts and presets

Every section type is available in every report. A theme supplies colors and typography;
a layout controls the placement of branding, titles and metadata. Presets provide defaults
for these settings. Explicit `theme` and `layout` values override the preset independently.

```json
{
  "theme": "pgx",
  "layout": {
    "header": "branded",
    "metadata_heading": {"en": "Document information", "sv": "Dokumentinformation"},
    "document_label": {"en": "Analysis report", "sv": "Analysrapport"}
  },
  "branding": {
    "application_name": "Example Analytics",
    "application_logo": "logos/application.svg",
    "organization": "Example Center"
  }
}
```

These are presentation fields to add to a report containing `title`, `report` and `sections`.
No application identity is required. Record the originating application in `provenance`.
The [custom example](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/inputs/custom.json)
contains a complete document.

| Layout field | Effect |
| --- | --- |
| `header` | `center` for center branding alone; `branded` for product and center branding |
| `header_rule` | Show the theme-colored separator below either header style; defaults to `true` |
| `repeat_title` | Repeat the document title in the printed header; omit the duplicate body title |
| `black_title` | Use black for the document title and its label |
| `metadata_borders` | Add top and bottom rules around metadata |
| `metadata_heading` | Literal or translated metadata heading |
| `document_label` | Literal or translated label above the title; `analyte` remains an optional prefix |

Omitted or null layout fields inherit their preset defaults. Partial overrides remain partial
when JSON is exported and reloaded. Use `preset` for new documents; when both `preset` and
legacy `application` are present, the legacy selector must be `generic` or match `preset`.

All configurations retain the common typography, table components, page numbering,
accreditation footer and section ordering. Summary sections retain their pale yellow background,
darker yellow left border and page breaks before and after, independently of the chosen theme.

## Document fields

| Field | Description |
| --- | --- |
| `preset` | Optional presentation defaults; `generic` when omitted |
| `application` | Legacy preset selector; retained for existing inputs |
| `theme` | Independent built-in or registered theme name |
| `layout` | Independent header, title and metadata settings |
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
Column labels use language-specific lists, as shown below. Package labels use English
source text; Swedish interface translations are selected only for `language: "sv"`.

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
| `width` | Automatic | Optional relative weight; when supplied, unspecified columns use `1` |
| `format` | `plain` | Plain text or sanitized `markdown` |
| `emphasis` | `false` | Semibold values (font weight `600`), unless `font_weight` is set |
| `font_weight` | `null` | `normal` (400), `semibold` (600), or `bold` (700) |
| `italic` | `null` | `true` for italic; `false` for upright text |
| `highlight` | `false` | Yellow background |
| `badge` | Omitted | Optional preset, custom-color or theme-colored badge |
| `full_width` | `false` | Full-width row within a detail card |

Ordinary tables size their columns automatically from translated headings and displayed
content when no `width` is supplied. Longer values receive more space; text wraps when
the available width is insufficient. Table styling and the overall report width stay the same.

Supplying any explicit `width` selects proportional widths for the entire table. Unspecified
columns then use weight `1`; explicit weights, including `1`, survive JSON export and reload.
Unknown settings and options referencing undeclared columns fail validation. The same column
format is used by tables, detail cards and grouped grids.

## Column text styling

Set `emphasis: true` to make every value in a column semibold (font weight `600`).
Column indexes are zero-based: `"0"` selects the first column and `"6"` selects the seventh.
For example, the classification values in this table, including `Tier I`, are semibold:

```json
{
  "kind": "table",
  "key": "variants",
  "columns": {
    "en": ["Gene", "Chromosome", "Exon", "HGVS", "VAF", "Tier", "Classification"]
  },
  "column_options": {
    "6": {"emphasis": true}
  },
  "rows": [
    ["BRAF", "7", "15", "p.Val600Glu", "24%", "I", "Tier I"],
    ["EXAMPLE2", "1", "2", "p.Example2del", "18%", "II", "Tier II"]
  ]
}
```

`emphasis` changes cell values; column headings retain their standard styling. The option
also applies to value fields in detail cards and grouped grids. Omit it or set it to `false`
for normal text.

Bold and italic text use Markdown within individual values. Set `format: "markdown"`
for the relevant columns, then add the markers to the values:

```json
{
  "kind": "table",
  "key": "formatted-values",
  "columns": {"en": ["Gene", "Classification"]},
  "column_options": {
    "0": {"format": "markdown"},
    "1": {"format": "markdown"}
  },
  "rows": [["*BRAF*", "**Tier I**"], ["*EXAMPLE2*", "Tier II"]]
}
```

`*text*` renders italic, `**text**` renders bold, and `***text***` combines both.
Markdown cells trim the first block’s top margin and the last block’s bottom margin, so
a single formatted paragraph adds no extra vertical spacing. Multiple paragraphs retain
their internal spacing.

With `format: "plain"`, these markers remain literal text. `font_weight` and `italic`
can also be set in `column_options` without adding Markdown to the values.
[Badge labels](#optional-badges) are plain text and default to semibold.

## Individual cell text styling

Use `cell_options` to format individual values without changing their text. The first key
selects the zero-based data row; the second selects the zero-based column. Only cells that
need an override are listed:

```json
{
  "kind": "table",
  "key": "classifications",
  "columns": {"en": ["Gene", "Classification"]},
  "rows": [["BRAF", "Tier I"], ["EXAMPLE1", "Tier II"], ["EXAMPLE2", "Tier III"]],
  "cell_options": {
    "0": {"0": {"italic": true}, "1": {"font_weight": "semibold"}},
    "1": {"1": {"font_weight": "bold", "italic": true}},
    "2": {"1": {"font_weight": "normal", "italic": false}}
  }
}
```

This renders *BRAF* in italic, `Tier I` in semibold, `Tier II` in bold italic and
`Tier III` in normal upright text. Headings retain their standard styling.

The [Coyote3 example](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/inputs/coyote3-dna.json)
includes Tier I and Tier II rows with semibold and normal classification cells, respectively.

| Cell option | Default | Effect |
| --- | --- | --- |
| `font_weight` | `null` | Inherit, or select `normal` (400), `semibold` (600), `bold` (700) |
| `italic` | `null` | Inherit, or select italic (`true`) or upright (`false`) text |

Cell settings override column settings, including `emphasis`. Omitted or `null` settings
inherit the column style. Use `normal` and `false` to reset individual cells in a styled
column. Badge text follows explicit cell typography; its color remains unchanged. Markdown
inline emphasis remains available within a value; explicit Markdown bold or italic spans
retain their own styles.

The same options work in `details` and `grid` sections. Their outer key selects a data
record in `rows`, not a visual row within the card or grid. Repeated grid references to a
column in the same record use the same cell typography. Cell options do not change column
widths, labels, layout or values. Unknown settings, malformed indexes and references outside
the supplied rows or columns fail validation.

Standalone HTML embeds Source Sans 3 regular, semibold and bold fonts with matching italic
faces. PDF rendering uses the same bundled fonts without network access.

## Optional badges

Tables, detail cards and grouped grids share the same `column_options.badge` setting.
Omit it to retain normal text formatting. Badge styling never changes the supplied cell
value or assigns a tier automatically.

For a whole column, choose a predefined color. A value such as `Strong clinical significance`
keeps that exact label and uses the Tier 1 color:

```json
{
  "column_options": {
    "1": {"badge": {"preset": "tier1"}}
  }
}
```

| Preset | Background color |
| --- | --- |
| `tier1` | `#af6246` |
| `tier2` | `#ae8540` |
| `tier3` | `#4f7d9f` |
| `tier4` | `#4b8b76` |

Use `"badge": {"color": "#4f7d9f"}` for a custom background, or `"badge": {}` to use
the selected theme's heading color. Foreground text is automatically black or white for
legibility. Custom colors must use six-digit hexadecimal notation (`#RRGGBB`). Choose a
preset or a custom color, rather than combining both.

When rows require different styles, map their displayed values once:

```json
{
  "columns": {"en": ["Tier", "CLL subset"]},
  "column_options": {
    "0": {"badge": {"values": {"I": "tier1", "II": "tier2", "III": "tier3", "IV": "tier4"}}},
    "1": {"badge": {"values": {"#2": {"color": "#4f7d9f"}}}}
  },
  "rows": [["I", "#2"], ["II", "#8"]]
}
```

The first row shows two badges; `#8` in the second row remains ordinary text. Mapping
keys match the displayed text in the selected report language. Each entry accepts a tier
name or an object with `preset`, `color`, or no properties for the theme default.
Use either a whole-column style or a value mapping. Unlisted values retain normal column
formatting. Null and empty values keep the ordinary missing-value display without a badge;
zero and false remain visible.

Badge labels are escaped plain text, including when the column otherwise supports Markdown.
Badges wrap within narrow cells and remain selectable text in PDF output. Colors and styles
are embedded in HTML and require no external assets.

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
items in their display order; repeated values are retained. Item translations, zero and
false use the same formatting rules as other report cells. Null, empty and whitespace-only
values are omitted. The final row contains only supplied items, with no empty boxes.

Column counts are calculated from the bundled font and the selected paper width. Whole
items continue onto consecutive rows with shared borders and minimal vertical cell padding.
Text stays on one line in each cell and is 2.5 points smaller than normal report text.
The caption uses normal body size, bold weight and black text. Long lists continue across
PDF pages. Custom paper dimensions are supported.

Omit `columns` for automatic sizing. Set a positive upper limit for equal-width cells,
for example `"columns": 10` for a gene panel or `"columns": 5` for longer haplotype labels.
Fewer columns are used when needed to fit the page. The supported range is 1–64. An item
that cannot fit on one line raises `ReportInputError`; use a wider page, shorter label or
an ordinary table. Characters must be available in the bundled report font.

`format` defaults to `plain`; `markdown` supports inline bold, italic and code formatting.
Block elements are rejected. Plain items are escaped for HTML. An empty table displays
`empty_text`, which can contain English and Swedish translations.

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
