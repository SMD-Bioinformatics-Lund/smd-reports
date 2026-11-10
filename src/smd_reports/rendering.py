"""Render standalone HTML and load the optional PDF renderer when needed."""

import logging
import re
from html import escape, unescape
from importlib.resources import files

import bleach
import markdown
from jinja2 import (
    Environment,
    PackageLoader,
    StrictUndefined,
    TemplateError,
    pass_context,
    select_autoescape,
)
from markupsafe import Markup

from .badges import badge_colors
from .compact_layout import column_widths
from .core import Report
from .errors import PDFUnavailableError, ReportInputError, ReportRenderError
from .localization import label, localized_text
from .svg_validation import svg_font_css, validate_font_uri
from .themes import Theme, default_themes

logger = logging.getLogger(__name__)


def format_markdown(value: str) -> Markup:
    """Convert Markdown into sanitized HTML while preserving placeholder text.

    Args:
        value: Markdown source text. Uppercase tokens such as <PATIENT_NAME>
            remain visible in paragraphs, tables, and code.

    Returns:
        Markup containing permitted text, heading, list, and table elements.
    """
    allowed_tags = {
        "p",
        "br",
        "strong",
        "em",
        "ul",
        "ol",
        "li",
        "blockquote",
        "code",
        "pre",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }
    html = markdown.markdown(value, extensions=["tables", "sane_lists"])
    # Protect placeholder text before the sanitizer treats it as an unknown HTML tag.
    html = re.sub(
        r"<([A-Z][A-Z0-9_]*)>",
        lambda match: match[0] if match[1].lower() in allowed_tags else escape(match[0]),
        html,
    )
    return Markup(bleach.clean(html, tags=allowed_tags, attributes={}, protocols=[], strip=True))


def display(value, language="sv"):
    """Format a cell value, preserving zero and false.

    Args:
        value: A scalar or English/Swedish translation mapping.
        language: Language used for translated values and booleans.

    Returns:
        Display text, or a hyphen for None and empty strings.
    """
    if isinstance(value, dict):
        value = label(value, language)
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return label("Yes" if value else "No", language)
    return str(value)


@pass_context
def render_cell(context, value, column):
    """Render a cell using optional badges or its existing text format.

    Args:
        context: Template context containing the report language and selected theme.
        value: Scalar or translated cell value.
        column: Validated column display options.

    Returns:
        Escaped text, sanitized Markdown, or a badge with validated inline colors.
    """
    language = context["report"].language
    text = display(value, language)
    original = label(value, language) if isinstance(value, dict) else value
    if column.badge is not None and original is not None and original != "" and text.strip():
        style = column.badge.style_for(text)
        if style is not None:
            background, foreground = badge_colors(style, context["theme"].heading)
            return Markup(
                '<span class="report-badge" style="background-color: {}; color: {};{}">{}</span>'
            ).format(
                background, foreground, " " + column.text_style if column.text_style else "", text
            )
    return format_markdown(text) if column.format == "markdown" else Markup.escape(text)


@pass_context
def display_in_language(context, value):
    """Format a cell in the active report language.

    Args:
        context: Jinja context containing the loaded report.
        value: Scalar or translated cell value.

    Returns:
        The cell's display text.
    """
    return display(value, context["report"].language)


@pass_context
def localized_in_language(context, value):
    """Select localized branding text while preserving literal names.

    Args:
        context: Template context containing the report language.
        value: Literal text or a translation mapping.

    Returns:
        The supplied text in the selected report language.
    """
    return localized_text(value, context["report"].language)


@pass_context
def ui_label(context, value):
    """Resolve interface text in the active report language.

    Args:
        context: Jinja context containing the loaded report.
        value: Literal label or English/Swedish translation mapping.

    Returns:
        The selected label text.
    """
    return label(value, context["report"].language)


@pass_context
def record_heading(context, section, values, index):
    """Resolve a finding heading from explicit titles or positional values.

    Args:
        context: Jinja context containing the loaded report.
        section: Detail or grid section with heading configuration.
        values: Values for the current finding.
        index: Zero-based finding index.

    Returns:
        The translated and formatted finding heading.
    """
    if section.record_titles is not None:
        return label(section.record_titles[index], context["report"].language)
    if section.record_heading is not None:
        pattern = label(section.record_heading, context["report"].language)
        return pattern.format(*[display(value, context["report"].language) for value in values])
    return display(values[0], context["report"].language)


@pass_context
def grid_row_visible(context, layout, values):
    """Check whether a translated grid row contains displayable values.

    Args:
        context: Jinja context containing the loaded report.
        layout: Grid row with an optional hide-if-empty setting.
        values: Values for the current finding.

    Returns:
        False only when empty-row suppression is enabled and all referenced
        values are null or empty. Zero and false remain visible.
    """
    selected = [
        label(values[cell.column], context["report"].language)
        if isinstance(values[cell.column], dict)
        else values[cell.column]
        for cell in layout.cells
    ]
    return not layout.hide_if_empty or any(value is not None and value != "" for value in selected)


