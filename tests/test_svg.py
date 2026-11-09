"""Self-contained SVG artwork, embedded fonts and offline HTML/PDF rendering."""

import base64
import json
import os
import re
import struct
from pathlib import Path

import pytest
from pydantic import ValidationError

from smd_reports import ReportInputError, ReportLoader, ReportRenderer
from smd_reports._svg import validate_font_uri, validate_svg
from smd_reports.assets import validate_image
from smd_reports.rendering import _offline_url_fetcher, offline_fetcher

FONT_CSS = Path(__file__).parents[1] / "src/smd_reports/static/fonts.css"


def data_uri(content):
    return "data:image/svg+xml;base64," + base64.b64encode(content).decode()


def svg(body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="100" '
        'viewBox="0 0 240 100">' + body + "</svg>"
    ).encode()


@pytest.fixture
def font_uri():
    return re.search(r"data:font/woff2;base64,[A-Za-z0-9+/=]+", FONT_CSS.read_text())[0]


@pytest.fixture
def artwork(font_uri):
    return svg(
        '''<metadata xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:dc="http://purl.org/dc/elements/1.1/">
        <rdf:RDF><rdf:Description><dc:title>Example artwork</dc:title></rdf:Description></rdf:RDF>
        </metadata><defs><style>
        @font-face { font-family: ArtworkProof; src: url("'''
        + font_uri
        + """") format("woff2"); }
        .label { fill: #123456; font-family: ArtworkProof; font-size: 20px; }
        .panel { fill: url(#ink); stroke: #987654; }
        </style><linearGradient id="ink"><stop offset="0" stop-color="#ffffff"/>
        <stop offset="1" stop-color="#cccccc"/></linearGradient></defs>
        <rect class="panel" x="0" y="0" width="240" height="100"/>
        <text class="label" x="10" y="50">Artwork proof</text>"""
    )


def report_with_artwork(payloads, raw, *, location="accreditation"):
    payload = payloads["generic"]
    payload["branding"] = {}
    payload["sections"] = []
    uri = data_uri(raw)
    if location == "accreditation":
        payload["branding"] = {"accredited": True, "accreditation_logo": uri}
    elif location == "center":
        payload["branding"] = {"center_logo": uri}
    elif location == "image":
        payload["sections"] = [{"kind": "image", "key": "plot", "source": uri}]
    else:
        payload["sections"] = [
            {"kind": "text", "key": "notes", "text": "Example", "images": [{"source": uri}]}
        ]
    return ReportLoader().loads(json.dumps(payload))


@pytest.mark.parametrize("location", ["accreditation", "center", "image", "inline"])
def test_styles_fonts_and_original_artwork_survive_loading_and_html(payloads, artwork, location):
    uri = data_uri(artwork)
    assert validate_image(uri) == uri
    report = report_with_artwork(payloads, artwork, location=location)
    html = ReportRenderer().render_html(report)
    assert uri in html
    assert "font-family: ArtworkProof" in html
    assert base64.b64decode(uri.split(",", 1)[1]) == artwork
    restored = ReportLoader().loads(report.model_dump_json())
    assert ReportRenderer().render_html(restored) == html


