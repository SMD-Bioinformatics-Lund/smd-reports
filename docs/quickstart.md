# Quickstart

Install the package:

```sh
python -m pip install smd-reports
```

Save this as `report.json`:

```json
{
  "application": "coyote3",
  "analyte": "dna",
  "title": "Molecular Genetics Report",
  "language": "en",
  "report": {
    "report_id": "DEMO-001",
    "sample_id": "SYNTHETIC-001",
    "generated_at": "2026-01-01T12:00:00Z"
  },
  "sections": [
    {
      "kind": "table",
      "key": "results",
      "columns": [
        {
          "label": "Gene"
        },
        {
          "label": "HGVS"
        }
      ],
      "rows": [
        [
          "BRAF",
          "p.Val600Glu"
        ]
      ],
      "heading": "Detected variants"
    },
    {
      "kind": "summary",
      "key": "summary",
      "text": "Synthetic demonstration.",
      "heading": "Conclusion"
    }
  ]
}
```

Validate and render:

```sh
smd-reports validate report.json
smd-reports render report.json --format html --output report.html
```

Open `report.html` in a browser. For PDF:

```sh
python -m pip install "smd-reports[pdf]"
smd-reports render report.json --format pdf --output report.pdf
```

See [installation](installation.md) for native PDF dependencies,
[Python usage](python-api.md) for imports and [JSON inputs](json-inputs.md) for
additional columns, translations, logos and detailed sections.
