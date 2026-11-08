# Branches and pull requests

The development flow is:

```text
feat/... or fix/...  ->  dev  ->  master
     development PR      release PR
```

`master` contains released code. `dev` stages reviewed changes for the next release.
Create feature or bugfix branches from `dev`. Do not develop directly on `dev` or `master`.

## Development environment

From a source checkout:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[pdf,test,docs]'
python -m pytest -q
python -m ruff check src examples tests scripts
python -m ruff format --check src examples tests scripts
python -m build
```

PDF checks also require the native libraries described in [installation](installation.md).
Run `python examples/reports.py --pdf` to generate synthetic HTML/JSON/PDF artifacts in
`.artifacts/examples/`. The example JSON files are the source inputs.

The four curated HTML/PDF pairs in `examples/rendered/` are intentionally versioned so
users can inspect report output without installing the package. Regenerate them with:

```sh
python examples/reports.py --previews --pdf --output examples/rendered
```

Review the resulting documents before committing them. Other scratch output belongs in
`.artifacts/`; implementation work logs and local workspace metadata are not versioned.

## Documentation

```sh
python -m mkdocs serve
python -m mkdocs build --strict
```

Documentation uses MkDocs Material. The `docs` extra installs the documentation tools;
building documentation does not publish it. Add new pages to the navigation in `mkdocs.yml`.

## Development PR

Commit the changes on the work branch and run the relevant verification in
[validation and releases](validation.md). Open a PR targeting `dev` using the
development template at `.github/PULL_REQUEST_TEMPLATE/development.md`. Include
a description of the change and its test results.

After review and required checks, squash-merge the work branch into `dev`.
Create subsequent work branches from the updated `dev`.

## Release PR

Prepare the release version, template revisions, changelog and validation evidence
on a work branch and merge them into `dev` through the normal development review.
When the release candidate is ready, open a PR from `dev` to `master` using the
release template at `.github/PULL_REQUEST_TEMPLATE/release.md`.

Merge release PRs with a merge commit so the ancestry of the long-lived branches is
preserved. Do not squash or rebase the `dev` to `master` release PR. Tagging, publishing
release artifacts and upgrading applications are separate reviewed release actions.

## GitHub configuration

The `PR target` workflow checks that release PRs to `master` originate from this repository's
`dev` branch. It also rejects normal `master` to `dev` development PRs.
The `Quality` workflow verifies the package and uploads distribution/report candidates.

Keep `master` as the GitHub default branch. Once the workflows are published, repository
administrators should require PR review plus the `branch-flow`, core
matrix and PDF checks on both long-lived branches. Enable squash merging for development
PRs and merge commits for releases. These repository settings are not enforced by local
branch creation or by a workflow alone.

Development branches are merged into `dev` only after review; releases promote the
reviewed staging changes from `dev` into `master`.
