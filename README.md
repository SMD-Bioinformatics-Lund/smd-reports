# smd-reports

![smd-reports logo](https://raw.githubusercontent.com/SMD-Bioinformatics-Lund/smd-reports/f809a167384ecd28b34be9cbc5efa0ca64055766/docs/assets/smd-reports-logo.svg)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Installation)
[![Package version](https://img.shields.io/badge/package-0.1.0-00897B?style=flat-square)](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/CHANGELOG.md)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/SMD-Bioinformatics-Lund/smd-reports/actions/workflows/quality.yml)
[![Documentation](https://img.shields.io/badge/docs-wiki-009688?style=flat-square&logoColor=white)](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Home)
[![PDF renderer](https://img.shields.io/badge/PDF-WeasyPrint_63.0-D44A3A?style=flat-square)](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/HTML-and-PDF)
[![License](https://img.shields.io/badge/license-GPL--3.0--only-4C9A2A?style=flat-square)](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/LICENSE)

Render JSON reports as standalone HTML and PDF with shared layouts, configurable branding
and Swedish/English labels. Use a neutral default theme or choose a built-in preset.

Build reports from JSON. Define columns once and supply values as row lists. HTML includes its CSS,
print rules, fonts and artwork, so it can be converted elsewhere with WeasyPrint.
Choose preset/custom paper sizes, attach plots to sections, and format summaries,
descriptions and references as plain text or Markdown.

## Report workflow

![JSON input to HTML and PDF report workflow](https://raw.githubusercontent.com/SMD-Bioinformatics-Lund/smd-reports/7b241f357134628486e72b9f6fcaa2aafd3c8689/docs/assets/report-workflow.svg)

The [development and release workflow](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Contributing#pull-requests)
and [documentation publishing workflow](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Contributing#documentation-hosting)
are described in the contribution guide.

## Install

Requires Python 3.10 or newer. Install with pip:

```sh
python -m pip install smd-reports
# Include the optional PDF renderer:
python -m pip install "smd-reports[pdf]"
```

The distribution name is `smd-reports`; the Python import name is `smd_reports`.
PDF rendering also requires native Pango libraries. See [installation](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Installation).

## Use from Python

```python
from pathlib import Path
from smd_reports import ReportLoader, ReportRenderer

report = ReportLoader().load("report.json")
renderer = ReportRenderer()
Path("report.html").write_text(renderer.render_html(report), encoding="utf-8")
# Requires the PDF extra:
Path("report.pdf").write_bytes(renderer.render_pdf(report))
```

Load JSON text with `ReportLoader().loads(json_text)` or files with `load(path)`.
The [Python guide](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Python-usage) and [quickstart](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Quickstart) include examples.
Custom columns and detail fields are configured in JSON, including English/Swedish labels.

## Use from the command line

```sh
smd-reports validate report.json
smd-reports render report.json --format html --output report.html
smd-reports render report.json --format pdf --output report.pdf
smd-reports normalize report.json --output report.portable.json
smd-reports schema --output report.schema.json
```

The same commands are available with `python -m smd_reports`.

## Documentation

Read the [documentation wiki](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki) for installation, Python usage, JSON inputs and rendering.

- [Overview](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Home), [installation](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Installation) and [quickstart](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Quickstart)
- [Python usage](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Python-usage) and [Python API reference](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Python-reference)
- [Report examples and presets](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Report-examples), [JSON format](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/JSON-format)
  and [Command-line reference](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Command-line)
- [Center branding](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Center-branding) and [HTML/PDF rendering](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/HTML-and-PDF)
- [Contributing](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Contributing), [testing and releases](https://github.com/SMD-Bioinformatics-Lund/smd-reports/wiki/Testing-and-releases)
  and [changelog](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/CHANGELOG.md)

Runnable synthetic examples and complete JSON inputs are in [examples/](https://github.com/SMD-Bioinformatics-Lund/smd-reports/tree/master/examples/).

## Example reports

| Preset | HTML | PDF | Input |
| --- | --- | --- | --- |
| Generic | [HTML](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/generic.html) | [PDF](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/generic.pdf) | [JSON](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/inputs/generic.json) |
| Coyote3 | [HTML](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/coyote3.html) | [PDF](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/coyote3.pdf) | [JSON](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/inputs/coyote3-dna.json) |
| Genexus | [HTML](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/genexus.html) | [PDF](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/genexus.pdf) | [JSON](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/inputs/genexus-en.json) |
| CLL Genie | [HTML](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/cll-genie.html) | [PDF](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/cll-genie.pdf) | [JSON](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/inputs/cll-genie-positive.json) |
| PGxModule | [HTML](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/pgx.html) | [PDF](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/rendered/pgx.pdf) | [JSON](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/examples/inputs/pgx.json) |

These reports use synthetic clinical data and generic application, center and accreditation
placeholders. Production reports use the artwork supplied through JSON.
Download HTML files and open them locally; CSS, fonts and artwork are embedded. PDFs can
be previewed directly in GitHub.

## License

Copyright (C) 2026 Ram Nanduri.

[GPL-3.0-only](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/LICENSE). Embedded Source Sans 3 fonts use the
[SIL Open Font License](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/src/smd_reports/static/SourceSans3-LICENSE.md).
