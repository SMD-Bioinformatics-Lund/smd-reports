# Center branding

Add a `branding` object to the JSON document:

```json
{
  "branding": {
    "application_logo": "logos/application.svg",
    "center_logo": "logos/center.png",
    "accreditation_logo": "logos/accreditation.svg",
    "organization": "Example Diagnostics Center",
    "department": "Molecular Diagnostics",
    "address": "Example address 1",
    "telephone": "000-000000",
    "email": "demo@example.org",
    "accredited": true,
    "accreditation_label": {
      "en": "Accreditation mark",
      "sv": "Ackrediteringsmärke"
    }
  }
}
```

Paths resolve relative to the JSON file. Absolute paths and base64 image data URIs are
also accepted. The loader embeds local artwork automatically; generated HTML and portable
JSON no longer depend on those files. When loading JSON text, use `loads(..., base_dir=...)`
for relative paths.

## Header and footer

| Field | Placement |
| --- | --- |
| `organization` | Center name in the header |
| `department`, `address`, `telephone`, `email`, `website` | Header contact information |
| `application_logo` | Optional Coyote3/CLL Genie header icon |
| `center_logo` | Header beside center details |
| `accreditation_logo` | Left footer when `accredited` is true |
| `accreditation_label` | Logo alternative text |

Coyote3 shows a purple/orange application name; CLL Genie uses dark orange. Generic, Genexus and
PGx presets use center-only headers. Omitting the application logo retains the colored name.
No institutional logos or center information are supplied as defaults.

## Dimensions

| Setting | Default | Range |
| --- | --- | --- |
| `branding.center_logo_width_mm` | 11.64 | 5–35 |
| `branding.application_logo_width_mm` | 13.75 | 5–30 |
| `branding.accreditation_logo_width_mm` | 25 | 10–35 |
| `presentation.header_height_mm` | 65 | 40–120 |
| `presentation.footer_height_mm` | 38 | 22–50 |

Artwork keeps its aspect ratio. Header information repeats on PDF pages. The footer places
the accreditation image on the left and template/page numbering on the right. Without
accreditation artwork, the PDF uses a 22 mm footer.

## Image formats

PNG, JPEG, static SVG, WebP, GIF, TIFF and BMP are supported. SVG scripts, external references, entities,
embedded documents and CSS URL resources are rejected. Missing or unsupported artwork
produces a loading error. Public examples use generic logos and a synthetic CNV plot from `examples/assets/`.
