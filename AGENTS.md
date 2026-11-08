# Repository instructions

See [the contributing guide](docs/contributing.md) for development setup, checks and releases.

## Development

- Work on feature or bugfix branches and target `dev` with development pull requests.
- Release pull requests promote `dev` to `master`. Do not work directly on either branch.
- Merge, tag or publish only when explicitly authorized. Preserve branch protection rules.
- Keep changes focused and exclude local artifacts, credentials and workspace settings.

## Implementation

- Accept report data through JSON using `ReportLoader` and `ReportRenderer`.
- Follow the configured Ruff rules, Google-style docstrings and 100-character line limit.
- Add meaningful tests for behavior changes and failures. The coverage minimum is 75%,
  including branches.
- Use standard Python logging; exclude report values, image contents and private paths.
- Keep author, license and version metadata in their existing central locations.

## Documentation and examples

- Edit documentation in `docs/` and navigation in `mkdocs.yml`; these supply the GitHub wiki.
- Use synthetic data and generic example logos in fixtures, documentation and previews.
- Regenerate and inspect the committed HTML/PDF examples when report appearance changes.
- Store other generated output under `.artifacts/`.

## Verification

- Run the relevant tests and `python -m pre_commit run --all-files` before committing.
- For documentation changes, run `python -m mkdocs build --strict` and check wiki generation
  as described in the contributing guide.
- For packaging changes, build and check distributions and verify clean installation using
  the commands in [testing and releases](docs/validation.md).
