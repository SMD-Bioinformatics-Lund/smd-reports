# Testing and releases

## Local checks

```sh
python -m pytest -q
python -m ruff check src examples tests scripts
python -m ruff format --check src examples tests scripts
python -m mkdocs build --strict
python -m build
python -m twine check --strict dist/*
python scripts/wheel_smoke.py
```

Tests cover JSON validation, matrix row lengths, configurable columns, translations,
grouped grids, image loading, escaped text, Markdown, standalone HTML and PDF pagination.
CI checks core functionality on Python 3.10, 3.12 and 3.14; PDF checks use Python 3.12 and
WeasyPrint 63.0.

## Report previews

```sh
python examples/reports.py --previews --pdf --output examples/rendered
python scripts/visual_review.py examples/rendered
```

The first command regenerates the four public example pairs. The second rasterizes PDFs
and records page sizes, image hashes and rendering versions under `.artifacts/`.
Use `--baseline PATH` to compare with an existing capture.

## Release preparation

Feature PRs target `dev`. Release PRs promote `dev` to `master` with a merge commit.
Update the package version and changelog, run checks and review the generated examples.
The package version is defined once in `src/smd_reports/__init__.py`.

The publishing workflow is manual. Pushing a branch, merging a PR or adding a tag does
not publish a distribution. See [publishing setup](publishing.md) for the one-time account
configuration and later release commands.
