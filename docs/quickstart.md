# Quickstart

Install the package:

```sh
python -m pip install smd-reports
```

Save this as `report.json`:

```json
{
  "title": "Example Report",
  "language": "en",
  "report": {
    "report_id": "DEMO-001",
    "generated_at": "2026-01-01T12:00:00Z"
  },
  "sections": [
    {
      "kind": "table",
      "key": "results",
      "columns": {
        "en": ["Measure", "Value"],
        "sv": ["Mått", "Värde"]
      },
      "rows": [
        [
          "Example A",
          12
        ]
      ],
      "heading": "Results"
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

Omitting `application` selects the neutral default theme. `sample_id` is optional.
Choose a [preset](integration.md) when you want a different report identity.

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
