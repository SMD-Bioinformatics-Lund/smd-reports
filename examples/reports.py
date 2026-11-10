"""Render the supplied JSON examples without any application code."""

import argparse
from pathlib import Path

from smd_reports import ReportLoader, ReportRenderer


def main():
    """Render the packaged JSON examples into a chosen output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/examples"))
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--previews", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).parent / "inputs"
    sources = (
        {
            "generic": "generic",
            "custom": "custom",
            "coyote3": "coyote3-dna",
            "genexus": "genexus-en",
            "cll-genie": "cll-genie-positive",
            "pgx": "pgx",
        }
        if args.previews
        else {path.stem: path.stem for path in sorted(root.glob("*.json"))}
    )
    renderer = ReportRenderer()
    for name, source in sources.items():
        report = ReportLoader().load(root / f"{source}.json")
        args.output.joinpath(name + ".html").write_text(
            renderer.render_html(report) + "\n", encoding="utf-8"
        )
        if args.pdf:
            args.output.joinpath(name + ".pdf").write_bytes(renderer.render_pdf(report))
        print(name)


if __name__ == "__main__":
    main()
