# Application examples

Every application uses the same [JSON format](json-inputs.md). The `application` value
selects the header identity and theme; the JSON sections define the report contents.

| Application | JSON identity | Example |
| --- | --- | --- |
| Coyote3 | `coyote3` | DNA/RNA summary tables, parameters, variant and biomarker details |
| Genexus | `genexus` | SNV/INDEL, CNV, fusion and other-finding cards |
| CLL Genie | `cll_genie` | Sequence summaries and grouped V/J/D, FR/CDR and junction details |
| PGx | `pgx` | Recommendations, variants, depth, genes and target tables |

The example JSON files contain complete synthetic reports. Modify their `columns` and
`rows` to add fields without changing the renderer.

## Coyote3

Set `analyte` to `dna` or `rna`. Use ordinary tables for summary results and analysis
parameters, `details` for finding cards, and `image` for supplied plots. An optional
`analysis` on each section lets `enabled_analyses` select related sections together.

## Genexus

Use `details` sections with `fields_per_row: 3`. Setting `full_width_last: true` batches
compact fields before classification and comment rows. The example includes mutation
hotspots, CNV ratios, fusion read support and unique molecules, plus other-finding metrics.
Add any additional field once in `columns` and append its value to each row.

## CLL Genie

The example uses a `grid` section. Its JSON layout retains the five-column sequence table:
sequence/subset/category, functionality, V/J genes with scores and identities, D-region,
FR/CDR, junction and read-count rows. Each sequence occupies one row in the data matrix;
the same layout is reused for every sequence.

For reports without sequence results, omit the sequence table or use an empty `rows` list
and the desired `empty_text`.

## PGx

Supply the report tables through JSON, including recommendations, variants, low-depth
targets and the analyzed genes/targets. These use the same configurable columns and value
matrices as the other examples.
