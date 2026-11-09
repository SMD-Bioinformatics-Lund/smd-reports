"""Actionable failures, event logging and safe command-line output."""

import json
import logging
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import TemplateNotFound
from pydantic import ValidationError

from smd_reports import (
    PDFUnavailableError,
    ReportAssetError,
    ReportInputError,
    ReportLoader,
    ReportRenderer,
    ReportRenderError,
    format_validation_error,
)
from smd_reports.cli import main

PRIVATE = "PRIVATE-PATIENT-AND-PATH"


def test_import_and_default_logging_do_not_configure_application():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import logging
root = logging.getLogger()
root.setLevel(logging.DEBUG)
before = list(root.handlers)
import smd_reports
assert root.handlers == before
assert root.level == logging.DEBUG
assert all(isinstance(h, logging.NullHandler)
           for h in logging.getLogger('smd_reports').handlers)
try: smd_reports.ReportLoader().loads('invalid')
except ValueError: pass
""",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from smd_reports import ReportLoader
try: ReportLoader().loads('invalid')
except ValueError: pass
""",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == result.stderr == ""


def test_loading_and_html_events_exclude_report_data(payloads, load, caplog):
    data = payloads["generic"]
    data["title"] = PRIVATE
    with caplog.at_level(logging.INFO, logger="smd_reports"):
        report = load(data)
        assert PRIVATE in ReportRenderer().render_html(report)
    messages = caplog.text
    assert "Loading report JSON" in messages
    assert "Report loaded: preset=generic" in messages
    assert "Report HTML rendered" in messages
    assert PRIVATE not in messages and "data:image" not in messages
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize("failure", ["unknown-key", "unknown-kind", "wrong-type", "invalid-row"])
def test_validation_messages_exclude_values_and_unknown_keys(payloads, load, failure):
    data = payloads["generic"]
    if failure == "unknown-key":
        data[PRIVATE] = PRIVATE
    elif failure == "unknown-kind":
        data["sections"] = [{"kind": PRIVATE, "key": PRIVATE}]
    elif failure == "wrong-type":
        data["sections"] = PRIVATE
    else:
        data["sections"] = [
            {
                "kind": "table",
                "key": PRIVATE,
                "columns": {"en": [PRIVATE]},
                "rows": [[PRIVATE, PRIVATE]],
            }
        ]
    with pytest.raises(ValidationError) as caught:
        load(data)
    message = format_validation_error(caught.value)
    assert message.startswith("Invalid report: ")
    assert PRIVATE not in message
    expected = {
        "unknown-key": "Unknown field",
        "unknown-kind": "Unknown section kind",
        "wrong-type": "Expected a JSON array",
        "invalid-row": "exactly one value",
    }
    assert expected[failure] in message


def test_many_validation_errors_are_bounded():
    with pytest.raises(ValidationError) as caught:
        ReportLoader().loads(json.dumps({f"{PRIVATE}-{index}": PRIVATE for index in range(20)}))
    message = format_validation_error(caught.value)
    assert "additional validation errors" in message
    assert message.count("Unknown field") <= 10
    assert PRIVATE not in message


@pytest.mark.parametrize("kind", ["image", "inline"])
def test_asset_errors_use_json_indexes_not_user_keys(tmp_path, payloads, caplog, kind):
    data = payloads["generic"]
    data["branding"] = {}
    image = {"source": str(tmp_path / PRIVATE / "missing.png")}
    section = {"kind": "text", "key": PRIVATE, "text": PRIVATE, "images": [image]}
    if kind == "image":
        section = {"kind": "image", "key": PRIVATE, **image}
    data["sections"] = [section]
    with caplog.at_level(logging.INFO, logger="smd_reports"):
        with pytest.raises(ReportAssetError) as caught:
            ReportLoader().loads(json.dumps(data))
    expected = "sections[0].source" if kind == "image" else "sections[0].images[0].source"
    assert caught.value.field == expected
    assert "Image file not found" in str(caught.value)
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert PRIVATE not in str(caught.value) + caplog.text


def test_relative_asset_explains_base_directory(payloads):
    data = payloads["generic"]
    with pytest.raises(ReportAssetError, match="Relative image paths require base_dir"):
        ReportLoader().loads(json.dumps(data))


