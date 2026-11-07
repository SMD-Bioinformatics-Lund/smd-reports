"""PGx file ingestion and report preparation extracted from PGxModule semantics."""

import csv
import re
from pathlib import Path

from pydantic import Field

from ..core import Column, Model, TableSection
from ..localization import localize_table
from .prepared import PreparedContent, PreparedData, PreparedReport, ReportConfig

FAULTY_RECOMMENDATION = "Ingen rekommendation ges pga obalans i heterozygositet"


class PGxVariant(Model):
    """Detected PGx variant with percent frequency and duplication assessment."""

    gene: str
    rsid: str
    haplotypes: str
    position: str
    zygosity: str | None
    frequency_percent: float = Field(ge=0, le=100)
    possible_duplication: bool


class Recommendation(Model):
    """A supplied guideline selected or suppressed by existing PGx report rules."""

    gene: str
    haplotypes: str
    text: str


class LowDepthTarget(Model):
    """Target below the configured read-depth threshold."""

    rsid: str
    haplotypes: str
    position: str
    depth: float = Field(ge=0)


class PGxContent(PreparedContent):
    """Prepared PGx report data, also constructible from existing TSV inputs."""

    variants: list[PGxVariant] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    low_depth_targets: list[LowDepthTarget] = Field(default_factory=list)
    read_depth_threshold: int = Field(default=100, ge=0)
    targets: list[dict[str, str]] = Field(default_factory=list)
    genes: list[str] = Field(default_factory=list)


class PGxData(PGxContent, PreparedData):
    """PGx content with shared Python document inputs."""


class PGxFiles(Model):
    """Explicit local TSV inputs; no implicit discovery or output side effects."""

    detected_variants: Path
    haplotype_definitions: Path
    possible_diplotypes: Path
    possible_interactions: Path
    missing_annotated_depth: Path
    target_rsids: Path


