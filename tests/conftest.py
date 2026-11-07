"""Shared synthetic report fixtures."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "report_examples",
    Path(__file__).parents[1] / "examples" / "reports.py",
)
examples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(examples)


@pytest.fixture
def reports():
    return examples.demo_reports()
