# Contributing

## Development setup

From a source checkout, create an environment and install the development tools:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,test,docs,pdf]'
python -m pre_commit install
python -m pre_commit run --all-files
```

PDF tests require the native libraries listed in [installation](installation.md).
Pre-commit runs Ruff linting and formatting, checks JSON/YAML/TOML, and checks whitespace
and merge conflict markers. CI runs the same hooks. Ruff uses a 100-character line limit
and Google-style docstrings; EditorConfig supplies matching editor defaults.

Document public classes and functions with a concise description and relevant `Args`,
`Returns` and `Raises` sections. Keep package authorship and contact information in
`pyproject.toml`; source files need module docstrings rather than repeated metadata headers.

## Tests and documentation

```sh
python -m pytest -q --cov=smd_reports --cov-branch --cov-report=term-missing --cov-report=html
python -m mkdocs build --strict
```

The coverage minimum is 75%, including branches. Add tests for observable behavior and
failure cases; see [testing and releases](validation.md) for distribution checks.
Use `python -m mkdocs serve` to preview documentation locally.

## Example reports

JSON files in `examples/inputs/` are the source for the report examples. Regenerate the
five versioned HTML/PDF previews after changing report appearance:

```sh
python examples/reports.py --previews --pdf --output examples/rendered
```

Review the PDFs and keep their data and artwork synthetic. Other generated output belongs
under `.artifacts/`.

## Pull requests

Create feature or bugfix branches from `dev` and open development PRs against `dev`.
Include the behavior change and relevant test results. Development PRs use squash merges.
Release PRs go from `dev` to `master` and use merge commits to preserve branch ancestry.
The PR templates in `.github/PULL_REQUEST_TEMPLATE/` describe the expected checks.

See [publishing setup](publishing.md) for release configuration and commands.