@pytest.mark.parametrize("failure", [TemplateNotFound, RuntimeError])
def test_html_template_failure_has_safe_error_and_original_cause(
    reports, monkeypatch, caplog, failure
):
    renderer = ReportRenderer()

    def fail(*args):
        raise failure(PRIVATE)

    monkeypatch.setattr(renderer.environment, "get_template", fail)
    with caplog.at_level(logging.INFO, logger="smd_reports"):
        with pytest.raises(ReportRenderError, match="Could not render report HTML") as caught:
            renderer.render_html(reports["generic"])
    assert isinstance(caught.value.__cause__, failure)
    assert PRIVATE not in str(caught.value) + caplog.text


def test_renderer_reports_invalid_object_and_unknown_theme(reports):
    renderer = ReportRenderer()
    with pytest.raises(TypeError, match="ReportLoader"):
        renderer.render_html({})
    with pytest.raises(ReportInputError, match="Unknown theme") as caught:
        renderer.render_html(reports["generic"], theme=PRIVATE)
    assert PRIVATE not in str(caught.value)


def test_pdf_failure_is_wrapped_without_logging_engine_message(reports, monkeypatch, caplog):
    def fail(**kwargs):
        raise RuntimeError(PRIVATE)

    monkeypatch.setitem(sys.modules, "weasyprint", SimpleNamespace(HTML=fail))
    monkeypatch.setitem(
        sys.modules,
        "weasyprint.urls",
        SimpleNamespace(FatalURLFetchingError=type("FatalResourceError", (BaseException,), {})),
    )
    monkeypatch.setattr("smd_reports.rendering._offline_url_fetcher", lambda: None)
    with caplog.at_level(logging.INFO, logger="smd_reports"):
        with pytest.raises(ReportRenderError, match="Could not generate the PDF") as caught:
            ReportRenderer().render_pdf(reports["generic"])
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert PRIVATE not in str(caught.value) + caplog.text


def test_pdf_rejects_swallowed_resource_failure(reports, monkeypatch):
    class HTML:
        def __init__(self, *, string, url_fetcher):
            try:
                url_fetcher("https://example.org/" + PRIVATE)
            except ValueError:
                pass

        def write_pdf(self, **kwargs):
            return b"incomplete PDF"

    class FailedFetcher:
        failed = False

        def __call__(self, url):
            self.failed = True
            raise ValueError("External report resources are prohibited")

    monkeypatch.setitem(sys.modules, "weasyprint", SimpleNamespace(HTML=HTML))
    monkeypatch.setitem(
        sys.modules,
        "weasyprint.urls",
        SimpleNamespace(FatalURLFetchingError=type("FatalResourceError", (BaseException,), {})),
    )
    monkeypatch.setattr("smd_reports.rendering._offline_url_fetcher", FailedFetcher)
    with pytest.raises(ReportRenderError, match="PDF resources could not be loaded"):
        ReportRenderer().render_pdf(reports["generic"])


def test_pdf_missing_runtime_has_installation_message(reports, monkeypatch, caplog):
    monkeypatch.setitem(sys.modules, "weasyprint", None)
    with caplog.at_level(logging.INFO, logger="smd_reports"):
        with pytest.raises(PDFUnavailableError, match=r"smd-reports\[pdf\]"):
            ReportRenderer().render_pdf(reports["generic"])
    assert "missing PDF dependencies" in caplog.text


@pytest.mark.parametrize(
    "contents, expected",
    [
        (b'{\n"PRIVATE": }', "line 2, column 12"),
        (b"\xff", "UTF-8"),
        (b'{"x":1,"x":2}', "Duplicate JSON keys"),
        (b'{"x":NaN}', "Non-finite JSON numbers"),
    ],
)
def test_cli_input_errors_are_specific(tmp_path, capsys, contents, expected):
    source = tmp_path / "input.json"
    source.write_bytes(contents)
    assert main(["validate", str(source)]) == 2
    output = capsys.readouterr()
    assert expected in output.err
    assert "smd-reports[pdf]" not in output.err
    assert "PRIVATE" not in output.err
    assert not output.out


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("missing", "not found"),
        ("directory", "directory"),
        ("permission", "permission denied"),
    ],
)
def test_cli_read_errors_are_specific(tmp_path, monkeypatch, capsys, kind, expected):
    source = tmp_path / PRIVATE
    if kind == "directory":
        source.mkdir()
    if kind == "permission":

        def fail(*args, **kwargs):
            raise PermissionError(PRIVATE)

        monkeypatch.setattr(Path, "read_text", fail)
    assert main(["validate", str(source)]) == 2
    error = capsys.readouterr().err
    assert "read the input JSON" in error and expected in error
    assert PRIVATE not in error


