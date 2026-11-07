"""Generate synthetic demonstrations without importing any clinical application."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from smd_reports import (
    Branding,
    CLLGenieData,
    CLLGenieReport,
    CLLSequence,
    Column,
    CoyoteData,
    CoyoteReport,
    FieldValue,
    GenexusData,
    GenexusReport,
    PGxData,
    PGxReport,
    ReportLoader,
    ReportMetadata,
    ReportRenderer,
    TableSection,
)
from smd_reports.plugins.pgx import LowDepthTarget, PGxVariant, Recommendation
from smd_reports.plugins.prepared import Analysis, ReportConfig


def metadata(report_id="DEMO-REPORT-001"):
    """Fixed timestamp and placeholder tokens make demonstrations reproducible."""
    return ReportMetadata(
        report_id=report_id,
        sample_id="SYNTHETIC-001",
        generated_at=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        author="Demo User",
        fields=[
            FieldValue(label="Patientnamn", value="<PATIENT_NAME>"),
            FieldValue(label="Personnummer", value="<PERSONAL_IDENTITY_NUMBER>"),
            FieldValue(label="Provtyp", value="Syntetiskt prov"),
            FieldValue(label="Registreringsdatum", value="<REGISTRATION_DATE>"),
            FieldValue(label="Frågeställning", value="Syntetisk analys"),
            FieldValue(label="Analysmetod", value="NGS - syntetisk demonstration"),
            FieldValue(label="Analys genomförd av", value="Example Diagnostics Center"),
        ],
    )


def table(key, title, labels, rows, **kwargs):
    """Create an explicitly declared presentation table."""
    return TableSection(
        key=key,
        title=title,
        columns=[Column(key=k, label=v) for k, v in labels],
        rows=rows,
        **kwargs,
    )


def demo_reports():
    """Cover four identities, Coyote RNA and both CLL Genie no-result cases."""
    brand = Branding.from_files(
        center_logo=Path(__file__).parent / "assets/center-example.svg",
        accreditation_logo=Path(__file__).parent / "assets/accreditation-example.svg",
        accredited=True,
        accreditation_label="Example accreditation placeholder",
        organization="Example Diagnostics Center",
        department="Molekylär diagnostik",
        address="Exempeladress 1",
        telephone="000-000000",
        email="demo@example.org",
    )
    snv = table(
        "snvs",
        "Kliniskt relevanta SNVs och små INDELs",
        [
            ("gene", "Gen"),
            ("chromosome", "Kromosom"),
            ("exon", "Exon"),
            ("variant", "HGVS"),
            ("af", "VAF"),
            ("tier", "Tier"),
            ("classification", "Klassificering"),
        ],
        [
            {
                "gene": "BRAF",
                "chromosome": "7",
                "exon": "15",
                "variant": "p.Val600Glu",
                "af": "24%",
                "tier": "I",
                "classification": "Tier I",
            }
        ],
        emphasis_column="classification",
        emphasis_value="Tier I",
    )
    cnv = table("cnvs", "Kopietalsförändringar", [("gene", "Gen"), ("copy", "Kopietal")], [])
    fusion = table(
        "fusions",
        "Fusioner",
        [("fusion", "Fusion"), ("tier", "Klassificering")],
        [{"fusion": "EML4::ALK", "tier": "Tier II"}],
    )
    biomarker = table(
        "biomarkers",
        "Kliniskt relevanta biomarkörer",
        [("marker", "Biomarkör"), ("value", "Resultat"), ("assigned", "Bedömning")],
        [{"marker": "TMB", "value": "12 mut/Mb", "assigned": "Hög"}],
    )
    common = dict(
        metadata=metadata(),
        branding=brand,
        description="Syntetisk analysbeskrivning. Inga kliniska beslut fattas här.",
        summary="Exempel på granskad slutsats. Endast för demonstration.",
    )
    coyote = CoyoteReport(
        CoyoteData(
            **common,
            analyte="dna",
            supported_analyses=["SNV", "CNV", "BIOMARKER", "FUSION"],
            enabled_analyses=["SNV", "CNV", "BIOMARKER"],
            analyses=[
                Analysis(
                    name="SNV",
                    parameters=[FieldValue(label="Referensgenom", value="GRCh38")],
                    sections=[snv],
                ),
                Analysis(name="CNV", sections=[cnv]),
                Analysis(name="BIOMARKER", sections=[biomarker]),
            ],
        ),
        ReportConfig(title="Molekylärgenetisk analysrapport"),
    )
    rna = CoyoteReport(
        CoyoteData(
            **common,
            analyte="rna",
            supported_analyses=["FUSION"],
            enabled_analyses=["FUSION"],
            analyses=[Analysis(name="FUSION", sections=[fusion])],
        ),
        ReportConfig(title="RNA-analysrapport"),
    )
    genexus = GenexusReport(
        GenexusData(
            **common,
            supported_analyses=["SNV", "FUSION"],
            enabled_analyses=["SNV", "FUSION"],
            analyses=[
                Analysis(name="SNV", sections=[snv]),
                Analysis(name="FUSION", sections=[fusion]),
            ],
            assay=[FieldValue(label="Assay", value="Demonstrationspanel")],
            run=[FieldValue(label="Körning", value="SYNTHETIC-RUN")],
        ),
        ReportConfig(title="NGS-analysrapport", header_height_mm=75),
    )
    cll = CLLGenieReport(
        CLLGenieData(
            **common,
            report_type="positive",
            submission_id="submission_demo",
            sequences=[
                CLLSequence(
                    sequence_id="Seq1",
                    length_nt=321,
                    identity_percent=97.5,
                    identity_nt="313/321",
                    identity_with_indels="97.2% (312/321)",
                    mutation_status="Borderline (granskad)",
                    productivity="Produktiv",
                    subset="#2",
                    details=[
                        FieldValue(label="V-GENE and allele", value="IGHV3-21*01"),
                        FieldValue(label="J-GENE and allele", value="IGHJ6*02"),
                        FieldValue(label="D-GENE and allele", value="IGHD3-3*01"),
                        FieldValue(label="AA JUNCTION", value="SYNTHETIC"),
                        FieldValue(label="JUNCTION-nt nb", value=42),
                        FieldValue(label="Total reads (%)", value=0),
                    ],
                )
            ],
        ),
        ReportConfig(title="IGHV-mutationsanalys"),
    )
    pgx = PGxReport(
        PGxData(
            **common,
            recommendations=[
                Recommendation(
                    gene="DPYD",
                    haplotypes="*1/*2A",
                    text="Syntetisk rekommendation - ej för kliniskt bruk.",
                )
            ],
            variants=[
                PGxVariant(
                    gene="DPYD",
                    rsid="rsDEMO",
                    haplotypes="DPYD-*2A",
                    position="1:100",
                    zygosity="Hetero",
                    frequency_percent=50,
                    possible_duplication=False,
                )
            ],
            low_depth_targets=[
                LowDepthTarget(rsid="rsLOW", haplotypes="DEMO", position="1:200", depth=72)
            ],
            genes=["DPYD", "TPMT", "NUDT15"],
        ),
        ReportConfig(title="Farmakogenetisk analysrapport"),
    )
    reports = {
        "coyote3-dna": coyote,
        "coyote3-rna": rna,
        "genexus": genexus,
        "cll-genie-positive": cll,
        "pgx": pgx,
    }
    for kind in ("nonfunctional", "no_clone"):
        reports[f"cll-genie-{kind}"] = CLLGenieReport(
            CLLGenieData(**common, report_type=kind),
            ReportConfig(title="IGHV-mutationsanalys"),
        )
    from smd_reports.assets import embed_image

    logos = {"coyote3": "application-example.svg", "cll_genie": "application-example.svg"}
    for builder in reports.values():
        if builder.application in logos:
            builder.data.branding.application_logo = embed_image(
                Path(__file__).parent / "assets" / logos[builder.application]
            )
    return reports


def main():
    """Write examples to an explicitly selected local output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/examples"))
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument(
        "--previews",
        action="store_true",
        help="Generate the four curated previews from application JSON inputs",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.previews:
        sources = {
            "coyote3": "coyote3-dna",
            "genexus": "genexus-en",
            "cll-genie": "cll-genie-positive",
            "pgx": "pgx",
        }
        renderer = ReportRenderer()
        for name, source in sources.items():
            report = ReportLoader().load(Path(__file__).parent / "inputs" / f"{source}.json")
            args.output.joinpath(name + ".html").write_text(
                renderer.render_html(report),
                encoding="utf-8",
            )
            if args.pdf:
                args.output.joinpath(name + ".pdf").write_bytes(renderer.render_pdf(report))
            print(name)
        return
    for name, report in demo_reports().items():
        args.output.joinpath(name + ".html").write_text(report.render_html(), encoding="utf-8")
        args.output.joinpath(name + ".json").write_text(
            report.build().model_dump_json(indent=2),
            encoding="utf-8",
        )
        if args.pdf:
            args.output.joinpath(name + ".pdf").write_bytes(report.render_pdf())
        print(name)


if __name__ == "__main__":
    main()
