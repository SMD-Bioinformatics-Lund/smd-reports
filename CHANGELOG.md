# Changelog

## 0.5.0

- Limit Quality to protected-branch PRs, cancel superseded runs and build distributions once per PR.
- Reuse verified release-PR validation during publication instead of rerunning the test suite.
- Add shared explicit table captions and a compact bordered reference-table presentation.
- Allow regular table headers to be hidden through JSON without changing row validation.
- Justify description prose through the reusable `justified-text` style.
- Fit compact gene matrices with equal-width cells based on the longest item and page width.

## 0.4.1

- Make all automatic metadata captions configurable with literal or translated labels in HTML and PDF headers.
- Preserve the default English and Swedish captions when no override is supplied.

## 0.4.0

- Remove extra outer paragraph spacing from Markdown cells in tables and finding cards.
- Add individual-cell font weights and italic styles to result tables, detail cards and grids.
- Bundle matching bold, semibold italic and bold italic fonts for standalone HTML and PDF.
- Show Tier I and Tier II rows with individual typography and preset badge colors.

## 0.3.0 - 2026-11-10

- Select themes, layouts, product branding and metadata labels independently of presets.
- Add optional tier, custom-color and theme-colored badges to result tables and finding cards.
- Fit result-table columns to their content, preserve explicit widths and correct highlighting.
- Refine compact gene tables, description spacing and colored header separators.
- Use English source labels with Swedish translations and localized center information.
- Add a complete configuration reference and updated synthetic HTML/PDF examples.

## 0.2.1 - 2026-11-09

- Keep browser width queries out of print stylesheet parsing.
- Include HarfBuzz-Subset in native PDF installation instructions and CI.

## 0.2.0 - 2026-11-09

- Add compact description tables with fitted columns, continuous rows and smaller single-line text.
- Add row highlighting to result tables through indexed JSON display options.
- Update gene and haplotype examples to use compact tables.
- Use a transparent SVG logo with outlined lettering for light and dark backgrounds.

## 0.1.2 - 2026-11-09

- Run CI tests with two workers and reuse example setup with isolated copies per test.
- Set template revisions to the package release in which each template last changed.
- Fit accreditation logos within the footer while preserving their aspect ratio.
- Exclude hidden logos from document font definitions and accept inert SVG metadata values.
- Update dependencies and development tools, including the pinned WeasyPrint 70.0 renderer.
- Configure Dependabot for private alerts with automatic update pull requests disabled.
- Accept self-contained SVG styles, editor metadata and validated embedded WOFF2 fonts.
- Preserve original SVG artwork and expose its embedded fonts for standalone HTML/PDF conversion.
- Reject unsafe CSS, encoded external references, malformed fonts and XML processing instructions.

## 0.1.1 - 2026-11-09

- Enforce version increases and nonempty changelog entries for release PRs and publishing.
- Use Read the Docs for documentation links and version-aware canonical URLs.
- Keep wiki generation and YAML checks compatible with versioned documentation builds.

## 0.1.0

First release.

- Validated JSON input with translated column lists, configurable tables, detail cards,
  grouped grids and image sections.
- Standalone HTML with embedded CSS, fonts and artwork; optional WeasyPrint PDF rendering.
- Neutral default theme and four branded presets, with configurable center and accreditation logos.
- English/Swedish labels, plain text and Markdown, and summaries on separate pages.
- Preset/custom paper sizes, plot format and frame selection, and automatic renderer metadata.
- Python interface, command-line tools, JSON Schema export and complete HTML/PDF examples.
- Field-specific errors and standard Python event logging, with verbose command-line output.