def read_tsv(path: Path, required: set[str]) -> list[dict[str, str]]:
    """Read a UTF-8 table and fail on missing columns or malformed rows."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path.name}: missing required columns {sorted(required)}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"{path.name}: malformed TSV row")
    return rows


class PGxInputParser:
    """Prepare existing PGxModule inputs without importing its workflow dependencies."""

    def parse(self, inputs: PGxFiles, context: PGxData) -> PGxData:
        """Apply existing frequency/duplication, recommendation and depth handling."""
        definitions = read_tsv(inputs.haplotype_definitions, {"ID", "HAPLOTYPE"})
        haplotypes: dict[str, list[str]] = {}
        for row in definitions:
            haplotypes.setdefault(row["ID"], []).append(row["HAPLOTYPE"])
        variants = []
        faulty = set()
        for row in read_tsv(inputs.detected_variants, {"GENE", "ID", "#CHROM", "POS", "GT", "AD"}):
            depths = row["AD"].split(",")
            if len(depths) != 2:
                raise ValueError("PGx report inputs require biallelic AD values")
            ref, alt = (int(value) for value in depths)
            if min(ref, alt) < 0 or ref + alt == 0:
                raise ValueError("PGx allele depths must be nonnegative with a positive total")
            frequency = alt / (ref + alt)
            if frequency == 0:
                continue
            duplication = min(abs(frequency - p) for p in (1 / 4, 1 / 3, 2 / 3, 3 / 4)) <= min(
                abs(frequency - p) for p in (0, 1 / 2, 1)
            )
            names = haplotypes.get(row["ID"], [])
            if duplication:
                faulty.update(names)
            variants.append(
                PGxVariant(
                    gene=row["GENE"],
                    rsid=row["ID"],
                    haplotypes="/".join(names),
                    position=f"{row['#CHROM']}:{row['POS']}",
                    zygosity=(
                        "Homo"
                        if row["GT"] in {"0/0", "1/1"}
                        else "Hetero"
                        if row["GT"] in {"1/0", "0/1"}
                        else None
                    ),
                    frequency_percent=round(frequency * 100, 2),
                    possible_duplication=duplication,
                )
            )
        recommendations = []
        for row in read_tsv(
            inputs.possible_diplotypes,
            {"gene", "Haplotype1", "Haplotype2", "Guideline", "Activity"},
        ):
            if row["gene"] == "DPYD":
                recommendations.append(
                    Recommendation(
                        gene="DPYD",
                        haplotypes=f"{row['Haplotype1']}/{row['Haplotype2']}",
                        text=FAULTY_RECOMMENDATION
                        if faulty.intersection((row["Haplotype1"], row["Haplotype2"]))
                        else row["Guideline"],
                    )
                )
        for row in read_tsv(inputs.possible_interactions, {"haplotypes", "Guideline"}):
            names = row["haplotypes"].split(",")
            grouped = [
                "/".join(name for name in names if gene in name) for gene in ("TPMT", "NUDT15")
            ]
            recommendations.append(
                Recommendation(
                    gene="TPMT-NUDT15",
                    haplotypes=",".join(grouped),
                    text=FAULTY_RECOMMENDATION
                    if any(name and re.search(name, row["haplotypes"]) for name in faulty)
                    else row["Guideline"],
                )
            )
        low_depth = []
        for row in read_tsv(inputs.missing_annotated_depth, {"ID", "Locus", "Total_Depth"}):
            depth = float(row["Total_Depth"])
            if depth < 0 or depth != depth or depth == float("inf"):
                raise ValueError("Read depth must be finite and nonnegative")
            if depth < context.read_depth_threshold:
                low_depth.append(
                    LowDepthTarget(
                        rsid=row["ID"],
                        haplotypes="/".join(haplotypes.get(row["ID"], [])),
                        position=row["Locus"],
                        depth=depth,
                    )
                )
        # PGxModule reads this as a headered five-column table, then renames the columns.
        genes = set()
        with inputs.target_rsids.open(encoding="utf-8") as stream:
            reader = csv.reader(stream, delimiter="\t")
            header = next(reader, [])
            if len(header) != 5:
                raise ValueError("target_rsids requires a header with five columns")
            for row in reader:
                if len(row) != 5:
                    raise ValueError("target_rsids requires five columns")
                genes.add(row[4])
        values = context.model_dump()
        values.update(
            variants=[item.model_dump() for item in variants],
            recommendations=[item.model_dump() for item in recommendations],
            low_depth_targets=[item.model_dump() for item in low_depth],
            genes=sorted(genes),
            targets=[
                {"rsid": key, "haplotypes": "/".join(dict.fromkeys(haplotypes[key]))}
                for key in sorted(haplotypes)
            ],
        )
        return PGxData.model_validate(values)


class PGxReport(PreparedReport):
    """Build PGx reports from prepared data or explicit existing-format input files."""

    application = "pgx"

    def __init__(self, data: PGxData, config: ReportConfig):
        super().__init__(data, config)

    @classmethod
    def from_files(cls, inputs: PGxFiles, *, data: PGxData, config: ReportConfig):
        """Parse report inputs without writing intermediate files or artifacts."""
        return cls(PGxInputParser().parse(inputs, data), config)

    def build(self):
        document = super().build()
        tables = [
            (
                "pgx-recommendations",
                "Kliniska rekommendationer",
                self.data.recommendations,
                [("gene", "Gen"), ("haplotypes", "Haplotyp"), ("text", "Klinisk rekommendation")],
                "Inga detekterade varianter/rekommendationer",
            ),
            (
                "pgx-variants",
                "Kliniskt relevanta varianter",
                self.data.variants,
                [
                    ("gene", "Gen"),
                    ("rsid", "rsID"),
                    ("haplotypes", "Möjliga haplotyper"),
                    ("position", "Position"),
                    ("zygosity", "Zygositet"),
                    ("frequency_percent", "Variantfrekvens (%)"),
                    ("possible_duplication", "Möjlig duplikation"),
                ],
                "Inga detekterade varianter",
            ),
            (
                "pgx-depth",
                "Mål med lågt läsdjup",
                self.data.low_depth_targets,
                [
                    ("rsid", "rsID"),
                    ("haplotypes", "Haplotyp"),
                    ("position", "Position"),
                    ("depth", "Läsdjup"),
                ],
                f"Alla analyserade regioner har läsdjup ≥ {self.data.read_depth_threshold}x "
                "(PGX_QC_PASS)",
            ),
        ]
        sections = [
            TableSection(
                key=key,
                title=title,
                columns=[Column(key=k, label=v) for k, v in columns],
                rows=[item.model_dump() for item in rows],
                empty_text=empty,
                page_break_before=key == "pgx-variants",
            )
            for key, title, rows, columns, empty in tables
        ]
        if self.data.genes:
            sections.append(
                TableSection(
                    key="pgx-genes",
                    title="Gener som ingår i PGx-analysen",
                    columns=[Column(key="gene", label="Gen")],
                    rows=[{"gene": gene} for gene in self.data.genes],
                )
            )
        if self.data.targets:
            sections.append(
                TableSection(
                    key="pgx-targets",
                    title="Varianter som ingår i PGx-analysen",
                    columns=[
                        Column(key="rsid", label="rsID"),
                        Column(key="haplotypes", label="Haplotyp"),
                    ],
                    rows=self.data.targets,
                )
            )
        for section in sections:
            localize_table(section, self.config.language)
            if section.key == "pgx-depth" and self.config.language == "en":
                section.empty_text = (
                    f"All analyzed regions have read depth ≥ {self.data.read_depth_threshold}x "
                    "(PGX_QC_PASS)"
                )
        document.sections = sections + document.sections
        return document
