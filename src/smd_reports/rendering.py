"""Render standalone HTML and load the optional PDF renderer when needed."""

from importlib.resources import files

import bleach
import markdown
from jinja2 import Environment, PackageLoader, StrictUndefined, pass_context, select_autoescape
from markupsafe import Markup

from .core import Report
from .localization import label
from .themes import Theme, default_themes


class PDFUnavailableError(RuntimeError):
    """The optional renderer or its native runtime is unavailable."""


def format_markdown(value: str) -> Markup:
    """Convert Markdown into sanitized report HTML.

    Args:
        value: Markdown source text.

    Returns:
        Markup containing permitted text, heading, list, and table elements.
    """
    html = markdown.markdown(value, extensions=["tables", "sane_lists"])
    return Markup(
        bleach.clean(
            html,
            tags={
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
                "h5",
                "h6",
                "h3",
                "h4",
            },
            attributes={},
            protocols=[],
            strip=True,
        )
    )


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
        return ("Yes" if value else "No") if language == "en" else ("Ja" if value else "Nej")
    return str(value)


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


def offline_fetcher(url, **kwargs):
    """Fetch embedded image/font data without accessing files or the network.

    Args:
        url: Supported image or font data URI.
        **kwargs: Options forwarded to WeasyPrint's data fetcher.

    Returns:
        The resource dictionary expected by WeasyPrint.

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
    from weasyprint import default_url_fetcher

    return default_url_fetcher(url, **kwargs)


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
            display=display_in_language,
            ui=ui_label,
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
            raise ValueError(f"Theme already registered: {theme.name}")
        self.themes[theme.name] = Theme.model_validate(theme.model_dump())

    def render_html(self, report: Report, *, theme: str | None = None) -> str:
        """Render a complete HTML document with embedded styles and artwork.

        Args:
            report: Validated document returned by ReportLoader.
            theme: Optional registered theme name overriding the report preset.

        Returns:
            A standalone HTML document.

        Raises:
            ValueError: A theme or embedded image is invalid.
            pydantic.ValidationError: The report was modified into an invalid state.
        """
        report = Report.model_validate(report.model_dump())
        selected = theme or report.application
        if selected not in self.themes:
            raise ValueError(f"Unknown theme: {selected}")
        assets = files("smd_reports").joinpath("static")
        return self.environment.get_template("clinical.html").render(
            report=report,
            theme=self.themes[selected],
            css=assets.joinpath("report.css").read_text(encoding="utf-8"),
            fonts=assets.joinpath("fonts.css").read_text(encoding="utf-8"),
        )

    def render_pdf(self, report: Report, *, theme: str | None = None) -> bytes:
        """Convert the standalone report HTML into PDF bytes.

        Args:
            report: Validated document returned by ReportLoader.
            theme: Optional registered theme name overriding the report preset.

        Returns:
            PDF bytes containing the report and automatic rendering metadata.

        Raises:
            PDFUnavailableError: WeasyPrint or its native libraries are unavailable.
            ValueError: A theme or embedded image is invalid.
            pydantic.ValidationError: The report was modified into an invalid state.
        """
        try:
            from weasyprint import HTML
        except (ImportError, OSError) as exc:
            raise PDFUnavailableError(
                "Install smd-reports[pdf] and the WeasyPrint native runtime to render PDFs"
            ) from exc
        return HTML(
            string=self.render_html(report, theme=theme), url_fetcher=offline_fetcher
        ).write_pdf(custom_metadata=True)
