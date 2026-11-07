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
            for analysis in english["data"]["analyses"]:
                for section in analysis["sections"]:
                    section["title"] = {
                        "snvs": "Clinically relevant SNVs and small INDELs",
                        "fusions": "Fusions",
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
                        }[column["key"]]
            (args.output / "genexus-en.json").write_text(
                json.dumps(english, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
