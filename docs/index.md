# smd-reports

`smd-reports` builds report documents from validated application data. It provides
application-specific Python builders, shared presentation components, center branding,
self-contained HTML and optional PDF rendering.

## Choose an interface

| Starting point | Interface | Guide |
| --- | --- | --- |
| Prepared data in Python | Application builder classes | [Python usage](python-api.md) |
| Application-specific JSON | `ReportLoader` or CLI | [JSON format](json-inputs.md) |
| Normalized document snapshot | `ReportLoader` and `ReportRenderer` | [Rendering](rendering.md) |
| Shell script or batch job | `smd-reports` commands | [Command-line reference](cli.md) |

Start with [installation](installation.md), then run the [quickstart](quickstart.md).
Install the distribution as `smd-reports`; import it as `smd_reports`.

## Application support

| Application | Python builder | JSON discriminator |
| --- | --- | --- |
| Coyote3 | `CoyoteReport` | `coyote3` |
| Genexus | `GenexusReport` | `genexus` |
| CLL Genie | `CLLGenieReport` | `cll_genie` |
| PGxModule | `PGxReport` | `pgx` |

Each application has its own typed content and uses the shared layout. Coyote3,
Genexus and CLL Genie supply prepared findings and reviewed interpretation text. PGx also
provides local TSV report preparation. See [application inputs](integration.md).

## Document features

- Shared typography, metadata tables, analysis tables, conclusions and application themes.
- Center logos/contact details in headers and conditional accreditation artwork in footers.
- Swedish/English built-in labels and PDF page numbering.
- Embedded CSS, print rules, Source Sans 3 fonts and artwork in exported HTML.
- Versioned JSON inputs, schema export and snapshots with embedded logos.

Applications retain clinical decisions, approval and artifact storage. Supplied clinical
interpretations are displayed as provided, without automatic translation.
