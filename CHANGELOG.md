# Changelog

## 0.1.0

- Use generic artwork in public examples; production branding comes entirely from caller
  JSON. Application names use styled text. Shared template revisions are 1.6.0.

- Isolate yellow conclusions with print/PDF page breaks before and after across all
  applications; long conclusions may span pages.

- Show optional application logos and colored application names for Coyote3/CLL Genie;
  use center-only headers for Genexus/PGx.

- Restore the Coyote3/Genexus clinical skeleton: document heading, compact patient metadata,
  original table treatments, center/application branding and left-aligned accreditation
  artwork opposite template/page numbering.

- Add installation, quickstart, Python/CLI references, application input, branding and
  rendering guides with a MkDocs documentation site and strict documentation build in CI.

- Add versioned per-application JSON inputs, JSON Schema export, local logo resolution and
  portable normalized snapshots through `ReportLoader` and the `smd-reports` CLI.
- Localize built-in labels for Swedish/English and verify standalone WeasyPrint conversion
  of exported HTML after removing source assets.

- Add shared center logo/contact parameters, local artwork loading, restricted static SVG
  support, configurable logo dimensions and print header space.
- Use feature/bugfix PRs into `dev` and release PRs from `dev` into `master`.
- Adopt application-owned JSON as the file interface, replacing the earlier unspecified
  Genexus text-source proposal.

- Introduce shared typed report documents and class-based builders for Coyote3, Genexus,
  CLL Genie and PGxModule.
- Add a common compact layout with application themes, embedded Source Sans 3,
  sanitized Markdown, repeating PDF headers and optional offline PDF rendering.
- Add prepared-data contracts, local PGx TSV preparation, synthetic demonstrations,
  content regression checks, packaging checks and visual-review tooling.

Initial evaluation release; application integrations and clinical visual approval remain pending.
