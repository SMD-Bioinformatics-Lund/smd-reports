# HTML and PDF rendering

```python
from pathlib import Path
from smd_reports import ReportLoader, ReportRenderer

report = ReportLoader().load("report.json")
renderer = ReportRenderer()
Path("report.html").write_text(renderer.render_html(report), encoding="utf-8")
Path("report.pdf").write_bytes(renderer.render_pdf(report))
```

## Portable HTML

HTML embeds CSS, print rules, Source Sans 3 fonts and artwork. Plain text is escaped and
Markdown is sanitized. Reports require no JavaScript or external assets.

Convert the HTML on another machine with:

```sh
weasyprint report.html report.pdf
```

That machine needs WeasyPrint and its native runtime, but not `smd-reports`, the source
JSON or the original image files.

## Print layout

Reports use A4 pages with repeating center branding and compact patient metadata.
Ordinary tables repeat headers across pages. Column widths follow the JSON definitions;
text wraps within each column. Finding cards and grouped grids use their JSON layout.

Text sections with `conclusion: true` use the yellow summary box and always have page
breaks before and after. Long summaries and full-width detail comments can span pages.
Set `page_break_before: true` on any other section for an additional break.

Use `presentation.header_height_mm` and `footer_height_mm` to adjust reserved print space.
Genexus repeats the report title in its header. The accreditation logo, when enabled,
appears opposite the template revision and page number.

## Language

`language: "en"` selects English interface labels and `Page X of Y` numbering;
`language: "sv"` selects Swedish labels and `Sida X av Y`. Custom labels and text can
include both translations in JSON. See [translations](json-inputs.md#translations).

## Themes

| Application | Colors |
| --- | --- |
| Coyote3 | Purple/orange |
| Genexus | Blue |
| CLL Genie | Dark orange |
| PGx | Teal |

You can register a custom theme on a renderer:

```python
from smd_reports import ReportRenderer, Theme

renderer = ReportRenderer()
renderer.register_theme(Theme(
    name="center", heading="#176B68", accent="#278780",
    tint="#edf7f5", rule_end="#9dcac0",
))
html = renderer.render_html(report, theme="center")
```

The loader records the package and template revision in `provenance`. PDF appearance can
vary with fonts, WeasyPrint and native libraries; use the same rendering environment when
comparing outputs. See [installation](installation.md) for PDF dependencies.
