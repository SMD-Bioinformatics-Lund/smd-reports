"""Validate, normalize and render report JSON from the command line."""

import argparse
import json
import logging
import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from .errors import ReportInputError, ReportRenderError, format_validation_error
from .loading import APPLICATIONS, ReportLoader
from .rendering import ReportRenderer


@contextmanager
def _event_logging(enabled):
    """Temporarily send package events to stderr when requested.

    Args:
        enabled: Whether the command was invoked with --verbose.

    Yields:
        Control to the command without changing application logging permanently.
    """
    logger = logging.getLogger("smd_reports")
    if not enabled:
        yield
        return
    level, propagate = logger.level, logger.propagate
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(level)
        logger.propagate = propagate


def _write_output(path: Path, output: str | bytes) -> None:
    """Replace output only after a complete write succeeds.

    Args:
        path: Destination whose parent directory must exist.
        output: Complete HTML, PDF, JSON or JSON Schema output.

    Raises:
        OSError: The destination cannot be written or replaced.
    """
    path = path.resolve()
    with TemporaryDirectory(prefix=".smd-reports-", dir=path.parent) as directory:
        temporary = Path(directory) / "output"
        if isinstance(output, bytes):
            temporary.write_bytes(output)
        else:
            temporary.write_text(output, encoding="utf-8")
        if path.exists():
            temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    logging.getLogger(__name__).info("Report output written")


def _run(args) -> int:
    """Execute a parsed command and report recoverable failures.

    Args:
        args: Parsed command-line options.

    Returns:
        Zero on success, two for input/setup errors, or one for rendering failures.
    """
    loader = ReportLoader()
    operation = "read the input JSON file"
    try:
        if args.command == "schema":
            output = json.dumps(loader.schema(args.application), ensure_ascii=False, indent=2)
        else:
            if hasattr(args, "output") and (
                args.output.resolve() == args.input.resolve()
                or (
                    args.output.exists()
                    and args.input.exists()
                    and args.output.samefile(args.input)
                )
            ):
                raise ReportInputError("Output must not overwrite input JSON; choose another file.")
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
        operation = "write the output file"
        _write_output(args.output, output)
        print(f"Written {args.output}")
        return 0
    except ValidationError as exc:
        message = format_validation_error(exc)
    except json.JSONDecodeError as exc:
        message = f"Invalid JSON at line {exc.lineno}, column {exc.colno}; check the JSON syntax."
    except UnicodeError:
        message = "Cannot decode input JSON; save the file with UTF-8 encoding."
    except ReportInputError as exc:
        message = str(exc)
    except ReportRenderError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except FileNotFoundError:
        message = f"Cannot {operation}: file or parent directory not found."
    except PermissionError:
        message = f"Cannot {operation}: permission denied. Check file and directory permissions."
    except IsADirectoryError:
        message = f"Cannot {operation}: the selected path is a directory; choose a file."
    except OSError:
        message = f"Cannot {operation}: filesystem error. Check the location and available space."
    except Exception:
        logging.getLogger(__name__).error("Report command failed unexpectedly")
        print(
            "Report command failed unexpectedly; check the installation and report format.",
            file=sys.stderr,
        )
        return 1
    print(message, file=sys.stderr)
    return 2


def main(argv=None) -> int:
    """Run a JSON validation, normalization, schema, or rendering command.

    Args:
        argv: Command arguments, excluding the executable name. None reads sys.argv.

    Returns:
        Zero on success, two for input/setup errors, or one for rendering failures.
    """
    parser = argparse.ArgumentParser(prog="smd-reports", description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Log main events to stderr")
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
    with _event_logging(args.verbose):
        return _run(args)
