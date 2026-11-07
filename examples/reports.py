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
    DetailField,
    DetailRecord,
    DetailSection,
    FieldValue,
    GenexusData,
    GenexusReport,
    PGxData,
    PGxReport,
    ReportLoader,
    ReportMetadata,
    ReportRenderer,
    TableSection,
    TextSection,
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


def finding(key, title, fields, comment):
    """Prepared facts and text; no classification or interpretation rules."""
    return DetailSection(
        key=key,
        title=title,
        records=[
            DetailRecord(
                key=key + "-1",
                title=title,
                fields=[
                    *[DetailField(label=label, value=value) for label, value in fields],
                    DetailField(
                        label="Klassificering",
                        value="Reviewed example",
                        full_width=True,
                        emphasis=True,
                    ),
                    DetailField(
                        label="Kommentar", value=comment, full_width=True, format="markdown"
                    ),
                ],
            )
        ],
    )


def genexus_analyses():
    """Mirror the source Genexus report configuration using synthetic prepared data."""

    def card(key, title, fields, full_width=False):
        return DetailRecord(
            key=key,
            title=title,
            fields=[
                DetailField(
                    label=label, value=value, full_width=full_width and label == "Klassificering"
                )
                for label, value in fields
            ],
        )

    mutation_fields = [
        ("Gen", "BRAF"),
        ("Typ", "SNV"),
        ("Transcript", "NM_004333.6"),
        ("Consequence", "missense_variant"),
        ("HGVS cDNA", "c.1799T>A"),
        ("HGVS protein", "p.Val600Glu"),
        ("Chromosome", "7"),
        ("Position", 140753336),
        ("VAF (%)", 24),
        ("Hotspot", True),
        ("Klassificering", "Reviewed synthetic classification"),
    ]
    indel_fields = [
        ("Gen", "EXAMPLE2"),
        ("Typ", "INDEL"),
        ("Transcript", "DEMO_TRANSCRIPT"),
        ("Consequence", "inframe_deletion"),
        ("HGVS cDNA", "c.100_102del"),
        ("HGVS protein", "p.(Example34del)"),
        ("Chromosome", "1"),
        ("Position", 100100),
        ("VAF (%)", 18),
        ("Hotspot", False),
        ("Klassificering", "Reviewed synthetic classification"),
    ]
    return [
        Analysis(
            name="SNV",
            sections=[
                table(
                    "snvs",
                    "Kliniskt relevanta SNVs och små INDELs",
                    [
                        ("gene", "Gen"),
                        ("hgvs_p", "HGVS protein"),
                        ("vaf", "VAF (%)"),
                        ("hotspot", "Hotspot"),
                        ("classification", "Klassificering"),
                    ],
                    [
                        {
                            "gene": "BRAF",
                            "hgvs_p": "p.Val600Glu",
                            "vaf": 24,
                            "hotspot": True,
                            "classification": "Reviewed synthetic classification",
                        },
                        {
                            "gene": "EXAMPLE2",
                            "hgvs_p": "p.(Example34del)",
                            "vaf": 18,
                            "hotspot": False,
                            "classification": "Reviewed synthetic classification",
                        },
                    ],
                )
            ],
            details=[
                DetailSection(
                    key="snv-details",
                    title="Detekterade mutationer",
                    records=[
                        card("braf", "BRAF: p.Val600Glu", mutation_fields),
                        card("indel", "EXAMPLE2: p.(Example34del)", indel_fields),
                    ],
                )
            ],
        ),
        Analysis(
            name="CNV",
            sections=[
                table(
                    "cnvs",
                    "Kliniskt relevanta kopietalsförändringar",
                    [
                        ("gene", "Gen"),
                        ("copy_number", "Kopietal"),
                        ("classification", "Klassificering"),
                    ],
                    [
                        {
                            "gene": "EXAMPLE1",
                            "copy_number": 6,
                            "classification": "Reviewed synthetic classification",
                        }
                    ],
                )
            ],
            details=[
                DetailSection(
                    key="cnv-details",
                    title="Detekterade kopietalsförändringar",
                    records=[
                        card(
                            "cnv-1",
                            "EXAMPLE1",
                            [
                                ("Gen", "EXAMPLE1"),
                                ("Förändring", "Gain"),
                                ("Kopietal", 6),
                                ("CNV-kvot", 3.1),
                                ("Locus", "chr1:100000-200000"),
                                ("Klassificering", "Reviewed synthetic classification"),
                            ],
                            full_width=True,
                        )
                    ],
                )
            ],
        ),
        Analysis(
            name="FUSION",
            sections=[
                table(
                    "fusions",
                    "Detekterade fusioner",
                    [
                        ("genes_exons", "Gener (exoner)"),
                        ("locus", "Locus"),
                        ("classification", "Klassificering"),
                    ],
                    [
                        {
                            "genes_exons": "EML4(13)::ALK(20)",
                            "locus": "chr2:42400000;chr2:29400000",
                            "classification": "Reviewed synthetic classification",
                        }
                    ],
                )
            ],
            details=[
                DetailSection(
                    key="fusion-details",
                    title="Detaljerade fusionsresultat",
                    records=[
                        card(
                            "fusion-1",
                            "EML4(13)::ALK(20)",
                            [
                                ("Variant-ID", "DEMO-FUSION-001"),
                                ("Gener (exoner)", "EML4(13)::ALK(20)"),
                                ("Locus", "chr2:42400000;chr2:29400000"),
                                ("Oncomine-drivargen", "ALK"),
                                ("Fusionstyp", "RNA fusion"),
                                ("Stödjande läsningar", 37),
                                ("Unika molekyler", 18),
                                ("Brytpunkt 5′", "chr2:42400000"),
                                ("Brytpunkt 3′", "chr2:29400000"),
                                ("Klassificering", "Reviewed synthetic classification"),
                            ],
                            full_width=True,
                        )
                    ],
                )
            ],
        ),
        Analysis(
            name="OTHER",
            sections=[
                table(
                    "others",
                    "Övriga kliniskt relevanta fynd",
                    [
                        ("gene", "Gen"),
                        ("source_type", "Källtyp"),
                        ("source_class", "Variantklass"),
                        ("classification", "Klassificering"),
                    ],
                    [
                        {
                            "gene": "EXAMPLE3",
                            "source_type": "Imbalance",
                            "source_class": "RNA",
                            "classification": "Reviewed synthetic classification",
                        }
                    ],
                )
            ],
            details=[
                DetailSection(
                    key="other-details",
                    title="Detaljer för övriga fynd",
                    records=[
                        card(
                            "other-1",
                            "EXAMPLE3: Imbalance",
                            [
                                ("Gen", "EXAMPLE3"),
                                ("Källtyp", "Imbalance"),
                                ("Variantklass", "RNA"),
                                ("Locus", "chr3:100000-200000"),
                                ("Obalansvärde", 2.1),
                                ("P-värde för obalans", 0.01),
                                ("Brytpunktsintervall", "100000-200000"),
                                ("Klassificering", "Reviewed synthetic classification"),
                            ],
                            full_width=True,
                        )
                    ],
                )
            ],
        ),
    ]


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
    cnv = table(
        "cnvs",
        "Kopietalsförändringar",
        [("gene", "Gen"), ("copy", "Kopietal")],
        [{"gene": "EXAMPLE1", "copy": 6}],
    )
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
    snv_detail = finding(
        "snv-details",
        "SNV / INDEL - BRAF p.Val600Glu",
        [
            ("Gen", "BRAF"),
            ("Typ", "SNV"),
            ("Transkript", "NM_004333.6"),
            ("Konsekvens", "missense_variant"),
            ("cDNA", "c.1799T>A"),
            ("Protein", "p.Val600Glu"),
            ("Kromosom", "7"),
            ("Position", "140753336"),
            ("VAF", "24%"),
            ("Exon", "15"),
        ],
        "**Synthetic example.** Interpretation supplied and reviewed by the application.",
    )
    cnv_detail = finding(
        "cnv-details",
        "CNV - EXAMPLE1",
        [
            ("Gen", "EXAMPLE1"),
            ("Region", "chr1:100000-200000"),
            ("Typ", "Gain"),
            ("Kopietal", 6),
            ("Storlek", "100 kb"),
            ("Prober", 42),
            ("PR", 25),
            ("SR", 12),
        ],
        "Synthetic copy-number finding; supplied description and classification.",
    )
    fusion_detail = finding(
        "fusion-details",
        "Fusion - EML4::ALK",
        [
            ("5′ gen", "EML4"),
            ("3′ gen", "ALK"),
            ("Effekt", "In-frame"),
            ("5′ brytpunkt", "chr2:42400000"),
            ("3′ brytpunkt", "chr2:29400000"),
            ("Split reads", 37),
            ("Spanning pairs", 18),
            ("Anchor", 64),
        ],
        "Synthetic fusion. All breakpoints, evidence and text are application inputs.",
    )
    biomarker_detail = DetailSection(
        key="biomarker-details",
        title="Biomarkördetaljer",
        records=[
            DetailRecord(
                key="tmb",
                title="TMB",
                fields=[
                    DetailField(label="Resultat", value="12 mut/Mb"),
                    DetailField(label="Bedömning", value="Hög"),
                ],
            ),
            DetailRecord(
                key="msi",
                title="MSI",
                fields=[
                    DetailField(label="Instabila markörer", value=0),
                    DetailField(label="Analyserade markörer", value=100),
                    DetailField(label="Resultat", value="0%"),
                ],
            ),
            DetailRecord(
                key="hrd",
                title="HRD",
                fields=[
                    DetailField(label="Summa", value=25),
                    DetailField(label="TAI", value=8),
                    DetailField(label="LST", value=9),
                    DetailField(label="LOH", value=8),
                ],
            ),
        ],
    )
    common = dict(
        metadata=metadata(),
        branding=brand,
        description="Syntetisk analysbeskrivning. Inga kliniska beslut fattas här.",
        summary="Exempel på granskad slutsats. Endast för demonstration.",
        supporting_sections=[
            table(
                "covered-genes",
                "Analyserade gener",
                [("gene", "Gen")],
                [{"gene": gene} for gene in ["BRAF", "EML4", "ALK", "EXAMPLE1"]],
            ),
            TextSection(
                key="classification-description",
                title="Klassificeringsbeskrivning",
                text="Synthetic classification description supplied by the application.",
            ),
        ],
        references="Example reference supplied by the application; demonstration only.",
    )
    coyote = CoyoteReport(
        CoyoteData(
            **common,
            analyte="dna",
            supported_analyses=["SNV", "CNV", "BIOMARKER", "TRANSLOCATION", "FUSION"],
            enabled_analyses=["SNV", "CNV", "BIOMARKER", "TRANSLOCATION"],
            analyses=[
                Analysis(
                    name="SNV",
                    parameters=[FieldValue(label="Referensgenom", value="GRCh38")],
                    sections=[snv],
                    details=[snv_detail],
                ),
                Analysis(name="CNV", sections=[cnv], details=[cnv_detail]),
                Analysis(name="BIOMARKER", sections=[biomarker], details=[biomarker_detail]),
                Analysis(
                    name="TRANSLOCATION",
                    sections=[
                        fusion.model_copy(
                            update={"key": "translocations", "title": "Translokationer"}
                        )
                    ],
                    details=[fusion_detail.model_copy(update={"key": "translocation-details"})],
                ),
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
            analyses=[Analysis(name="FUSION", sections=[fusion], details=[fusion_detail])],
        ),
        ReportConfig(title="RNA-analysrapport"),
    )
    genexus = GenexusReport(
        GenexusData(
            **common,
            supported_analyses=["SNV", "CNV", "FUSION", "OTHER"],
            enabled_analyses=["SNV", "CNV", "FUSION", "OTHER"],
            analyses=genexus_analyses(),
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
                    analysis_category="Single productive rearrangement (synthetic)",
                    indel_summary="Synthetic insertion/deletion description supplied by CLL Genie.",
                    functionality_label="V-Domain functionality after removal of Indels",
                    functionality_comment="Reviewed synthetic result supplied by CLL Genie.",
                    v_gene="IGHV3-21*01",
                    v_score=1500,
                    j_gene="IGHJ6*02",
                    j_score=230,
                    j_identity_percent=100,
                    j_identity_nt="60/60",
                    d_gene="IGHD3-3*01",
                    d_reading_frame=2,
                    fr_lengths="[25.17.38.11]",
                    cdr_lengths="8.8.14",
                    aa_junction="SYNTHETIC",
                    junction_length_nt=42,
                    junction_decryption="DEMO-V {N1} DEMO-D {N2} DEMO-J",
                    junction_legend="(3′V)3′{N1}5′(D)3′{N2}5′(5′J)",
                    merge_count=1200,
                    total_reads_percent=0,
                    details=[FieldValue(label="JUNCTION-nt nb", value=42)],
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
            targets=[{"rsid": "rsDEMO", "haplotypes": "DPYD-*2A"}],
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
    for name, builder in reports.items():
        if builder.application == "cll_genie":
            builder.data.supporting_sections = []
        elif builder.application == "genexus":
            builder.data.supporting_sections[0].rows = [
                {"gene": gene}
                for gene in ["BRAF", "EXAMPLE1", "EXAMPLE2", "EXAMPLE3", "EML4", "ALK"]
            ]
        elif builder.application == "pgx":
            builder.data.supporting_sections = builder.data.supporting_sections[1:]
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
