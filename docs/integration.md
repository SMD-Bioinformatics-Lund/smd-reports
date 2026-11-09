# Report examples and presets

The neutral `generic` preset is the default. Omit `application` to use it, or select a
preset explicitly. Every preset uses the same [JSON format](json-inputs.md), section
components and rendering methods. Choosing a preset changes the theme and header identity;
columns and content are supplied by the JSON document.

| Preset | Example input | Demonstrates |
| --- | --- | --- |
| `generic` | `examples/inputs/generic.json` | Neutral header, optional sample ID, translated tables and narrative |
| `coyote3` | `examples/inputs/coyote3-dna.json` | Summary tables, a separate CNV overview page and finding cards; optional DNA/RNA heading |
| `genexus` | `examples/inputs/genexus-en.json` | Compact finding fields, full-width comments and wrapping gene lists |
| `cll_genie` | `examples/inputs/cll-genie-positive.json` | Grouped detail grids with column spans and conditional empty rows |
| `pgx` | `examples/inputs/pgx.json` | Recommendations, highlighted variant rows and compact gene/haplotype tables |

Browse the [example inputs](https://github.com/SMD-Bioinformatics-Lund/smd-reports/tree/master/examples/inputs)
and [HTML/PDF previews](https://github.com/SMD-Bioinformatics-Lund/smd-reports/tree/master/examples/rendered).
All previews use synthetic values and example artwork.

The Coyote3 DNA example places the genome-wide CNV profile on a separate page after the
conclusion and before the detailed findings. The profile is an `image` section in the JSON;
page breaks before the profile and the following detail section keep it on its own page.
Omit the image section when no profile is supplied.

## Choosing section layouts

Use `table` for rows with shared column headings, `details` for repeated cards, and `grid`
for arrangements that combine fields or span columns. Define labels by language in `columns` and
append one list of values per record to `rows`. Add plots through a section's `images`
list, or use an `image` section for a standalone figure.

Use `summary` for a highlighted conclusion on its own page, and `text`, `description`
or `references` for narrative content. Each accepts plain text or sanitized Markdown.
See the [JSON guide](json-inputs.md) for complete field definitions and layout examples.

## Description tables

The Coyote3 and Genexus examples place analyzed genes in `compact_table` sections after
the analysis description. The PGx example uses the same component for genes and haplotypes,
and `row_options` for a highlighted variant row. Use ordered `items` for compact tables
and the standard column/row matrix for result tables.
