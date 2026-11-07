# Application inputs

Each application uses a typed data model and a corresponding report builder. All data
models include `metadata`, optional `branding` and `provenance`, and prepared report content.
JSON inputs separate those shared fields from the application's `data` payload.

## Common prepared content

| Field | Meaning |
| --- | --- |
| `supported_analyses` | Analysis names supported by the assay |
| `enabled_analyses` | Supported analyses selected for this report |
| `analyses` | Prepared `Analysis` objects, including explicit empty results |
| `summary` / `summary_format` | Reviewed conclusion, plain text or sanitized Markdown |
| `description` | Supplied analysis description |
| `references` | Supplied reference text |

An enabled analysis must be supported and have prepared data. Prepared but disabled
analyses are omitted. Selection is never inferred from whether a result list is empty.
Provide parameters and typed sections through `Analysis`; see [Python usage](python-api.md).

## Coyote3

Use `CoyoteData` with `analyte="dna"` or `"rna"`, then construct `CoyoteReport(data, config)`.

Supply already selected SNV, germline SNV, CNV, fusion/translocation, biomarker or PGx
results as typed presentation sections. Preserve the application's selected sort order,
classifications, biomarker assessments and reviewed summary/description text.

Queries, filtering, classification, clinical conditional text generation, template approval
and finding snapshots remain application responsibilities. DNA and RNA template revisions
are tracked independently in the package.

## Genexus

Use `GenexusData` and `GenexusReport(data, config)`. In addition to common prepared content,
`GenexusData` accepts ordered `assay` and `run` lists of `FieldValue`. These are included
in report metadata. Supply QC results as typed sections.

Input discovery, exported-data parsing, merging, duplicate detection, assay eligibility,
finding selection and clinical narrative generation remain in the application. Both Python
and JSON interfaces consume the resulting prepared content.

## CLL Genie

Use `CLLGenieData` and `CLLGenieReport(data, config)`.

| `report_type` | Required context |
| --- | --- |
| `positive` | Reviewed `summary`, `submission_id`, at least one `CLLSequence` |
| `nonfunctional` | Reviewed `summary`; positive sequence tables must be absent |
| `no_clone` | Reviewed `summary`; positive sequence tables must be absent |

`CLLSequence` has required `sequence_id`, `mutation_status` and `productivity` strings.
Optional values include `length_nt`, `identity_percent`, `identity_nt`, `identity_with_indels`
and `subset`. Sequence identifiers must be unique. Supply detailed V/J/D gene/allele,
scores, functionality comments, indels, FR/CDR, junction and read information as ordered
`FieldValue` entries in `details`.

The application determines authoritative mutation status, productivity and subset results;
the builder does not recalculate them. Reviewed comment selection, thresholds, clinical
rules, report numbering and storage remain application responsibilities.

## PGxModule

Use `PGxData` and `PGxReport(data, config)` for prepared data. Specialized models are
imported from `smd_reports.plugins.pgx`:

| Model | Fields |
| --- | --- |
| `Recommendation` | `gene`, `haplotypes`, `text` |
| `PGxVariant` | `gene`, `rsid`, `haplotypes`, `position`, `zygosity`, `frequency_percent`, `possible_duplication` |
| `LowDepthTarget` | `rsid`, `haplotypes`, `position`, `depth` |

`PGxData` adds `recommendations`, `variants`, `low_depth_targets`, `genes`, `targets` and
`read_depth_threshold` (default 100). Variant frequency is expressed in percent.

### Prepare local TSV inputs

`PGxReport.from_files(inputs: PGxFiles, *, data: PGxData, config: ReportConfig)` reads:

| `PGxFiles` field | Required columns |
| --- | --- |
| `detected_variants` | `GENE`, `ID`, `#CHROM`, `POS`, `GT`, `AD` |
| `haplotype_definitions` | `ID`, `HAPLOTYPE` |
| `possible_diplotypes` | `gene`, `Haplotype1`, `Haplotype2`, `Guideline`, `Activity` |
| `possible_interactions` | `haplotypes`, `Guideline` |
| `missing_annotated_depth` | `ID`, `Locus`, `Total_Depth` |
| `target_rsids` | Headered five-column table; fifth column contains the gene |

Files are UTF-8 TSVs and are read without writing intermediate outputs. The preparation
pipeline computes alt/(ref+alt) frequency, omits zero-alt variants, assesses nearest
duplication/diploid fractions, applies faulty-haplotype guideline suppression and flags
targets strictly below the depth threshold. It displays DPYD and TPMT/NUDT15 recommendations.
Interaction suppression uses regex matching of faulty haplotype labels.

Upstream calling and guideline input production remain outside this package. Supplied
guidelines are not scientifically updated or translated by the renderer. Invalid depths
and multiallelic `AD` inputs fail explicitly.

## Shared integration responsibilities

Map source records to the appropriate typed models before rendering. Retain meaningful
null values, units and reviewed interpretation text. All applications own authorization,
clinical approval, external service access, report storage and retention. Report IDs and
timezone-aware timestamps are supplied by the caller.

Configure center details through [Branding](branding.md). Use the [JSON format](json-inputs.md)
for file-based integration or the [Python API reference](reference.md) for Python interfaces.
