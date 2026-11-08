# Testing and releases

## Local checks

```sh
python -m pre_commit run --all-files
python -m pytest -q --cov=smd_reports --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=html
python -m mkdocs build --strict
python -m build
python -m twine check --strict dist/*
python scripts/wheel_smoke.py
```

Tests cover JSON validation, scalar type preservation, dynamic column and grid layouts,
localization, image loading, sanitized Markdown, standalone HTML, PDF content and pagination,
and command-line behavior. Coverage measures the entire package, including branches, with
an enforced 75% minimum. HTML and XML reports are written to `.artifacts/coverage/`.

CI runs core checks on Python 3.10, 3.12 and 3.14, and PDF checks on Python 3.12 with
WeasyPrint 63.0. It also runs pre-commit, builds documentation and distributions, and checks
fresh wheel/source installations.

## Report previews

```sh
python examples/reports.py --previews --pdf --output examples/rendered
python scripts/visual_review.py examples/rendered
```

The first command regenerates the five public example pairs. The second rasterizes PDFs
and records page sizes, image hashes and rendering versions under `.artifacts/`.
Use `--baseline PATH` to compare with an existing capture. Inspect wrapping, page breaks,
headers and footers when a rendering change affects the previews.

## Release preparation

Feature PRs target `dev`. Release PRs promote `dev` to `master` with a merge commit.
Update the package version and changelog, run checks and review the generated examples.
The package version is defined once in `src/smd_reports/__init__.py`.

The publishing workflow is manual. Pushing a branch, merging a PR or adding a tag does
not publish a distribution. See [publishing setup](publishing.md) for account configuration
and release commands.
