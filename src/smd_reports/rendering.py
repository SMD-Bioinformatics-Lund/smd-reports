"""Offline HTML-first rendering; PDF support is imported only when requested."""

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
    """Render Markdown with safe structure and no embedded external resources."""
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
                "h3",
                "h4",
            },
            attributes={},
            protocols=[],
            strip=True,
        )
    )


def display(value, language="sv"):
    """Preserve zero/false rather than treating them as missing values."""
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return ("Yes" if value else "No") if language == "en" else ("Ja" if value else "Nej")
    return str(value)


@pass_context
def display_in_language(context, value):
    """Format scalar values in the document language."""
    return display(value, context["report"].language)


@pass_context
def ui_label(context, value):
    """Translate explicitly marked interface labels in templates."""
    return label(value, context["report"].language)


def offline_fetcher(url, **kwargs):
    """Allow embedded raster/font resources only; never access disk or the network."""
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
    """Render validated documents using an isolated theme registry."""

    def __init__(self):
        self.themes = default_themes()
        self.environment = Environment(
            loader=PackageLoader("smd_reports", "templates"),
            undefined=StrictUndefined,
            autoescape=select_autoescape(default=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.environment.filters.update(
            markdown=format_markdown, display=display_in_language, ui=ui_label
        )

    def register_theme(self, theme: Theme) -> None:
        """Register an additional theme without replacing existing names."""
        if theme.name in self.themes:
            raise ValueError(f"Theme already registered: {theme.name}")
        self.themes[theme.name] = Theme.model_validate(theme.model_dump())

    def render_html(self, report: Report, *, theme: str | None = None) -> str:
        """Return a self-contained document, revalidating potentially mutated inputs."""
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
        """Render the canonical HTML without saving files or fetching external assets."""
        try:
            from weasyprint import HTML
        except (ImportError, OSError) as exc:
            raise PDFUnavailableError(
                "Install smd-reports[pdf] and the WeasyPrint native runtime to render PDFs"
            ) from exc
        return HTML(
            string=self.render_html(report, theme=theme), url_fetcher=offline_fetcher
        ).write_pdf()