@pass_context
def image_uri(context, value, frame=0, plot=False):
    """Prepare an embedded image for the active report.

    Args:
        context: Jinja context containing the loaded report.
        value: Embedded image data URI.
        frame: Zero-based frame or TIFF page index.
        plot: Whether to enforce the report's accepted plot-format list.

    Returns:
        An embedded, portable image data URI.

    Raises:
        ValueError: The image, selected frame, or requested format is invalid.
    """
    from .assets import prepare_image

    formats = context["report"].presentation.accepted_image_formats if plot else None
    return prepare_image(value, frame=frame, accepted_formats=formats)


def _compact_tables(report, theme):
    """Prepare single-line cells and fitted column widths for compact tables.

    Args:
        report: Validated report and its selected language and page dimensions.
        theme: Theme supplying the normal report text size.

    Returns:
        Prepared rows and column widths indexed by section key.

    Raises:
        ReportInputError: Cell content requires multiple lines or exceeds the page width.
    """
    result = {}
    for section in report.sections:
        if section.kind != "compact_table":
            continue
        values, texts = [], []
        for item in section.items:
            if isinstance(item, dict):
                item = label(item, report.language)
            if item is None or (isinstance(item, str) and not item.strip()):
                continue
            text = " ".join(display(item, report.language).split())
            if section.format == "markdown":
                rendered = str(format_markdown(text))
                tags = re.findall(r"</?([a-z][a-z0-9]*)\b[^>]*>", rendered)
                if set(tags) - {"p", "strong", "em", "code"} or tags.count("p") > 2:
                    raise ReportInputError(
                        "Compact table items support single-line text and inline Markdown only."
                    )
                rendered = rendered.removeprefix("<p>").removesuffix("</p>")
                text = unescape(bleach.clean(rendered, tags=[], strip=True))
                value = Markup(rendered)
            else:
                value = text
            if not text.strip():
                continue
            values.append(value)
            texts.append(text)
        widths = column_widths(
            texts,
            theme.body_pt - 2.5,
            report.presentation.dimensions_mm[0] - 32,
            columns=section.columns,
            markdown=section.format == "markdown",
        )
        count = len(widths)
        result[section.key] = {
            "rows": [values[index : index + count] for index in range(0, len(values), count)]
            if count
            else [],
            "widths": widths,
            "width": sum(widths),
        }
    return result


def offline_fetcher(url, **kwargs):
    """Fetch embedded image/font data without accessing files or the network.

    Args:
        url: Supported image or font data URI.
        **kwargs: Options forwarded to WeasyPrint's data fetcher.

    Returns:
        The resource response expected by WeasyPrint.

    Raises:
        ValueError: The URL is external or its embedded image is invalid.
    """
    allowed = (
        "data:image/png;base64,",
        "data:image/jpeg;base64,",
        "data:image/svg+xml;base64,",
        "data:font/woff2;base64,",
    )
    if not url.startswith(allowed):
        raise ValueError("External report resources are prohibited")
    if url.startswith("data:image/"):
        from .assets import validate_image

        validate_image(url)
    elif url.startswith("data:font/woff2;base64,"):
        validate_font_uri(url)
    from weasyprint.urls import URLFetcher

    return URLFetcher(allowed_protocols={"data"}, allow_redirects=False).fetch(url, **kwargs)


def _offline_url_fetcher():
    """Create a restricted fetcher that records failures swallowed by the PDF engine.

    Returns:
        A WeasyPrint URLFetcher restricted to validated embedded resources.
    """
    from weasyprint.urls import URLFetcher

    class EmbeddedResourceFetcher(URLFetcher):
        """Validate embedded resources and retain their failure status."""

        failed = False

        def fetch(self, url, headers=None):
            """Fetch one validated resource and record failures.

            Args:
                url: Embedded image or font URL.
                headers: Optional headers supplied by WeasyPrint.

            Returns:
                A validated embedded resource response.

            Raises:
                Exception: Validation or decoding of the resource fails.
            """
            try:
                return offline_fetcher(url, headers=headers)
            except Exception:
                self.failed = True
                raise

    return EmbeddedResourceFetcher(
        allowed_protocols={"data"}, allow_redirects=False, fail_on_errors=True
    )


