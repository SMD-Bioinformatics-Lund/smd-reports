"""Validate, normalize and render report JSON from the command line."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .loading import APPLICATIONS, ReportAssetError, ReportLoader
from .rendering import PDFUnavailableError, ReportRenderer


def main(argv=None) -> int:
    """Run a JSON validation, normalization, schema, or rendering command.

    Args:
        argv: Command arguments, excluding the executable name. None reads sys.argv.

    Returns:
        Zero on success, or two for invalid input, assets, or output locations.
    """
    parser = argparse.ArgumentParser(prog="smd-reports", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    schema = commands.add_parser("schema", help="Export a report JSON Schema")
    schema.add_argument("--application", choices=APPLICATIONS)
    schema.add_argument("--output", type=Path, required=True)
    for name in ("validate", "normalize", "render"):
        command = commands.add_parser(name)
        command.add_argument("input", type=Path)
        if name != "validate":
            command.add_argument("--output", type=Path, required=True)
        if name == "render":
            command.add_argument("--format", choices=("html", "pdf"), required=True)
    args = parser.parse_args(argv)
    loader = ReportLoader()
    try:
        if args.command == "schema":
            output = json.dumps(loader.schema(args.application), ensure_ascii=False, indent=2)
        else:
            if hasattr(args, "output") and args.output.resolve() == args.input.resolve():
                raise ValueError("Output must not overwrite input JSON")
            report = loader.load(args.input)
            if args.command == "validate":
                print(f"Valid {report.application} report ({report.language})")
                return 0
            if args.command == "normalize":
                output = report.model_dump_json(indent=2)
            else:
                renderer = ReportRenderer()
                output = (
                    renderer.render_html(report)
                    if args.format == "html"
                    else renderer.render_pdf(report)
                )
        if isinstance(output, bytes):
            args.output.write_bytes(output)
        else:
            args.output.write_text(output, encoding="utf-8")
        print(f"Written {args.output}")
        return 0
    except ValidationError as exc:
        fields = [
            ".".join(str(part) for part in error["loc"]) + ": " + error["type"]
            for error in exc.errors(include_input=False, include_url=False)
        ]
        print("Invalid report: " + "; ".join(fields), file=sys.stderr)
    except ReportAssetError as exc:
        print(str(exc), file=sys.stderr)
    except (OSError, ValueError, PDFUnavailableError) as exc:
        # Exception text may contain source data or private paths; report only its category.
        print(
            f"Report command failed ({type(exc).__name__}); check input, assets and "
            "output location. PDF output requires smd-reports[pdf].",
            file=sys.stderr,
        )
    return 2