def test_woff2_is_embedded_in_real_pdf_and_all_fetches_are_data(payloads, artwork, monkeypatch):
    weasyprint = pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    from urllib.request import HTTPRedirectHandler

    from weasyprint.urls import URLFetcher

    original = URLFetcher.fetch
    fetched = []

    def fetch(self, url, **kwargs):
        assert url.startswith("data:"), url
        assert self._allowed_protocols == {"data"}
        assert not any(isinstance(handler, HTTPRedirectHandler) for handler in self.handlers)
        fetched.append(url)
        return original(self, url, **kwargs)

    monkeypatch.setattr(URLFetcher, "fetch", fetch)
    report = report_with_artwork(payloads, artwork)
    document = pymupdf.open(stream=ReportRenderer().render_pdf(report), filetype="pdf")
    assert any("Artwork proof" in page.get_text() for page in document)
    assert any("ArtworkProof" in font[3] for page in document for font in page.get_fonts())
    assert any(url.startswith("data:font/woff2;") for url in fetched)
    assert data_uri(artwork) in fetched
    assert not any(page.get_images() for page in document)  # Artwork stays vector.
    spans = [
        span
        for page in document
        for block in page.get_text("dict")["blocks"]
        if block["type"] == 0
        for line in block["lines"]
        for span in line["spans"]
    ]
    assert any("Artwork proof" in span["text"] and span["color"] == 0x123456 for span in spans)
    # Exported HTML also carries the font definitions for conversion outside this package.
    standalone = weasyprint.HTML(
        string=ReportRenderer().render_html(report), url_fetcher=_offline_url_fetcher()
    ).write_pdf()
    external = pymupdf.open(stream=standalone, filetype="pdf")
    assert any("ArtworkProof" in font[3] for page in external for font in page.get_fonts())


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-le", "utf-16-be"])
def test_xml_declarations_and_inert_editor_metadata_are_supported(encoding):
    content = (
        f'<?xml version="1.0" encoding="{encoding.split("-le")[0].split("-be")[0]}"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:s="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
        'xmlns:i="http://www.inkscape.org/namespaces/inkscape">'
        '<s:namedview i:document-units="mm"><i:grid type="xygrid"/></s:namedview>'
        "<metadata>Source: https://example.org/artwork (example)</metadata>"
        '<style>.ink {fill:#123456}</style><path class="ink" d="M0 0h1v1Z"/></svg>'
    )
    assert validate_svg(content.encode(encoding)) == ()


@pytest.mark.parametrize(
    "body",
    [
        "<script/>",
        "<foreignObject/>",
        '<image href="data:image/png;base64,AAAA"/>',
        '<animate attributeName="href"/>',
        '<set attributeName="href"/>',
        "<metadata><script/></metadata>",
        '<g ONLOAD="alert(1)"/>',
        '<g xmlns:e="urn:events" e:onload="alert(1)"/>',
        '<use href="https://example.org/a.svg"/>',
        '<use href="file:///private.svg"/>',
        '<use href="//example.org/a.svg"/>',
        '<use href="&#104;ttps://example.org/a.svg"/>',
        '<g xml:base="https://example.org/"><use href="#shape"/></g>',
        '<metadata xmlns:h="http://www.w3.org/1999/xhtml"><h:iframe/></metadata>',
        '<style>@import "https://example.org/a.css";</style>',
        '<style>@im\\70ort "https://example.org/a.css";</style>',
        "<style>@namespace url(https://example.org/a);</style>",
        "<style>.a {fill:url(https://example.org/a)}</style>",
        '<style>.a {fill:u\\72l("https://example.org/a")}</style>',
        '<style>.a {fill:url("\\68 ttps://example.org/a")}</style>',
        '<style>.a {fill:url("%23local")}</style>',
        '<style>.a {fill:url("#x", "https://example.org")}</style>',
        '<style>.a {fill:url(broken"url)}</style>',
        "<style>.a {fill:expression(alert(1))}</style>",
        "<style>.a {fill:e\\78pression(alert(1))}</style>",
        '<style>.a {fill:image-set("https://example.org/a")}</style>',
        "<style>.a {fill:attr(data-resource url)}</style>",
        "<style>.a {-moz-binding:url(#x)}</style>",
        "<style>.a {behavior:url(#x)}</style>",
        "<style>.a {--resource:url(https://example.org/a);fill:var(--resource)}</style>",
        '<path style="fill:url(&quot;file:///private&quot;)"/>',
        '<path style="fill:u\\72l(https://example.org/a)"/>',
        '<style type="text/javascript">.a { fill:red }</style>',
        "<style><g/></style>",
    ],
)
def test_active_content_and_encoded_css_resources_are_rejected(payloads, body):
    raw = svg(body)
    with pytest.raises(ReportInputError):
        validate_image(data_uri(raw))
    with pytest.raises(ValidationError):
        report_with_artwork(payloads, raw)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-le", "utf-16-be"])
