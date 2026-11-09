# Testing and releases

## Local checks

```sh
python -m pre_commit run --all-files
python -m pytest -n 2 -q --durations=10 --cov=smd_reports --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=html
python -m mkdocs build --strict
python -m build
python -m twine check --strict dist/*
python scripts/check_installation.py
```

Tests cover JSON validation, scalar type preservation, dynamic column and grid layouts,
localization, image loading, sanitized Markdown, standalone HTML, PDF content and pagination,
and command-line behavior. SVG regressions cover static CSS, editor metadata, embedded
WOFF2 fonts, encoded resource references, malformed fonts and vector PDF output. Coverage measures the entire package, including branches, with
an enforced 75% minimum. HTML and XML reports are written to `.artifacts/coverage/`.

CI runs core checks on Python 3.10, 3.12 and 3.14, and PDF checks on Python 3.12 with
WeasyPrint 70.0. It also runs pre-commit, builds documentation and distributions, and checks
fresh wheel/source installations.

An optional regression reads external SVG artwork without copying it into the repository:

```sh
SMD_REPORTS_REFERENCE_SVG=/path/to/accreditation.svg python -m pytest tests/test_svg.py -q
```

This checks JSON loading, unchanged embedded artwork, HTML and real vector PDF output.
The regular tests use synthetic artwork and bundled fonts, with no institutional marks.

Use `-n 2` for two test workers, or omit it when debugging a single process. The
`--durations=10` summary identifies slow setup and test calls. Example inputs are loaded
once per worker; each test receives an independent copy. PDF generation and comparisons
still execute for each test.

## Report previews

```sh
python examples/reports.py --previews --pdf --output examples/rendered
python scripts/visual_review.py examples/rendered
```

These commands regenerate the five example reports, render PDF pages as images,
and record page sizes, image hashes and rendering versions under `.artifacts/`.
Use `--baseline PATH` to compare with an existing capture. Inspect wrapping, page breaks,
headers and footers when a rendering change affects the previews.

## Release preparation

Feature PRs target `dev`. Release PRs promote `dev` to `master` with a merge commit.
Update the package version and changelog, run checks and review the generated examples.
The package version is defined once in `src/smd_reports/__init__.py`.

Release PRs into `master` must increase the version beyond the exact PR base version and
any release tags already reachable from that base. Versions use Python packaging ordering,
so `0.1.10` is newer than `0.1.9`. Ordinary PRs into `dev` do not require a version increase.
These checks run inside the required `branch-flow` job; the maintainer review exception
does not bypass them.

`CHANGELOG.md` must contain exactly one entry matching the package version, with a heading
such as `## 0.1.1` or `## [0.1.1] - 2026-11-08`. Include release changes beneath that heading.
Empty sections, placeholder-only notes, comments and code examples do not count as release
notes. Keep work in progress under `## Unreleased` until preparing a release.

Before opening a release PR, check the candidate locally:

```sh
python scripts/check_release.py --base-ref origin/master
```

Publishing repeats changelog validation and checks the version against previous release
tags on `master`, excluding the candidate's own tag. The first release is allowed when no
previous package version or release tags exist.

The publishing workflow is manual. Pushing a branch, merging a PR or adding a tag does
not publish a distribution. See [publishing setup](publishing.md) for account configuration
and release commands.
