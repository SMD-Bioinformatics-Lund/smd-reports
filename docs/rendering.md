# HTML and PDF rendering

```python
from pathlib import Path
from smd_reports import ReportLoader, ReportRenderer

report = ReportLoader().load("report.json")
renderer = ReportRenderer()
Path("report.html").write_text(renderer.render_html(report), encoding="utf-8")
Path("report.pdf").write_bytes(renderer.render_pdf(report))
```

![JSON input to HTML and PDF report workflow](assets/report-workflow.svg)

## Portable HTML

HTML embeds CSS, print rules, Source Sans 3 fonts and artwork. Plain text is escaped and
Markdown is sanitized. Reports require no JavaScript or external assets.

Convert the HTML on another machine with:

```sh
weasyprint --custom-metadata report.html report.pdf
```

That machine needs WeasyPrint and its native runtime, but not `smd-reports`, the source
JSON or the original image files. `--custom-metadata` retains the automatically filled
rendering metadata; PDF output from `ReportRenderer` includes it by default.

## Print layout

Reports default to A4 with repeating center branding and compact report metadata.
Ordinary tables repeat headers across pages and fit columns to their headings and content.
Explicit JSON width weights select proportional widths instead. Text wraps when needed. Compact tables wrap independent items across the available
width with shared cell borders and continue across pages. Cell text stays on one line. Finding cards and grouped grids use their JSON layout.

Sections with `kind: "summary"` use the yellow summary box and always have page
breaks before and after. Long summaries and full-width detail comments can span pages.
Set `page_break_before: true` on any other section for an additional break.

Use `presentation.header_height_mm` and `footer_height_mm` to adjust reserved print space.
Genexus repeats the report title in its header. The accreditation logo, when enabled,
appears opposite the template and package versions and page number.

## Page size

Choose a preset through `presentation.page_size`: A0–A6, B0–B6, Letter, Legal, Tabloid or
Executive. A4 is the default. `orientation` optionally selects `portrait` or `landscape`.

```json
{
  "presentation": {
    "page_size": "A3",
    "orientation": "landscape",
    "header_height_mm": 65,
    "footer_height_mm": 38
  }
}
```

For a custom size, supply both dimensions:

```json
{
  "presentation": {
    "page_size": "custom",
    "custom_width_mm": 320,
    "custom_height_mm": 200
  }
}
```

Without an explicit orientation, custom width and height are used exactly as supplied.
An explicit orientation orders the shorter/longer dimensions accordingly. Page dimensions
must leave room for headers, footers and content. Print rules and the HTML preview width
use the selected dimensions; PDF media boxes use the same size.

## Language

`language: "en"` selects English interface labels and `Page X of Y` numbering;
`language: "sv"` selects Swedish labels and `Sida X av Y`. Custom labels and text can
include both translations in JSON. See [translations](json-inputs.md#translations).

## Themes

| Theme key | Colors |
| --- | --- |
| `generic` (default) | Slate |
| `coyote3`, `coyote4` | Purple/orange |
| `genexus` | Blue |
| `cll_genie` | Dark orange |
| `pgx` | Teal |

Set `theme` in JSON to select colors independently of the preset and layout. Precedence
is the renderer's `theme=` argument, then JSON `theme`, then the selected preset's theme.
JSON accepts a registered name or an [inline palette](configuration.md#theme-registration).
The selected theme name and optional revision are recorded in the HTML metadata.

Themes set analysis heading colors, table tints and header rules. Patient and report
information use a fixed gray heading and label cells with white value cells. Wordmark typography
uses `wordmark_size_pt`, `wordmark_weight`, `wordmark_spacing_px` and
`wordmark_suffix_color`. Shared summary-box styling is independent of theme colors.

You can register a custom theme on a renderer:

```python
from smd_reports import ReportRenderer, Theme

renderer = ReportRenderer()
renderer.register_theme(
    Theme(
        name="center",
        heading="#176B68",
        accent="#278780",
        tint="#edf7f5",
        rule_end="#9dcac0",
    )
)
html = renderer.render_html(report, theme="center")
```

The package records its version automatically in HTML metadata. PDF appearance can
vary with fonts, WeasyPrint and native libraries; use the same rendering environment when
comparing outputs. See [installation](installation.md) for PDF dependencies.

## Template and package versions

Each report footer shows its name and the installed package version. When JSON includes
`provenance.application_version`, the footer also shows that value next to the report name.
For example, `"application_version": "3.1.2"` produces
`Coyote3 DNA v3.1.2 | smd-reports v0.6.0`. Numeric versions get a leading `v`.
The package version identifies the shared template, preset defaults and built-in palettes.

For custom palettes, set a theme name and an optional `revision`. The renderer records
them in the HTML metadata as `smd-reports:theme` and `smd-reports:theme_revision`.
The same values are included in PDFs generated by the package.

## Embedded screen and print styling

Standalone HTML embeds shared print-compatible CSS and a separate `media="screen"`
stylesheet for browser effects and responsive layouts. PDF converters skip browser-only
properties. Description and reference-table font sizes are computed by the renderer and
emitted as point values. Generated caption and finding IDs avoid collisions with supplied
section keys; section IDs retain their application-supplied values.
