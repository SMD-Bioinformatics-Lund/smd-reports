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
accreditation artwork, the PDF uses a 22 mm footer. Accreditation logos fit within their
configured width and the available footer height while preserving their aspect ratio.
The footer reserves 9 mm for spacing and its border; taller artwork is reduced to fit.

## Image formats

PNG, JPEG, static SVG, WebP, GIF, TIFF and BMP are supported. Missing or unsupported
artwork produces a loading error. Public examples use generic logos and a synthetic
CNV plot from `examples/assets/`.

### Self-contained SVG

SVG artwork is embedded unchanged, including its colours, text, static CSS and fonts.
Supported content includes `<style>` rules, `@font-face`, plain metadata, RDF/Dublin Core,
Creative Commons/XMP metadata, and Inkscape/Sodipodi editor metadata. CSS presentation
properties, inline styles and local fragment references such as `fill: url(#gradient)`
are accepted. Other at-rules, unsupported elements and unsupported CSS properties or
functions produce an error rather than being removed.

Embed fonts with `src: url("data:font/woff2;base64,...") format("woff2")`. The package
checks base64 encoding, WOFF2 headers, compressed contents and OpenType tables. Each font
is limited to 2 MiB compressed and 16 MiB expanded; fonts containing SVG glyph documents
are unsupported. External fonts and `local()` font sources are rejected. Without an
embedded font, SVG text uses fonts installed on the conversion machine.

Original SVG bytes and inert metadata values are retained. Validated font-face rules are also included in the HTML
stylesheet for converters that do not load font-face rules inside SVG images, including
WeasyPrint 63. This keeps embedded typography available when converting the HTML elsewhere, without
rasterizing the artwork. Only artwork displayed by the selected layout contributes font
definitions. Use distinct artwork font-family names: conflicting definitions
between artwork and report fonts produce an error instead of changing report typography.

Scripts, event handlers, animation, `foreignObject`, embedded images/documents, external
network/file references, DTDs, entities and XML processing instructions are rejected.
CSS escapes are decoded before validating references; imports, active CSS and malformed
font data also produce errors. Resource fetching during package PDF rendering remains
restricted to validated embedded image and WOFF2 data URIs.