@pytest.mark.parametrize(
    "declaration",
    [
        "<!DOCTYPE svg>",
        '<!DOCTYPE svg [<!ENTITY text "example">]>',
        '<!DOCTYPE svg SYSTEM "file:///private.dtd">',
        '<?xml-stylesheet href="https://example.org/a.css"?>',
        "<?editor instruction?>",
    ],
)
def test_dtd_entities_and_processing_instructions_rejected_in_all_encodings(encoding, declaration):
    document = (
        f'<?xml version="1.0" encoding="{encoding.split("-le")[0].split("-be")[0]}"?>'
        + declaration
        + '<svg xmlns="http://www.w3.org/2000/svg"/>'
    ).encode(encoding)
    with pytest.raises(ReportInputError):
        validate_image(data_uri(document))


@pytest.mark.parametrize(
    "source",
    [
        "url(https://example.org/a.woff2)",
        "url(file:///private.woff2)",
        "url(data:font/woff2;base64,d09GMg==)",
        "url(data:font/woff2;base64,%%%%)",
        "url(data:image/svg+xml;base64,d09GMg==)",
        "url(data:font/woff2;base64,d09GMg%3d%3d)",
        'local("Installed Font")',
        "var(--font)",
        '"data:font/woff2;base64,d09GMg=="',
        "url(#font)",
        'url("\\68 ttps://example.org/font.woff2")',
    ],
)
def test_font_sources_must_be_complete_embedded_woff2_fonts(source):
    with pytest.raises(ReportInputError):
        validate_svg(svg("<style>@font-face{font-family:Example;src:" + source + "}</style>"))


@pytest.mark.parametrize(
    "mutation", ["truncated", "bad-size", "bad-expanded", "bad-compression", "bad-body"]
)
def test_woff2_header_and_contents_are_checked(font_uri, mutation):
    raw = bytearray(base64.b64decode(font_uri.split(",", 1)[1]))
    if mutation == "truncated":
        raw = raw[:48]
    elif mutation == "bad-size":
        struct.pack_into(">I", raw, 8, len(raw) + 1)
    elif mutation == "bad-expanded":
        struct.pack_into(">I", raw, 16, 0xFFFFFFFF)
    elif mutation == "bad-compression":
        struct.pack_into(">I", raw, 20, 0xFFFFFFFF)
    else:
        raw[1000:1100] = b"\xff" * 100
    uri = "data:font/woff2;base64," + base64.b64encode(raw).decode()
    with pytest.raises(ReportInputError):
        validate_font_uri(uri)
    with pytest.raises(ReportInputError):
        offline_fetcher(uri)


def test_font_face_must_not_break_out_of_html_style_element(payloads, font_uri):
    raw = svg(
        '<style><![CDATA[@font-face{font-family:"</style><script>bad</script>";src:url("'
        + font_uri
        + '")}]]></style>'
    )
    html = ReportRenderer().render_html(report_with_artwork(payloads, raw))
    assert "<script>" not in html and r"\3c /style>" in html
    assert data_uri(raw) in html


def test_conflicting_artwork_font_fails_instead_of_changing_report_font(payloads, font_uri):
    raw = svg(
        '<style>@font-face{font-family:"Source Sans 3";font-weight:600;src:url("'
        + font_uri
        + '")}</style>'
    )
    report = report_with_artwork(payloads, raw)
    with pytest.raises(ReportInputError, match="font-family conflicts"):
        ReportRenderer().render_html(report)


