"""JSON-based report rendering with embedded HTML assets and optional PDF export."""

__version__ = "0.1.0"

from .loading import ReportAssetError, ReportLoader
from .rendering import PDFUnavailableError, ReportRenderer
from .themes import Theme

__all__ = ["ReportLoader", "ReportRenderer", "ReportAssetError", "PDFUnavailableError", "Theme"]
