# Command-line reference

Install with `pip install smd-reports`. Commands are available as `smd-reports` and
`python -m smd_reports`.

```sh
smd-reports validate report.json
smd-reports render report.json --format html --output report.html
smd-reports render report.json --format pdf --output report.pdf
smd-reports normalize report.json --output report.portable.json
smd-reports schema --output report.schema.json
```

`validate` checks JSON and artwork. `render` writes HTML or PDF. `normalize` writes the
same JSON format with embedded images and renderer versions. `schema` exports JSON Schema;
optionally add `--application generic`, `coyote3`, `genexus`, `cll_genie` or `pgx` to restrict the identity.

`--output` is required for commands that write a file. An output path cannot overwrite
the input JSON. Parent directories must already exist. Invalid JSON, assets or output
locations return exit status 2; success returns 0. PDF generation needs the PDF extra and
native dependencies described in [installation](installation.md).