def test_read_only_reference_accreditation_artwork(payloads):
    filename = os.environ.get("SMD_REPORTS_REFERENCE_SVG")
    if not filename:
        pytest.skip("Set SMD_REPORTS_REFERENCE_SVG to inspect external artwork read-only")
    raw = Path(filename).read_bytes()
    report = report_with_artwork(payloads, raw)
    html = ReportRenderer().render_html(report)
    assert data_uri(raw) in html
    assert base64.b64decode(report.branding.accreditation_logo.split(",", 1)[1]) == raw
    pytest.importorskip("weasyprint")
    pymupdf = pytest.importorskip("pymupdf")
    pdf = pymupdf.open(stream=ReportRenderer().render_pdf(report), filetype="pdf")
    assert len(pdf) == 1
    assert pdf[0].get_drawings()
    assert not pdf[0].get_images()


def test_static_selectors_and_escaped_local_resources_are_supported():
    raw = svg(
        '<style>.a:not(.b) {fill:u\\72l("\\23 ink")}</style>'
        '<defs><linearGradient id="ink"/></defs><path class="a" d="M0 0h1v1Z"/>'
    )
    assert validate_image(data_uri(raw)) == data_uri(raw)


@pytest.mark.parametrize(
    "descriptor",
    [
        'src:url("{font}") format("truetype")',
        'src:url("{font}"),local("Example")',
        'src:url("{font}"),',
        'src:format("woff2")',
        "font-family:Example",
        'src:url("{font}");font-family:Example,Other',
        'src:url("{font}");font-family:""',
    ],
)
def test_malformed_font_descriptors_are_rejected(font_uri, descriptor):
    raw = svg(
        "<style>@font-face{font-family:Example;" + descriptor.format(font=font_uri) + "}</style>"
    )
    with pytest.raises(ReportInputError):
        validate_image(data_uri(raw))


@pytest.mark.parametrize("mutation", ["metadata-bounds", "metadata-size", "private-bounds"])
def test_font_auxiliary_blocks_cannot_escape_bounds(font_uri, mutation):
    raw = bytearray(base64.b64decode(font_uri.split(",", 1)[1]))
    if mutation == "metadata-bounds":
        struct.pack_into(">III", raw, 28, len(raw) + 1, 1, 1)
    elif mutation == "metadata-size":
        struct.pack_into(">I", raw, 36, 1)
    else:
        struct.pack_into(">II", raw, 40, len(raw) + 1, 1)
    uri = "data:font/woff2;base64," + base64.b64encode(raw).decode()
    with pytest.raises(ReportInputError):
        validate_font_uri(uri)


def test_svg_glyph_documents_inside_fonts_are_rejected(font_uri):
    from io import BytesIO

    from fontTools.ttLib import TTFont
    from fontTools.ttLib.tables.DefaultTable import DefaultTable

    raw = base64.b64decode(font_uri.split(",", 1)[1])
    font = TTFont(BytesIO(raw))
    table = DefaultTable("SVG ")
    table.data = b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>'
    font["SVG "] = table
    output = BytesIO()
    font.save(output)
    font.close()
    uri = "data:font/woff2;base64," + base64.b64encode(output.getvalue()).decode()
    with pytest.raises(ReportInputError, match="Invalid embedded WOFF2"):
        validate_font_uri(uri)


@pytest.mark.parametrize(
    "source",
    ["https://example.org/private.svg", "file:///private.svg", "data:font/woff2;base64,d09GMg=="],
)
def test_real_pdf_rejects_invalid_resources_before_fetching(payloads, monkeypatch, source):
    pytest.importorskip("weasyprint")
    from weasyprint.urls import URLFetcher

    from smd_reports import ReportRenderError

    fetched = []
    original = URLFetcher.fetch

    def fetch(self, url, **kwargs):
        fetched.append(url)
        return original(self, url, **kwargs)

    monkeypatch.setattr(URLFetcher, "fetch", fetch)
    report = report_with_artwork(payloads, svg('<path d="M0 0h1v1Z"/>'))
    renderer = ReportRenderer()
    html = (
        '<style>@font-face{font-family:Bad;src:url("' + source + '")}</style><p>Test</p>'
        if source.startswith("data:font")
        else '<img src="' + source + '">'
    )
    monkeypatch.setattr(renderer, "render_html", lambda *args, **kwargs: html)
    with pytest.raises(ReportRenderError):
        renderer.render_pdf(report)
    assert fetched == []


