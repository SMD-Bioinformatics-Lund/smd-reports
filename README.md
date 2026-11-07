# smd-reports

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](docs/installation.md)
[![Package version](https://img.shields.io/badge/package-0.1.0-00897B?style=flat-square)](CHANGELOG.md)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/SMD-Bioinformatics-Lund/smd-reports/actions/workflows/quality.yml)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-009688?style=flat-square&logo=materialformkdocs&logoColor=white)](docs/index.md)
[![PDF renderer](https://img.shields.io/badge/PDF-WeasyPrint_63.0-D44A3A?style=flat-square)](docs/rendering.md)
[![License](https://img.shields.io/badge/license-GPL--3.0--only-4C9A2A?style=flat-square)](LICENSE)

Python report builders for Coyote3, Genexus, CLL Genie and PGxModule, with shared layouts,
application themes, center branding and Swedish/English interface labels.

Build reports from Python objects or application-specific JSON. HTML includes its CSS,
print rules, fonts and artwork, so it can be converted elsewhere with WeasyPrint.

## Install

Requires Python 3.10 or newer. Install with pip:

```sh
python -m pip install smd-reports
# Include the optional PDF renderer:
python -m pip install "smd-reports[pdf]"
```

The distribution name is `smd-reports`; the Python import name is `smd_reports`.
PDF rendering also requires native Pango libraries. See [installation](docs/installation.md).

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

Applications can also instantiate `CoyoteReport`, `GenexusReport`, `CLLGenieReport` or
`PGxReport` directly, without an intermediate JSON file. The
[Python guide](docs/python-api.md) and [quickstart](docs/quickstart.md) include examples.

## Use from the command line

```sh
smd-reports validate report.json
smd-reports render report.json --format html --output report.html
smd-reports render report.json --format pdf --output report.pdf
smd-reports normalize report.json --output report.snapshot.json
smd-reports schema --application coyote3 --output coyote3.schema.json
```

The same commands are available with `python -m smd_reports`.

## Documentation

- [Overview](docs/index.md), [installation](docs/installation.md) and [quickstart](docs/quickstart.md)
- [Python usage](docs/python-api.md) and [Python API reference](docs/reference.md)
- [Application inputs](docs/integration.md), [JSON format](docs/json-inputs.md)
  and [Command-line reference](docs/cli.md)
- [Center branding](docs/branding.md) and [HTML/PDF rendering](docs/rendering.md)
- [Contributing](docs/contributing.md), [testing and releases](docs/validation.md)
  and [changelog](CHANGELOG.md)

Runnable synthetic examples are in [examples/](examples/). Application workflows retain
clinical decisions, authorization, approval and storage; see the application guide for
the PGx preparation boundary.

## Example reports

| Application | HTML | PDF | Input |
| --- | --- | --- | --- |
| Coyote3 | [HTML](examples/rendered/coyote3.html) | [PDF](examples/rendered/coyote3.pdf) | [JSON](examples/inputs/coyote3-dna.json) |
| Genexus | [HTML](examples/rendered/genexus.html) | [PDF](examples/rendered/genexus.pdf) | [JSON](examples/inputs/genexus-en.json) |
| CLL Genie | [HTML](examples/rendered/cll-genie.html) | [PDF](examples/rendered/cll-genie.pdf) | [JSON](examples/inputs/cll-genie-positive.json) |
| PGxModule | [HTML](examples/rendered/pgx.html) | [PDF](examples/rendered/pgx.pdf) | [JSON](examples/inputs/pgx.json) |

These reports use synthetic clinical data and generic application, center and accreditation
placeholders. Production reports use the artwork supplied through JSON.
Download HTML files and open them locally; CSS, fonts and artwork are embedded. PDFs can
be previewed directly in GitHub.

## License

[GPL-3.0-only](LICENSE). Embedded Source Sans 3 fonts use the
[SIL Open Font License](src/smd_reports/static/SourceSans3-LICENSE.md).