class ReportRenderer:
    """Render reports using built-in templates and registered themes."""

    def __init__(self):
        """Create the template environment and independent preset themes."""
        self.themes = default_themes()
        self.environment = Environment(
            loader=PackageLoader("smd_reports", "templates"),
            undefined=StrictUndefined,
            autoescape=select_autoescape(default=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.environment.filters.update(
            markdown=format_markdown,
            cell=render_cell,
            display=display_in_language,
            ui=ui_label,
            localized=localized_in_language,
            heading=record_heading,
            grid_row_visible=grid_row_visible,
            image_uri=image_uri,
        )

    def register_theme(self, theme: Theme) -> None:
        """Register a custom theme without replacing an existing preset.

        Args:
            theme: Theme instance containing a new name and validated color tokens.

        Raises:
            ValueError: A theme with the same name is already registered.
            pydantic.ValidationError: The theme contains invalid design tokens.
        """
        if theme.name in self.themes:
            raise ReportInputError("Theme already registered; choose a different theme name.")
        self.themes[theme.name] = Theme.model_validate(theme.model_dump())

    def render_html(self, report: Report, *, theme: str | None = None) -> str:
        """Render a complete HTML document with embedded styles and artwork.

        Args:
            report: Validated document returned by ReportLoader.
            theme: Optional registered name overriding the JSON theme and preset defaults.

        Returns:
            A standalone HTML document.

        Raises:
            ValueError: A theme or embedded image is invalid.
            pydantic.ValidationError: The report was modified into an invalid state.
            ReportRenderError: Templates, package assets or the rendering engine failed.
        """
        logger.info("Rendering report HTML")
        try:
            if not isinstance(report, Report):
                raise TypeError("Supply a report returned by ReportLoader.load() or loads().")
            report = Report.model_validate(report.model_dump())
            selected = theme or report.theme_name
            layout = report.resolved_layout
            if selected not in self.themes:
                raise ReportInputError(
                    "Unknown theme; choose a built-in theme or register it before rendering."
                )
            assets = files("smd_reports").joinpath("static")
            fonts = assets.joinpath("fonts.css").read_text(encoding="utf-8")
            artwork = [report.branding.center_logo]
            if layout.header == "branded":
                artwork.append(report.branding.application_logo)
            if report.branding.accredited:
                artwork.append(report.branding.accreditation_logo)
            for section in report.sections:
                artwork.extend(image.source for image in section.images)
                if section.kind == "image":
                    artwork.append(section.source)
            html = self.environment.get_template("clinical.html").render(
                report=report,
                layout=layout,
                selected_theme=selected,
                theme=self.themes[selected],
                css=assets.joinpath("report.css").read_text(encoding="utf-8"),
                fonts=fonts,
                svg_fonts=svg_font_css(artwork, fonts),
                compact_tables=_compact_tables(report, self.themes[selected]),
            )
        except (TemplateError, OSError) as exc:
            logger.error("Report HTML rendering failed")
            raise ReportRenderError(
                "Could not render report HTML. Check the installed templates and package assets."
            ) from exc
        except (TypeError, ValueError):
            logger.error("Report HTML rendering failed: invalid report, image or theme")
            raise
        except Exception as exc:
            logger.error("Report HTML rendering failed")
            raise ReportRenderError(
                "Could not render report HTML. Check the installed templates and package assets."
            ) from exc
        logger.info("Report HTML rendered")
        return html

    def render_pdf(self, report: Report, *, theme: str | None = None) -> bytes:
        """Convert the standalone report HTML into PDF bytes.

        Args:
            report: Validated document returned by ReportLoader.
            theme: Optional registered name overriding the JSON theme and preset defaults.

        Returns:
            PDF bytes containing the report and automatic rendering metadata.

        Raises:
            PDFUnavailableError: WeasyPrint or its native libraries are unavailable.
            ValueError: A theme or embedded image is invalid.
            pydantic.ValidationError: The report was modified into an invalid state.
            ReportRenderError: Templates, package assets or the rendering engine failed.
        """
        logger.info("Rendering report PDF")
        try:
            from weasyprint import HTML
            from weasyprint.urls import FatalURLFetchingError
        except (ImportError, OSError) as exc:
            logger.error("PDF rendering is unavailable: missing PDF dependencies")
            raise PDFUnavailableError(
                "Install smd-reports[pdf] and the WeasyPrint native runtime to render PDFs."
            ) from exc
        html = self.render_html(report, theme=theme)
        try:
            fetcher = _offline_url_fetcher()
            result = HTML(string=html, url_fetcher=fetcher).write_pdf(custom_metadata=True)
            # WeasyPrint can continue after a failed fetch; do not return an incomplete report.
            if fetcher.failed:
                raise ReportRenderError(
                    "PDF resources could not be loaded. Check embedded images and fonts."
                )
        except (Exception, FatalURLFetchingError) as exc:
            logger.error("Report PDF rendering failed")
            if isinstance(exc, ReportRenderError):
                raise
            raise ReportRenderError(
                "Could not generate the PDF. Check the PDF runtime and installed package assets."
            ) from exc
        logger.info("Report PDF rendered")
        return result
