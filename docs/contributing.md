# Contributing

## Issues

Use the [issue forms](https://github.com/SMD-Bioinformatics-Lund/smd-reports/issues/new/choose)
for bugs, feature requests, documentation, usage questions and maintenance tasks.
Select the priority, affected components and report templates. Include the package version
and a minimal example for bugs. Report vulnerabilities through the private link described
in [the security policy](https://github.com/SMD-Bioinformatics-Lund/smd-reports/blob/master/SECURITY.md).

Issues receive type, priority, component and template labels from the form. Maintainers
confirm priority, assign an owner and select a milestone when scheduling work.
The `v0.1.0` milestone tracks the first public release.

| Priority | Use |
| --- | --- |
| `priority: critical` | P0: incorrect report content or a release-blocking failure |
| `priority: high` | P1: major functionality unavailable or significantly impaired |
| `priority: normal` | P2: standard fixes and planned improvements |
| `priority: low` | P3: minor improvements with a workaround |

New and reopened issues start with `status: triage`. Maintainers move accepted work to
`status: ready`, then `status: in progress` and `status: in review`. Use `status: blocked`
when work depends on another issue or decision. Adding a priority or status label removes
the previous label in that group. Closing
an issue removes its active status; GitHub's closed state records completion.

Form edits update the selected fields without resetting priority or component labels
changed by maintainers when those form fields have not changed. Custom labels are preserved.
Labels are defined in `.github/labels.json`. The Issue management workflow synchronizes them
when that file changes on `master`; it can also be run manually.

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
Both branches require one approving review, resolved discussions and passing checks on an
up-to-date branch. These rules also apply to administrators. Force pushes and branch deletion
are blocked. Required checks are `branch-flow`, `lint`, `docs`, `core (3.10)`, `core (3.12)`,
`core (3.14)` and `pdf`. Release PRs to `master` must originate from this repository's `dev`
branch. The PR templates in `.github/PULL_REQUEST_TEMPLATE/` describe the expected checks.

See [publishing setup](publishing.md) for release configuration and commands.
