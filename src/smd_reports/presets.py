"""Named defaults for the shared report layout and theme registry."""

from dataclasses import dataclass
from typing import Literal

PresetName = Literal["generic", "coyote3", "genexus", "cll_genie", "pgx"]
HeaderStyle = Literal["center", "branded"]


@dataclass(frozen=True)
class Preset:
    """Presentation defaults selected by an optional report preset."""

    template_name: str
    theme: str
    application_name: str = ""
    application_suffix: str = ""
    header: HeaderStyle = "center"
    header_rule: bool = True
    repeat_title: bool = False
    black_title: bool = False
    metadata_borders: bool = False
    metadata_heading: str = "Sample information"
    document_label: str = "Analysis report"
    template_analytes: tuple[str, ...] = ()


PRESETS = {
    "generic": Preset(
        "Report", "generic", metadata_heading="Report information", document_label="Report"
    ),
    "coyote3": Preset(
        "Coyote3", "coyote3", "Coyote", "3", header="branded", template_analytes=("dna", "rna")
    ),
    "cll_genie": Preset("CLL Genie", "cll_genie", "CLL Genie", header="branded"),
    "genexus": Preset(
        "Genexus", "genexus", repeat_title=True, black_title=True, metadata_borders=True
    ),
    "pgx": Preset("PGx", "pgx"),
}