def test_verbose_logging_is_temporary_and_does_not_repeat(tmp_path, capsys):
    logger = logging.getLogger("smd_reports")
    previous = (logger.level, logger.propagate, logger.handlers[:])
    args = ["schema", "--output", str(tmp_path / "schema.json")]
    for _ in range(2):
        assert main(["--verbose", *args]) == 0
        error = capsys.readouterr().err
        assert error.count("Report JSON Schema exported") == 1
        assert error.count("Report output written") == 1
        assert (logger.level, logger.propagate, logger.handlers) == previous
    assert main(args) == 0
    assert capsys.readouterr().err == ""


def test_cli_failed_write_preserves_existing_output(tmp_path, monkeypatch, capsys):
    output = tmp_path / "schema.json"
    output.write_text("previous valid output")

    def fail(*args):
        raise OSError(PRIVATE)

    monkeypatch.setattr("smd_reports.cli.os.replace", fail)
    assert main(["schema", "--output", str(output)]) == 2
    error = capsys.readouterr().err
    assert "write the output file" in error
    assert PRIVATE not in error
    assert output.read_text() == "previous valid output"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["schema.json"]


def test_cli_output_write_preserves_existing_permissions(tmp_path):
    output = tmp_path / "schema.json"
    output.touch(mode=0o600)
    assert main(["schema", "--output", str(output)]) == 0
    assert output.stat().st_mode & 0o777 == 0o600


def test_cli_render_failure_returns_one(tmp_path, reports, monkeypatch, capsys):
    source = tmp_path / "input.json"
    source.write_text(reports["generic"].model_dump_json())

    def fail(*args, **kwargs):
        raise ReportRenderError("Could not render report HTML.")

    monkeypatch.setattr(ReportRenderer, "render_html", fail)
    output = tmp_path / "report.html"
    assert main(["render", str(source), "--format", "html", "--output", str(output)]) == 1
    assert capsys.readouterr().err.strip() == "Could not render report HTML."
    assert not output.exists()


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("dimension", "custom_width_mm"),
        ("heading", "Malformed record heading"),
        ("column-option", "column_options[0].width"),
    ],
)
def test_validation_formatter_explains_layout_errors(payloads, load, kind, expected):
    data = payloads["generic"]
    if kind == "dimension":
        data["presentation"] = {"page_size": "custom"}
    else:
        section = {
            "kind": "details",
            "key": "details",
            "columns": {"en": ["Value"]},
            "rows": [[PRIVATE]],
        }
        if kind == "heading":
            section["record_heading"] = "{"
        else:
            section["column_options"] = {"0": {"width": 0}}
        data["sections"] = [section]
    with pytest.raises(ValidationError) as caught:
        load(data)
    message = format_validation_error(caught.value)
    assert expected in message
    assert PRIVATE not in message


@pytest.mark.parametrize(
    "failure, expected",
    [
        (PermissionError, "Permission denied"),
        (IsADirectoryError, "directory"),
        (OSError, "could not be read"),
    ],
)
def test_asset_read_failures_have_specific_messages(payloads, monkeypatch, failure, expected):
    data = payloads["generic"]
    data["branding"] = {"center_logo": f"/{PRIVATE}/image.png"}

    def fail(*args):
        raise failure(PRIVATE)

    monkeypatch.setattr("smd_reports.loading.embed_image", fail)
    with pytest.raises(ReportAssetError) as caught:
        ReportLoader().loads(json.dumps(data))
    assert expected in str(caught.value)
    assert PRIVATE not in str(caught.value)
    assert isinstance(caught.value.__cause__, failure)


def test_cli_unknown_failure_is_sanitized(tmp_path, monkeypatch, capsys):
    def fail(*args):
        raise RuntimeError(PRIVATE)

    monkeypatch.setattr(ReportLoader, "schema", fail)
    output = tmp_path / "schema.json"
    assert main(["--verbose", "schema", "--output", str(output)]) == 1
    message = capsys.readouterr().err
    assert "failed unexpectedly" in message
    assert PRIVATE not in message and not output.exists()


def test_cli_missing_output_directory_explains_write_error(tmp_path, capsys):
    output = tmp_path / "missing" / "schema.json"
    assert main(["schema", "--output", str(output)]) == 2
    message = capsys.readouterr().err
    assert "write the output file" in message and "parent directory not found" in message
