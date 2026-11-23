"""Render the supplied JSON examples without any application code."""

import argparse
from pathlib import Path

from smd_reports import ReportLoader, ReportRenderer


def main():
    """Render the packaged JSON examples into a chosen output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/examples"))
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument(
        "--previews", action="store_true", help="Keep established names for primary previews."
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).parent / "inputs"
    preview_names = {
        "coyote3-dna": "coyote3",
        "coyote4-dna": "coyote4",
        "genexus-en": "genexus",
        "genexus": "genexus-sv",
        "cll-genie-positive": "cll-genie",
    }
    renderer = ReportRenderer()
    for source in sorted(root.glob("*.json")):
        name = preview_names.get(source.stem, source.stem) if args.previews else source.stem
        report = ReportLoader().load(source)
        args.output.joinpath(name + ".html").write_text(
            renderer.render_html(report) + "\n", encoding="utf-8"
        )
        if args.pdf:
            args.output.joinpath(name + ".pdf").write_bytes(renderer.render_pdf(report))
        print(name)


if __name__ == "__main__":
    main()
