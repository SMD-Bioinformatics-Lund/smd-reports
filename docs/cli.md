# Command-line reference

Install the package to get `smd-reports`. All commands are also available as
`python -m smd_reports`. Run `smd-reports --help` for command help.

## Validate

```sh
smd-reports validate report.json
```

Checks the application contract, selected analyses and referenced artwork, then builds the
document. No output artifact is written. Application JSON and normalized snapshots are accepted.

## Render

```sh
smd-reports render report.json --format html --output report.html
smd-reports render report.json --format pdf --output report.pdf
```

`--format` and `--output` are required. HTML includes CSS, fonts, print rules and artwork.
PDF rendering requires the `pdf` extra and native runtime. The output parent directory must
already exist. The input JSON cannot also be the output path; an existing separate output
file is overwritten.

## Normalize

```sh
smd-reports normalize report.json --output report.snapshot.json
```

Saves the built `Report` with embedded artwork. The snapshot is a document format rather
than another application input envelope. It can be validated or rendered using the same
commands without the original logo files.

## Export JSON Schema

```sh
smd-reports schema --application coyote3 --output coyote3.schema.json
```

Application choices are `coyote3`, `genexus`, `cll_genie` and `pgx`. Schema export does not
read report data or require WeasyPrint. The loader applies additional cross-field and
artwork checks beyond the structural JSON Schema.

## Exit status and errors

| Status | Meaning |
| --- | --- |
| 0 | Command succeeded |
| 2 | Argument, input validation, filesystem or renderer dependency error |

Validation messages identify field locations/types without printing clinical values.
Artwork loading errors identify the branding field. Check input paths and permissions,
the [JSON format](json-inputs.md) and [PDF dependencies](installation.md) when a command fails.
