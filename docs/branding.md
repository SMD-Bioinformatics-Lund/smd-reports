# Center branding

Every application's data model accepts `branding=Branding(...)`. JSON inputs use the
equivalent top-level `branding` object. The same configuration applies across applications.

## Load local artwork

```python
from smd_reports import Branding

branding = Branding.from_files(
    center_logo="/path/to/center.svg",
    accreditation_logo="/path/to/accreditation.svg",
    organization="Example Molecular Diagnostics Center",
    department="Molecular Diagnostics",
    address="Postal address",
    telephone="Center telephone",
    email="contact@example.org",
    website="center.example.org",
    accredited=True,
    accreditation_label="Accreditation mark",
)
```

Python paths resolve against the process's working directory. Logo paths in JSON resolve
against the JSON file's directory. Absolute paths are supported. `from_files()` reads the
files once and embeds their contents; subsequent rendering does not depend on those paths.

For embedded artwork, construct `Branding` directly with base64 data URI strings.

## Header and footer fields

| Field | Placement | Default |
| --- | --- | --- |
| `organization` | Header | Empty |
| `department`, `address`, `telephone`, `email`, `website` | Header, when supplied | Empty |
| `application_logo` | Coyote3/CLL Genie header beside application name | None |
| `center_logo` | Header beside center details | None |
| `accreditation_logo` | Footer, when `accredited` is true | None |
| `accredited` | Application-provided assay eligibility | False |
| `accreditation_label` | Artwork alternative text | `Ackreditering` |

Contact strings are escaped display text. They are not interpreted as HTML or external
resource URLs. Header information repeats on PDF pages; the HTML preview shows it once.

### Application identity

| Application | Name treatment | Optional application logo |
| --- | --- | --- |
| Coyote3 | Purple/orange application name | Shown to the left of the name |
| CLL Genie | Dark orange application name | Shown to the left of the name |
| Genexus | Center header without an application name block | Not displayed |
| PGx | Center header without an application name block | Not displayed |

For Coyote3 or CLL Genie, provide the optional logo in JSON:

```json
{
  "branding": {
    "application_logo": "logos/application.png",
    "center_logo": "logos/center.png",
    "organization": "Center name"
  }
}
```

Omit `application_logo` or set it to null to show the colored application name alone.
The name treatment is selected by `application`; it does not depend on a logo being present.
Application themes still apply to section headings and tables for all four applications.

## Artwork dimensions

| Field | Default | Range |
| --- | --- | --- |
| `center_logo_width_mm` | 11.64 | 5–35 |
| `application_logo_width_mm` | 13.75 | 5–30 |
| `accreditation_logo_width_mm` | 25 | 10–35 |

Artwork aspect ratios are retained and print heights are constrained. Use approved logo
artwork and check its final printed size. The `accredited` flag does not validate an assay's
accreditation status; the application supplies that decision.

For more center details or patient fields, increase `ReportConfig.header_height_mm`
from its 65 mm default. The allowed range is 40–120 mm. Review the longest expected
metadata together with the chosen logos and contact fields.

For eligible accreditation artwork, `ReportConfig.footer_height_mm` reserves 38 mm by
default (range 22–50 mm). This accommodates portrait artwork at 25 mm wide,
including the footer rule and padding. Reports without that artwork use a 22 mm footer.
The mark is placed at the left; template revision and page numbering stay at the right.

## Supported image formats

PNG, JPEG and restricted static SVG are accepted. SVG supports static shapes, text and
local fragment references. Scripts, entities, processing instructions, CSS URL resources,
external references and embedded documents are rejected. Outline text or convert to PNG
when an SVG source relies on unsupported CSS, embedded images or external fonts.

Missing files and invalid artwork fail loading rather than silently omitting the logo.

Public examples use generic application, center and accreditation placeholders. They do not
represent a real organization or accreditation body. Production JSON supplies the deploying
center's chosen artwork and assay eligibility; no institutional logo is bundled as a default.
