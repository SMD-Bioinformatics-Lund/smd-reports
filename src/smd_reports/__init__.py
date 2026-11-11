"""JSON-based report rendering with embedded HTML assets and optional PDF export."""

import logging

__version__ = "0.5.1"

from .errors import (
    PDFUnavailableError,
    ReportAssetError,
    ReportInputError,
    ReportRenderError,
    format_validation_error,
)
from .loading import ReportLoader
from .rendering import ReportRenderer
from .themes import Theme

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "ReportLoader",
    "ReportRenderer",
    "ReportAssetError",
    "ReportInputError",
    "ReportRenderError",
    "PDFUnavailableError",
    "format_validation_error",
    "Theme",
]
