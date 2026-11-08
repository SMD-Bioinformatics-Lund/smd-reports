"""Render PDF pages as images and compare them with a saved baseline."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import pymupdf


def capture(source: Path, output: Path) -> dict:
    """Render PDF pages as images and record page sizes and library versions.

    Args:
        source: Directory containing the PDF files to inspect.
        output: Directory receiving PNG pages and a manifest.

    Returns:
        A manifest of rendering versions, page sizes, and pixel hashes.

    Raises:
        ValueError: The source directory contains no PDFs.
    """
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "reports": {},
    }
    for package in ("smd-reports", "weasyprint", "PyMuPDF"):
        try:
            manifest["environment"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            manifest["environment"][package] = "source checkout"
    from importlib.resources import files

    from weasyprint.text.ffi import pango

    manifest["environment"]["pango"] = pango.pango_version()
    manifest["environment"]["font_sha256"] = hashlib.sha256(
        files("smd_reports").joinpath("static/fonts.css").read_bytes()
    ).hexdigest()
    for path in sorted(source.glob("*.pdf")):
        pages = []
        with pymupdf.open(path) as document:
            for index, page in enumerate(document):
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                pixmap.save(output / f"{path.stem}-{index + 1}.png")
                pages.append(
                    {
                        "size": [pixmap.width, pixmap.height],
                        "sha256": hashlib.sha256(pixmap.samples).hexdigest(),
                    }
                )
        manifest["reports"][path.name] = pages
    if not manifest["reports"]:
        raise ValueError("No PDFs found in the source directory")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    """Generate report images and compare them with a baseline when provided."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/visual"))
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    result = capture(args.source, args.output)
    if args.baseline:
        baseline = json.loads((args.baseline / "manifest.json").read_text())
        if baseline != result:
            raise SystemExit("Report images or rendering environment differ from the baseline")
    print(f"Captured {len(result['reports'])} reports in {args.output}")


if __name__ == "__main__":
    main()
