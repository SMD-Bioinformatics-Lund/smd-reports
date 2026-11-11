# Configuration reference

This reference lists the report JSON fields, supported values, defaults and interactions.
Use the [JSON guide](json-inputs.md) for worked examples and the
[Python reference](reference.md) for loading and rendering methods.

Report contents are supplied as JSON. Renderer registration configures additional themes;
it does not change the report input format. Unknown JSON fields are rejected.

## Value types and defaults

- **Text:** a literal string or a translation object with `en`, `sv`, or both.
  Translation objects must contain at least one language. The requested translation is
  used first, followed by English and then the supplied alternative.
- **Cell value:** a string, integer, finite number, boolean, `null`, or translated text.
  Zero and false are preserved. Ordinary `null` and empty-string cells display `-`.
- **Image reference:** a local path or validated base64 image data URI. Remote URLs are
  rejected. See [image fields](#image-fields).
- **Index:** a zero-based position. Index keys in `column_options`, `cell_options` and `row_options` are
  JSON strings such as `"0"`, `"1"` and `"6"`; leading zeros are rejected.
- **Required:** the field must be supplied. `{}` and `[]` defaults are independent objects
  for each report. `null` is accepted only where the table explicitly allows it.
- Numeric values must be finite. Duplicate JSON object keys are rejected. Relative paths
  resolve against the input file's directory, or the `base_dir` passed to `loads()`.

## Report document

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `title` | Required | Text; the document title |
| `report` | Required | [Report identity](#report-identity-and-metadata) object |
| `language` | `sv` | `en` or `sv`; selects interface labels and supplied translations |
| `preset` | `null` | `generic`, `coyote3`, `genexus`, `cll_genie` or `pgx`; supplies presentation defaults |
| `application` | `generic` | Legacy preset selector; the same five choices |
| `theme` | `null` | Nonempty built-in or registered theme name; overrides the preset's theme |
| `layout` | `{}` | [Layout overrides](#layout) |
| `analyte` | `""` | Free-text label, rendered uppercase before the document label |
| `branding` | `{}` | [Product, center and accreditation branding](#branding) |
| `provenance` | `{}` | [Application, pipeline and assay identifiers](#provenance) |
| `presentation` | `{}` | [Paper and image settings](#paper-and-image-settings) |
| `sections` | `[]` | Ordered [section objects](#section-fields) |

With neither selector supplied, the effective preset is `generic`. If both `preset` and
`application` are supplied, `application` must be `generic` or match `preset`.
The originating application name can be recorded independently in `provenance.application_name`.
Every section type works with every preset, theme and layout.

### Selection precedence

1. `ReportRenderer.render_html(..., theme=...)` or `render_pdf(..., theme=...)` overrides
   JSON `theme`; JSON `theme` overrides the preset's theme.
2. Each non-null `layout` field overrides that preset's corresponding layout default.
   Omitted and null layout fields inherit. Partial overrides survive JSON export and reload.
3. Explicit product branding overrides preset wordmarks. A custom `application_name` does
   not inherit the preset's suffix unless `application_suffix` is supplied explicitly.
4. Section order follows `sections`. The selected preset never inserts clinical content.

### Complete report example

This document combines an independent theme and branded header, automatic result-table
widths, tier badges, a Markdown summary and a compact gene table. It requires no image files.

```json
{
  "title": "Example analysis report",
  "language": "en",
  "theme": "pgx",
  "layout": {
    "header": "branded",
    "header_rule": true
  },
  "branding": {
    "application_name": "Example Analytics",
    "organization": "Example Center"
  },
  "report": {
    "report_id": "EXAMPLE-001",
    "sample_id": "SYNTHETIC-001",
    "generated_at": "2026-01-01T12:00:00Z"
  },
  "sections": [
    {
      "kind": "table",
      "key": "results",
      "columns": {
        "en": [
          "Gene",
          "Classification"
        ]
      },
      "column_options": {
        "1": {
          "emphasis": true,
          "badge": {
            "values": {
              "Tier I": "tier1",
              "Tier II": "tier2"
            }
          }
        }
      },
      "rows": [
        [
          "EXAMPLE1",
          "Tier I"
        ],
        [
          "EXAMPLE2",
          "Tier II"
        ]
      ]
    },
    {
      "kind": "summary",
      "key": "summary",
      "format": "markdown",
      "text": "**Reviewed** synthetic example."
    },
    {
      "kind": "description",
      "key": "method",
      "format": "markdown",
      "text": "### Method\nSynthetic example method.\n\n### Scope\nExample results."
    },
    {
      "kind": "compact_table",
      "key": "genes",
      "heading": "Panel genes",
      "items": [
        "EXAMPLE1",
        "EXAMPLE2"
      ]
    }
  ]
}
```

## Preset defaults

The theme name matches the preset name. All presets show the colored header rule by default.

| Preset | Header | Product name and suffix | Additional enabled layout flags |
| --- | --- | --- | --- |
| `generic` | `center` | Empty | None |
| `coyote3` | `branded` | Coyote + 3 | None |
| `genexus` | `center` | Empty | `repeat_title`, `black_title`, `metadata_borders` |
| `cll_genie` | `branded` | CLL Genie | None |
| `pgx` | `center` | Empty | None |

`repeat_title`, `black_title` and `metadata_borders` default to false except for Genexus.
Generic metadata uses `Report information` and its document label is `Report`.
The other presets use `Sample information` and `Analysis report`, respectively.

These labels use English source text and the selected report language. Coyote3's `dna`
and `rna` analytes identify independently tracked template revisions and appear in its
footer template name. Other analyte strings still appear in the document label.

## Layout

All raw field defaults are `null`, meaning inherit the preset value above.

| Field | Allowed override | Effect |
| --- | --- | --- |
| `header` | `center`, `branded` | Center branding alone, or product branding beside the center |
| `header_rule` | Boolean | Show or hide the theme-colored separator, independently of product branding |
| `repeat_title` | Boolean | Repeat the document title in the printed header and hide its duplicate body title in print |
| `black_title` | Boolean | Use black for the main title and document label |
| `metadata_borders` | Boolean | Add top and bottom rules around metadata |
| `metadata_heading` | Text | Override the metadata block heading |
| `document_label` | Text | Override the label above the main title |

The normal title remains visible in the HTML screen layout. `black_title` does not change
section-heading colors. A branded header can show a name, a logo, or both. Center details
and accreditation artwork do not require a product identity.

## Branding

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `organization` | `""` | Text; center name |
| `department` | `""` | Text; department name |
| `address` | `""` | Text; address, including line breaks |
| `telephone` | `""` | String; telephone contact |
| `email` | `""` | String; email contact |
| `website` | `""` | String; displayed website text |
| `application_name` | `null` | Text or null; inherit preset name when null; `""` hides the name |
| `application_suffix` | `null` | String or null; appended directly in the theme's suffix color |
| `application_logo` | `null` | Image reference or null; displayed with `layout.header: "branded"` |
| `center_logo` | `null` | Image reference or null; beside the center details |
| `accreditation_logo` | `null` | Image reference or null; left footer when `accredited` is true |
| `accredited` | `false` | Boolean; enables the supplied accreditation logo |
| `center_logo_width_mm` | `11.64` | Number, 5–35 mm |
| `application_logo_width_mm` | `13.75` | Number, 5–30 mm |
| `accreditation_logo_width_mm` | `25` | Number, 10–35 mm |
| `accreditation_label` | `Accreditation` | Text; alternative text for the accreditation image |

Literal center and product names remain unchanged. Explicit translation objects select
language-specific names and addresses. The suffix is literal text; include a separator
in it if needed. No institutional artwork or contact information is supplied by default.
Logo artwork keeps its aspect ratio; the fixed header image frame also limits its height.
See [branding](branding.md) for image preparation and self-contained SVG requirements.

## Report identity and metadata

The `report` object contains:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `report_id` | Required | Nonempty string; document identifier |
| `generated_at` | Required | ISO timestamp with timezone, for example `2026-01-01T12:00:00Z` |
| `sample_id` | `""` | String; sample/reference identifier; omitted from display when empty |
| `author` | `""` | String; report creator's displayed name |
| `sample_id_label` | `null` | Literal or translated sample ID caption |
| `generated_at_label` | `null` | Literal or translated generation date caption |
| `report_id_label` | `null` | Literal or translated report ID caption |
| `author_label` | `null` | Literal or translated text; override the automatic author label |
| `fields` | `[]` | Ordered objects containing required `label` (text) and `value` (cell value) |

Each entry in `report.fields` contains:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `label` | Required | Text; metadata label |
| `value` | Required | Cell value; displayed metadata content |

The metadata block includes the sample ID when present, generation date, author and report
ID. Additional fields retain their order; the sample ID is inserted after the first two
additional fields. Screen metadata uses two label/value pairs per row and repeating print
metadata uses three. Long printed metadata values can span the row.

`report.sample_id_label`, `report.generated_at_label`, `report.author_label` and
`report.report_id_label` override their captions in both screen metadata and repeating PDF
headers. Omit it or use `null` for the built-in captions in the selected language.
A string is displayed literally. An object selects `en` or `sv`, falling back to English
or the available translation. An empty string leaves the caption blank and retains the
author value. Labels are escaped plain text, without Markdown or HTML formatting.

```json
{
  "author": "Example User",
  "author_label": {"en": "Prepared by", "sv": "Sammanställd av"}
}
```

Place these fields inside the `report` object. Additional `report.fields` entries do not
replace the automatic author label.

## Provenance

All fields default to `""` and accept strings:

| Field | Meaning |
| --- | --- |
| `application_name` | Originating application |
| `application_version` | Application version |
| `pipeline_name` | Pipeline name |
| `pipeline_version` | Pipeline version |
| `assay_name` | Assay name |

The package supplies `package_name`, `package_version` and `template_version` automatically
when rendering. Do not send those fields, `schema_version`, or other version keys in the
report JSON. Inspect `report.rendering_metadata` for the computed values. The actual theme
key is recorded separately as HTML metadata. See [version metadata](rendering.md#template-and-package-versions).

## Paper and image settings

The `presentation` object contains:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `page_size` | `A4` | Named size below, or `custom`; names are case-sensitive |
| `orientation` | `null` | `portrait`, `landscape`, or null to preserve the supplied dimensions |
| `custom_width_mm` | `null` | Positive number; required only for `page_size: "custom"` |
| `custom_height_mm` | `null` | Positive number; required only for `page_size: "custom"` |
| `header_height_mm` | `65` | Number, 40–120; reserved repeating-header area |
| `footer_height_mm` | `38` | Number, 22–50; accreditation-footer area |
| `accepted_image_formats` | All seven formats | Nonempty, duplicate-free list of `png`, `jpeg`, `svg`, `webp`, `gif`, `tiff`, `bmp` |

Custom dimensions must be supplied together and cannot accompany a named paper size.
After orientation is applied, width must exceed 52 mm and height must exceed
`header_height_mm + footer_height_mm + 20` mm. Small landscape sizes may need smaller
reserved areas. Side margins are fixed at 16 mm.

The visible accreditation logo uses the configured footer area. Without a visible
accreditation logo, print rendering reserves 22 mm at the bottom. Page validation still
checks the configured footer height. `accepted_image_formats` controls report plots and
section images, rather than branding logos; use `jpeg` as the format name, even for `.jpg` files.

### Named paper dimensions

| Size | Width × height (mm) |
| --- | --- |
| `A0` | 841 × 1189 |
| `A1` | 594 × 841 |
| `A2` | 420 × 594 |
| `A3` | 297 × 420 |
| `A4` | 210 × 297 |
| `A5` | 148 × 210 |
| `A6` | 105 × 148 |
| `B0` | 1000 × 1414 |
| `B1` | 707 × 1000 |
| `B2` | 500 × 707 |
| `B3` | 353 × 500 |
| `B4` | 250 × 353 |
| `B5` | 176 × 250 |
| `B6` | 125 × 176 |
| `Letter` | 215.9 × 279.4 |
| `Legal` | 215.9 × 355.6 |
| `Tabloid` | 279.4 × 431.8 |
| `Executive` | 184.15 × 266.7 |

## Section fields

All section kinds share these fields:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `key` | Required | Nonempty string, unique within the report |
| `kind` | Required selector | `text`, `summary`, `description`, `references`, `table`, `compact_table`, `details`, `grid`, `image` |
| `heading` | `""` | Text; empty hides the heading; narrative defaults are listed below |
| `page_break_before` | `false` | Boolean; request a new print page before this section |
| `images` | `[]` | Ordered [image objects](#image-fields), rendered after the section's content |

Section kinds use one shared rendering system. Ordinary result tables repeat their column
headings across pages. Long narrative content and full-width detail comments can continue
onto later pages. All sections retain the shared page header and footer.

## Text, summary, description and references

Description prose uses the reusable `justified-text` CSS class in both plain text and
Markdown. Paragraphs are justified, use text 1.25 pt smaller than the report body, and
have a 1.2 line height. Headings and table cells retain their own typography.

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `kind` | Required in section JSON | `text`, `summary`, `description`, `references`; supply explicitly in report JSON |
| `text` | Required | Text; literal or translated content |
| `format` | `plain` | `plain` or sanitized `markdown` |

When `heading` is omitted, `summary` uses `Conclusion`, `description` uses `Analysis
description`, and `references` uses `References`; `text` has no heading. These defaults
are translated into the report language. Supplying `heading: ""` suppresses the heading.

Summary sections always have print page breaks before and after, even if
`page_break_before` is false. Their yellow box, darker left border and compact Markdown
table styling are shared across themes. Description subheadings use tighter spacing.

Plain format preserves line breaks and escapes HTML. Markdown supports headings, emphasis,
lists, quotations, code and tables. Scripts, arbitrary attributes, styles, links and embedded
Markdown images are not retained; add images through image objects. Compact-table items
have narrower Markdown support, and badge labels are always literal text.

## Matrix data and column options

`table`, `details` and `grid` use the following common fields:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `columns` | Required | Object containing nonempty `en` and/or `sv` label lists |
| `rows` | `[]` | List of row lists, with one cell value per declared column |
| `column_options` | `{}` | Column-index keys mapped to the display options below |
| `cell_options` | `{}` | Row-index keys mapped to column-index keys and typography overrides |
| `empty_text` | `No reportable results` | Text; displayed when no rows are supplied |

All translated label lists must have the same length. An options index must reference a
declared column. Rows with too few or too many values are rejected.

| Column option | Default | Accepted value and effect |
| --- | --- | --- |
| `width` | Automatic for tables | Positive relative weight; supplying any weight selects proportional result-table widths; other columns then use weight 1 |
| `format` | `plain` | `plain` or `markdown` |
| `emphasis` | `false` | Boolean; semibold cell values unless `font_weight` is set |
| `font_weight` | `null` | Inherit, or `normal` (400), `semibold` (600), `bold` (700) |
| `italic` | `null` | Inherit, or italic (`true`) or upright (`false`) text |
| `highlight` | `false` | Boolean; yellow cell background |
| `full_width` | `false` | Boolean; render a detail-card field across the full row |
| `badge` | `null` | Null for normal formatting, or [badge options](#badges) |

Without explicit widths, ordinary tables fit columns to their displayed headings and
content. Explicit widths, including weight 1, survive normalization; their total must remain finite. Width weights do not
control detail-card pair widths or grid spans; those use their section layout fields.
Markdown fields also occupy full-width rows in detail cards.

`emphasis`, `font_weight` and `italic` apply to values, not headings. Explicit
`font_weight` takes precedence over `emphasis`. Markdown also supports `*text*`, `**text**`
and `***text***` within individual values.

`cell_options` accepts `font_weight` and `italic` for a single data cell. For example,
`"cell_options": {"0": {"6": {"font_weight": "semibold"}}}` styles only the seventh value
in the first row. Omitted or `null` options inherit the column style. `normal` and `false`
reset the inherited weight and italic style. Both index levels must reference supplied
rows and columns; for cards and grids, the row index selects the data record. Other
column options, such as width, format and highlighting, remain column settings. See
[individual cell text styling](json-inputs.md#individual-cell-text-styling).

## Result tables

With `kind: "table"`, add the common section and matrix fields, plus:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `caption` | `null` | Literal or translated numbered table caption, independent of `heading` |
| `style` | `default` | `default` or neutral bordered `reference` presentation |
| `show_header` | `true` | Render the declared column-header row |
| `row_options` | `{}` | Row-index keys mapped to objects with `highlight` |

Each row option has `highlight: false` by default; setting it true applies a pale-pink
background in the default table style. Reference tables retain white cell backgrounds.
The row index must exist. Pink row highlighting takes precedence over yellow
column highlighting in that row. Badges retain their own background colors. See [row highlighting](json-inputs.md#row-highlighting).

## Badges

Badges work in result tables, detail cards and grids. They do not replace or infer the cell
value. Omit `badge`, or use null, for ordinary formatting. `badge: {}` enables a badge using
the selected theme's heading color.

| Badge field | Default | Accepted value and effect |
| --- | --- | --- |
| `preset` | `null` | `tier1`, `tier2`, `tier3`, `tier4`, or null |
| `color` | `null` | Six-digit hexadecimal background color or null |
| `values` | `{}` | Display-text keys mapped to tier names or style objects |

| Tier preset | Background |
| --- | --- |
| `tier1` | `#af6246` |
| `tier2` | `#ae8540` |
| `tier3` | `#4f7d9f` |
| `tier4` | `#4b8b76` |

Use either a preset or custom color. A nonempty `values` map cannot be combined with a
whole-column preset or color. Each map entry accepts a tier-name string or an object with
`preset` or `color`; `{}` selects the theme default. Nested value maps are not supported.
Unlisted values retain the column's normal formatting. Keys match the displayed text in
the selected language, including formatted booleans. Blank and null values are not badged.

Foreground is selected automatically as black or white. Badges use semibold text, preserve
literal labels even in Markdown columns, and wrap within narrow cells. There are no
custom foreground, badge font, icon or shape settings. See [badge examples](json-inputs.md#optional-badges).

## Compact tables

Use `kind: "compact_table"` with the common section fields and:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `caption` | `null` | Literal or translated numbered caption, independent of `heading` |
| `items` | Required | Ordered cell-value list; gene symbols or haplotype labels, for example |
| `columns` | `null` | Integer 1–64 or null for automatic column count |
| `format` | `plain` | `plain` or inline `markdown` |
| `empty_text` | `No reportable results` | Text; used when no visible items remain |

Automatic layout measures the longest item in the bundled font, including padding and
borders, and uses that width for every cell. The available paper width determines the
column count. An explicit count is an upper limit; fewer columns are used if needed.
Null, empty and whitespace-only items are omitted. Order and repeated values are preserved;
the final row has no filler cells. Browser matrices reflow within their available width
without a horizontal scrollbar, preserving equal-width bordered cells.

For multi-row compact matrices, the measured longest item sets the minimum cell width.
The renderer fits as many equal-width columns as possible and divides the remaining
usable width evenly across them. Single-row lists retain their compact natural width.


Items remain on one line. An item too wide for the page raises `ReportInputError`;
characters must be supported by the bundled font. Markdown allows inline bold, italic and
code, but block elements are rejected. The caption uses normal-size bold text. Cell text
is 2.5 points smaller than normal body text, with minimal internal padding and shared borders.
Compact tables have no `column_options`, row highlights or badge settings.

## Record headings

Detail cards and grouped grids add:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `record_heading` | `null` | Text or null; a positional format such as `{0} - {1}` |
| `record_titles` | `null` | List of text values, one per data row, or null |

Explicit `record_titles` take precedence over `record_heading`. Without either, the first
cell supplies the heading. Heading formats allow positional column references only;
attribute access, conversions and format specifications are rejected. Use `{{` and `}}`
for literal braces.

## Detail cards

Use `kind: "details"` with section, matrix and record-heading fields, plus:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `fields_per_row` | `3` | Integer 1–6 label/value pairs per compact row |
| `full_width_last` | `false` | Boolean; place full-width/Markdown fields after compact fields |

A column with `full_width: true` or Markdown format occupies a separate full-width row.
Otherwise fields retain column order, grouped by `fields_per_row`. See
[detail examples](json-inputs.md#detailed-findings).

## Grouped grids

Use `kind: "grid"` with section, matrix and record-heading fields, plus:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `grid_columns` | `5` | Integer 1–24 logical grid units |
| `layout` | Required | Nonempty list of grid-row objects |

Each grid row contains:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `cells` | Required | Nonempty list of grid-cell objects |
| `hide_if_empty` | `false` | Hide the row when every referenced value is null or empty |

Each grid cell contains:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `column` | Required | Integer index, at least 0 and below the data column count |
| `mode` | `pair` | `pair`, `inline`, `value`, or `label` |
| `span` | `2` | Positive integer; total width of this cell in grid units |
| `label_span` | `1` | Positive integer; label width in `pair` mode; must be less than `span` |
| `label` | `null` | Text or null; overrides the column's label |

Cell spans in each layout row must sum to `grid_columns` exactly. A pair renders separate
label and value cells. Inline mode renders a bold label and value together; value mode
omits the label; label mode shows only the label. `label_span` is ignored outside pair mode.
Zero and false count as visible for empty-row suppression. See
[grid examples](json-inputs.md#grouped-detail-grids).

## Image fields

Standalone `kind: "image"` sections and entries in any section's `images` list use:

| Field | Default | Accepted value and effect |
| --- | --- | --- |
| `source` | Required | Image reference |
| `caption` | `""` | Text; optional caption below the image |
| `alt` | `""` | Text; falls back to the caption when empty |
| `frame` | `0` | Integer at least 0; selected image frame or TIFF page |
| `width_percent` | `100` | Number greater than 0 and at most 100 |
| `max_height_mm` | `null` | Positive number or null; an additional image-height cap |

Standalone image sections also require `key` and `kind: "image"` and accept the common
section fields. Attached images do not take section keys or kinds. Their order follows
`images`. To put a CNV plot before detailed findings, insert a standalone image section at
that position rather than attaching it after the finding section.

Plot formats are controlled by `presentation.accepted_image_formats`. Frame indexes must
exist in the source file; SVG accepts only frame 0. Image height is capped by the available page height after the
header, applicable footer and a 20 mm allowance; `max_height_mm` can reduce that cap.
Local artwork is embedded by the loader, so exported JSON and HTML remain portable.

Self-contained SVG may include validated metadata, static CSS and embedded WOFF2 fonts.
Scripts, event handlers, external resources, unsafe CSS and malformed fonts are rejected.
See [SVG compatibility](branding.md#self-contained-svg).

## Theme registration

Built-in themes are `generic`, `coyote3`, `genexus`, `cll_genie` and `pgx`.
Their colors are listed below; all values are six-digit hexadecimal strings.

| Theme | Heading | Accent | Tint | Rule end |
| --- | --- | --- | --- | --- |
| `generic` | `#435365` | `#64748B` | `#f3f5f7` | `#aab4c0` |
| `coyote3` | `#665271` | `#a58ab8` | `#f4eff8` | `#d9b18a` |
| `genexus` | `#3c6585` | `#3c6585` | `#f0f6fb` | `#91b5cd` |
| `cll_genie` | `#7B4925` | `#DF7849` | `#FFF8F5` | `#dca37b` |
| `pgx` | `#176B68` | `#278780` | `#edf7f5` | `#9dcac0` |

For a custom theme, create `Theme(...)` and register it on the renderer:

| Theme field | Default | Accepted value and effect |
| --- | --- | --- |
| `name` | Required | Unique registry key |
| `heading` | Required | Section-heading, product-name and default badge color |
| `accent` | Required | Start color of the header separator |
| `tint` | Required | Table and metadata background tint |
| `rule_end` | Required | End color of the header separator |
| `body_pt` | `9.25` | Number, 8–12 points |
| `wordmark_size_pt` | `15` | Number, 8–24 points |
| `wordmark_weight` | `600` | `400` or `600` |
| `wordmark_spacing_px` | `2.4` | Number, 0–5 CSS pixels |
| `wordmark_suffix_color` | `#c47b4c` | Suffix color |

Coyote3's built-in wordmark overrides size to 16.5 pt, weight to 400 and spacing to 1.5 px.
The other built-in themes use the table's typography defaults. Body and wordmark settings
are theme properties, not report JSON fields. JSON `theme` selects a registered name;
inline theme objects are not supported. Existing names cannot be replaced by registration.

```python
from smd_reports import ReportLoader, ReportRenderer, Theme

renderer = ReportRenderer()
renderer.register_theme(
    Theme(
        name="example",
        heading="#176B68",
        accent="#278780",
        tint="#edf7f5",
        rule_end="#9dcac0",
        body_pt=9.25,
        wordmark_size_pt=15,
        wordmark_weight=600,
        wordmark_spacing_px=2.4,
        wordmark_suffix_color="#c47b4c",
    )
)
report = ReportLoader().load("report.json")  # JSON may select "theme": "example".
html = renderer.render_html(report)
```

The bundled font family is Source Sans 3. Arbitrary font families, CSS snippets and template
paths are not JSON options. Shared table rules, description spacing, summary colors and
page-number placement belong to the common layout, rather than per-application switches.

## Shared appearance

These are shared styling defaults, not additional JSON fields:

| Component | Shared style |
| --- | --- |
| Summary box | Background `#fff9e8`, darker left border `#bda15b` at 3 CSS pixels, black text |
| Column highlight | Yellow `#ffffe0` |
| Row highlight | Pale pink `#ffe6e6`; takes precedence over column highlighting |
| Compact cells | Body size minus 2.5 pt; 0.5 px vertical and 2 px horizontal internal padding; touching cell borders |
| Compact caption | Normal body size, semibold, black |
| Badge | Compact rounded rectangle; semibold text and automatic black/white foreground |
| Description content | Reduced spacing around Markdown subheadings and paragraphs |

The theme controls the documented design tokens. Other per-cell padding, arbitrary CSS,
font-family choices, custom summary colors and alternative page-number positions are not
configuration fields.

## Python methods and runtime options

| Method | Options |
| --- | --- |
| `ReportLoader.load(path)` | JSON file path; image paths resolve against its parent |
| `ReportLoader.loads(source, *, base_dir=None)` | JSON text or bytes; optional base directory for relative artwork paths |
| `ReportLoader.schema(application=None, *, preset=None)` | General schema by default; optional legacy selector constraint or required `preset`; choose one |
| `ReportRenderer.register_theme(theme)` | Register a validated `Theme` under a new name on this renderer |
| `ReportRenderer.render_html(report, *, theme=None)` | Optional registry-name override; returns standalone HTML |
| `ReportRenderer.render_pdf(report, *, theme=None)` | Same override; returns PDF bytes; requires the PDF extra and native libraries |
| `report.model_dump_json(indent=2)` | Export the validated, portable JSON document |

`loads()` uses the current directory for relative paths when `base_dir` is omitted.
Neither renderer writes files automatically. Configure normal Python logging on
`smd_reports`; the package does not configure the root logger. See
[logging and errors](python-api.md#handle-errors) for the public exception types and
`format_validation_error(...)` helper.

## Command-line options

Both `smd-reports` and `python -m smd_reports` support the same commands:

| Command | Positional input | Options |
| --- | --- | --- |
| `validate` | JSON path, required | No output option |
| `normalize` | JSON path, required | `--output PATH`, required |
| `render` | JSON path, required | `--format html` or `--format pdf`, required; `--output PATH`, required |
| `schema` | None | `--output PATH`, required; optional `--preset NAME` or legacy `--application NAME`, mutually exclusive |

`--preset` and `--application` accept the five built-in preset names. Global `--verbose`
must appear before the command and sends package events to stderr. `-h`/`--help` is
available for the main command and each subcommand. A render command has no separate
`--theme` flag: put the selection in JSON or use the Python renderer override.

Output directories must exist; output cannot overwrite the input file. Exit status is
0 for success, 2 for input/setup/output errors and 1 for rendering failures. Existing output
is replaced only after the new content has been written successfully. See [CLI examples](cli.md).

## Inspect the installed format

```sh
smd-reports schema --output report.schema.json
smd-reports schema --preset coyote3 --output coyote3.schema.json
```

The schema describes field types, optional values, enums and numeric bounds. Cross-field
rules such as row lengths, grid span totals and available page space are also checked by
the loader. Schema export needs no report data or PDF runtime. Inspect
`report.preset_name`, `report.theme_name`, `report.resolved_layout`, `report.template_name`
and `report.template_version` for resolved settings and installed revisions.

## Explicit table captions and reference tables

Both `table` and `compact_table` accept `caption` as literal text or an `en`/`sv`
translation object. Captions render exactly as supplied; numbers are never generated or
changed. The shared black, semibold caption uses the report body size and spans the
available width, including above narrow gene matrices. A figure/figcaption wrapper and
`aria-labelledby` associate each nonempty table with its caption. Empty tables retain
the caption and their empty-state message. Captions stay with the start of the table
where possible, while long tables can continue onto later pages.

`heading` remains an independent section heading when `caption` is supplied. Omitting
`caption` retains the legacy heading presentation, including compact-table captions.

For `table`, choose `style: "reference"` for a white background, black text and thin
neutral borders around every cell and the perimeter. Text is 1 pt smaller than the
report body, with 2px vertical/4px horizontal padding and 1.2 line height. Column weights
remain configurable through `column_options`. This style adds no colored header bands
or row decorations. Explicit text and badge options remain available.

`show_header: false` removes the header row completely. Declare columns as usual: row
lengths are still validated, and empty labels do not imply a hidden header. These
options do not change compact-table font measurement, ordering or column fitting.
