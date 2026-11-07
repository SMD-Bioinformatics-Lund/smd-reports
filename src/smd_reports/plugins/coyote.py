"""Coyote3 receives prepared findings and evaluated clinical text from its host."""

from typing import Literal

from .prepared import PreparedContent, PreparedData, PreparedReport


class CoyoteContent(PreparedContent):
    """DNA/RNA reporting inputs; supported analyses do not imply enabled sections."""

    analyte: Literal["dna", "rna"]


class CoyoteData(CoyoteContent, PreparedData):
    """Coyote content with shared Python document inputs."""


class CoyoteReport(PreparedReport):
    """Build Coyote3 reports without querying data or evaluating clinical rules."""

    application = "coyote3"

    def __init__(self, data: CoyoteData, config):
        super().__init__(data, config)
