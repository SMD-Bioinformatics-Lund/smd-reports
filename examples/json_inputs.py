"""Create application JSON examples from the same synthetic Python builder inputs."""

import argparse
import json
import os
from pathlib import Path

from reports import demo_reports


def main():
    """Generate portable JSON inputs with logo paths relative to each JSON file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("examples/inputs"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, builder in demo_reports().items():
        raw = builder.data.model_dump(mode="json")
        branding = raw.pop("branding")
        logos = {
            "center_logo": "center-example.svg",
            "accreditation_logo": "accreditation-example.svg",
        }
        if builder.application in {"coyote3", "cll_genie"}:
            logos["application_logo"] = "application-example.svg"
        for key, filename in logos.items():
            asset = Path(__file__).parent / "assets" / filename
            branding[key] = os.path.relpath(asset.resolve(), args.output.resolve())
        config = builder.config.model_dump()
        envelope = {
            "schema_version": 1,
            "application": builder.application,
            "title": config.pop("title"),
            "language": config.pop("language"),
            "report": raw.pop("metadata"),
            "branding": branding,
            "provenance": raw.pop("provenance"),
            "presentation": config,
            "data": raw,
        }
        (args.output / f"{name}.json").write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if name == "genexus":
            english = json.loads(json.dumps(envelope))
            english.update(language="en", title="NGS Analysis Report")
            english["data"].update(
                summary="Reviewed synthetic conclusion. For demonstration only.",
                description="Synthetic analysis description supplied by the application.",
            )
            labels = {
                "Patientnamn": "Patient name",
                "Personnummer": "Personal identity number",
                "Provtyp": "Sample type",
                "Registreringsdatum": "Registration date",
                "Frågeställning": "Clinical question",
                "Analysmetod": "Analysis method",
                "Analys genomförd av": "Analysis performed by",
            }
            for field in english["report"]["fields"]:
                field["label"] = labels[field["label"]]
                if field["label"] == "Sample type":
                    field["value"] = "Synthetic sample"
            english["data"]["run"][0]["label"] = "Run"
            for analysis in english["data"]["analyses"]:
                for section in analysis["sections"]:
                    section["title"] = {
                        "snvs": "Clinically relevant SNVs and small INDELs",
                        "fusions": "Fusions",
                        "cnvs": "Copy-number alterations",
                        "others": "Other clinically relevant findings",
                    }[section["key"]]
                    section["empty_text"] = "No reportable results"
                    for column in section["columns"]:
                        column["label"] = {
                            "gene": "Gene",
                            "variant": "HGVS",
                            "af": "VAF",
                            "tier": "Tier",
                            "fusion": "Fusion",
                            "chromosome": "Chromosome",
                            "exon": "Exon",
                            "classification": "Classification",
                            "copy": "Copy number",
                            "hgvs_p": "HGVS protein",
                            "vaf": "VAF (%)",
                            "hotspot": "Hotspot",
                            "copy_number": "Copy number",
                            "genes_exons": "Genes (exons)",
                            "locus": "Locus",
                            "source_type": "Source type",
                            "source_class": "Variant class",
                        }[column["key"]]
            # Clinical text and labels are explicitly provided in the example adapter.
            detail_labels = {
                "Gen": "Gene",
                "Typ": "Type",
                "Transkript": "Transcript",
                "Konsekvens": "Consequence",
                "Kromosom": "Chromosome",
                "Klassificering": "Classification",
                "Kommentar": "Comment",
                "Kopietal": "Copy number",
                "Storlek": "Size",
                "Prober": "Probes",
                "5′ gen": "5′ gene",
                "3′ gen": "3′ gene",
                "Effekt": "Effect",
                "Förändring": "Change",
                "CNV-kvot": "CNV ratio",
                "Gener (exoner)": "Genes (exons)",
                "Oncomine-drivargen": "Oncomine driver gene",
                "Fusionstyp": "Fusion type",
                "Stödjande läsningar": "Supporting reads",
                "Unika molekyler": "Unique molecules",
                "Brytpunkt 5′": "5′ breakpoint",
                "Brytpunkt 3′": "3′ breakpoint",
                "Källtyp": "Source type",
                "Variantklass": "Variant class",
                "Obalansvärde": "Imbalance score",
                "P-värde för obalans": "Imbalance p-value",
                "Brytpunktsintervall": "Breakpoint range",
                "5′ brytpunkt": "5′ breakpoint",
                "3′ brytpunkt": "3′ breakpoint",
            }
            for analysis in english["data"]["analyses"]:
                for section in analysis["details"]:
                    section["title"] = {
                        "snv-details": "Detected mutations",
                        "cnv-details": "Detected copy-number alterations",
                        "fusion-details": "Detailed fusion results",
                        "other-details": "Details of other findings",
                    }[section["key"]]
                    for record in section["records"]:
                        for field in record["fields"]:
                            field["label"] = detail_labels.get(field["label"], field["label"])
            english["data"]["supporting_sections"][0]["title"] = "Analyzed genes"
            english["data"]["supporting_sections"][0]["columns"][0]["label"] = "Gene"
            english["data"]["supporting_sections"][1]["title"] = "Classification description"
            (args.output / "genexus-en.json").write_text(
                json.dumps(english, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