@pytest.mark.parametrize(
    "body",
    [
        '<metadata data-author="reports@example.org" data-note="Owner\'s artwork @ 2x"/>',
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:creator contact="reports@example.org">Example author</dc:creator></metadata>',
        '<metadata xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:RDF><rdf:Description rdf:about="" rdf:resource="mailto:reports@example.org"/>'
        "</rdf:RDF></metadata>",
        '<g xmlns:i="http://www.inkscape.org/namespaces/inkscape" '
        'i:export-filename="/examples/artwork@2x.svg"/>',
        '<s:namedview xmlns:s="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
        'name="Example @ 2x (reviewed)"/>',
    ],
)
def test_inert_metadata_punctuation_survives_json_loading_and_html(payloads, body):
    raw = svg(body + '<path d="M0 0h1v1Z"/>')
    report = report_with_artwork(payloads, raw)
    assert report.branding.accreditation_logo == data_uri(raw)
    assert data_uri(raw) in ReportRenderer().render_html(report)


@pytest.mark.parametrize(
    "body",
    [
        '<metadata style="fill:url(https://example.org/image)"/>',
        '<metadata fill="url(file:///image)"/>',
        '<metadata onclick="run()"/>',
        '<metadata href="https://example.org/image"/>',
        '<metadata src="file:///image"/>',
        '<metadata xml:base="https://example.org/"/>',
        '<s:namedview xmlns:s="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
        'style="fill:u\\72l(https://example.org/image)"/>',
        '<g xmlns:i="http://www.inkscape.org/namespaces/inkscape" i:onload="run()"/>',
    ],
)
def test_inert_metadata_does_not_bypass_style_resource_or_event_checks(body):
    with pytest.raises(ReportInputError):
        validate_image(data_uri(svg(body)))


@pytest.mark.parametrize("application", ["generic", "coyote3", "cll_genie", "genexus", "pgx"])
@pytest.mark.parametrize("slot", ["application_logo", "accreditation_logo"])
def test_only_visible_logos_contribute_font_definitions(payloads, font_uri, application, slot):
    raw = svg(
        '<style>@font-face{font-family:"Source Sans 3";font-weight:600;src:url("'
        + font_uri
        + '")}</style><path d="M0 0h1v1Z"/>'
    )
    payload = payloads["generic"]
    payload.update(application=application, branding={slot: data_uri(raw)}, sections=[])
    report = ReportLoader().loads(json.dumps(payload))
    if slot == "application_logo" and application in {"coyote3", "cll_genie"}:
        with pytest.raises(ReportInputError, match="font-family conflicts"):
            ReportRenderer().render_html(report)
    else:
        html = ReportRenderer().render_html(report)
        assert data_uri(raw) not in html
        assert html.count("@font-face") == FONT_CSS.read_text().count("@font-face")
        pytest.importorskip("weasyprint")
        pymupdf = pytest.importorskip("pymupdf")
        pdf = pymupdf.open(stream=ReportRenderer().render_pdf(report), filetype="pdf")
        assert len(pdf) == 1 and report.metadata.report_id in pdf[0].get_text()


@pytest.mark.parametrize("slot", ["application_logo", "accreditation_logo"])
def test_hidden_logo_content_is_still_validated(payloads, slot):
    payload = payloads["generic"]
    payload["branding"] = {slot: data_uri(svg("<script/>"))}
    with pytest.raises(ValidationError):
        ReportLoader().loads(json.dumps(payload))
