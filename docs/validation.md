# Validation and release procedure

## Test coverage

The framework targets Python 3.10+. CI runs
core contracts on Python 3.10, 3.12 and 3.14; PDF checks run on Python 3.12 with
WeasyPrint 63.0. Broader PDF/runtime compatibility is not implied by core compatibility.

Tests cover supplied clinical values, unknown/missing input handling, escaped placeholders,
sanitized Markdown, analysis selection, PGx preparation, CLL report types and offline assets.
PDF checks cover content, repeated metadata, page numbers, font embedding and long tables.
The visual check renders fixed synthetic inputs twice and compares rasterized pages for
determinism. This does not replace comparison against an independently reviewed baseline.

## Visual approval

Run examples in the pinned PDF environment. Review Coyote DNA/RNA, Genexus, PGx and CLL
positive/no-result outputs, checking typography, clinical text, empty results, table wraps,
page breaks, patient headers and footers. Include exceptionally long clinical text and the
maximum patient metadata used by the application. The A4 header area defaults to 65 mm;
use the bounded `header_height_mm` parameter for larger reviewed metadata layouts.

Use `scripts/visual_review.py OUTPUT` to rasterize generated PDFs and save their geometry,
page count, pixel hashes and font/environment versions. Keep an approved baseline artifact
outside any patient-data fixtures. Pass `--baseline BASELINE` to compare it with a candidate.
A change in page count, geometry, or pixels fails comparison. Do not update baselines solely
to pass CI: obtain layout and clinical-content review before replacing them.

The first generated artifacts are candidates, not approved baselines. The repository
does not contain a clinician-approved reference report.

## Release checklist

- Follow the [branch and PR workflow](contributing.md): development PRs to `dev`,
  then a release PR from `dev` to `master`.
- Record owner/reviewer and affected plugins; describe contract and clinical impacts.
- Update package version and changelog. Bump affected template revisions in
  `src/smd_reports/themes/versions.json`; shared layout/font changes affect every plugin,
  including both Coyote3 DNA and RNA. Bump plugin/schema revisions when their contracts change.
- Run relevant tests, the full suite, lint, package build and isolated wheel smoke checks.
- Review synthetic HTML/PDF artifacts and compare with approved baselines in the same environment.
- Record Python, WeasyPrint, font hashes, native rendering environment and verification results.
- Retain immutable wheel, source distribution, checksums and validation evidence in the
  controlled release process. Tag/publish only when separately authorized.
- Applications upgrade independently, keeping prior validated artifacts and wheels for rollback.

The package serializes its document inputs and carries generation/provenance fields.
Applications must preserve the input snapshot, reviewed configuration, templates and immutable
output with their access/retention controls. This library does not provide audit storage.

## Migration acceptance

Before replacing any production report path, compare clinical content with that application's
existing output using reviewed synthetic cases. Resolve intentional differences explicitly.
Verify approved-template governance, identity conventions, timestamp semantics, placeholder
replacement, logo requirements and artifact workflows in the application integration.

Applications perform their own adoption, release approval and deployment. Package tests
and synthetic examples do not replace validation of the application's complete workflow.
