"""Genexus consumes normalized findings and narrative prepared by the plugin host."""

from pydantic import Field

from ..core import FieldValue
from .prepared import PreparedContent, PreparedData, PreparedReport


class GenexusContent(PreparedContent):
    """Prepared sample, assay and run context; exported data is parsed by Genexus."""

    assay: list[FieldValue] = Field(default_factory=list)
    run: list[FieldValue] = Field(default_factory=list)


class GenexusData(GenexusContent, PreparedData):
    """Genexus content with shared Python document inputs."""


class GenexusReport(PreparedReport):
    """Build a report without discovering inputs or generating clinical narratives."""

    application = "genexus"

    def __init__(self, data: GenexusData, config):
        super().__init__(data, config)

    def build(self):
        document = super().build()
        document.metadata.fields.extend(
            field.model_copy(deep=True) for field in self.data.assay + self.data.run
        )
        return document
