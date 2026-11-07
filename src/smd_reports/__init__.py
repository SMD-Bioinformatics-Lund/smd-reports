"""Class-based clinical reporting with bundled application builders."""

__version__ = "0.1.0"

from .core import (
    Branding,
    ClinicalReport,
    Column,
    FieldValue,
    ImageSection,
    Provenance,
    Report,
    ReportMetadata,
    ReportSection,
    TableSection,
    TextSection,
)
from .loading import ReportLoader
from .plugins.cll_genie import CLLGenieData, CLLGenieReport, CLLSequence
from .plugins.coyote import CoyoteData, CoyoteReport
from .plugins.genexus import GenexusData, GenexusReport
from .plugins.pgx import PGxData, PGxFiles, PGxReport
from .plugins.prepared import Analysis, ReportConfig
from .rendering import PDFUnavailableError, ReportRenderer
from .themes import Theme

__all__ = [
    "ReportLoader",
    "Analysis",
    "ReportConfig",
    "Branding",
    "ClinicalReport",
    "Column",
    "FieldValue",
    "ImageSection",
    "Provenance",
    "Report",
    "ReportMetadata",
    "ReportSection",
    "TableSection",
    "TextSection",
    "CLLGenieData",
    "CLLGenieReport",
    "CLLSequence",
    "CoyoteData",
    "CoyoteReport",
    "GenexusData",
    "GenexusReport",
    "PGxData",
    "PGxFiles",
    "PGxReport",
    "PDFUnavailableError",
    "ReportRenderer",
    "Theme",
]
