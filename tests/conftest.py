"""JSON input fixtures shared by rendering and command-line tests."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from smd_reports import ReportLoader

INPUTS = Path(__file__).parents[1] / "examples/inputs"


@pytest.fixture(scope="session")
def example_payloads():
    return {path.stem: json.loads(path.read_text()) for path in INPUTS.glob("*.json")}


@pytest.fixture
def payloads(example_payloads):
    return deepcopy(example_payloads)


@pytest.fixture
def load():
    return lambda payload: ReportLoader().loads(json.dumps(payload), base_dir=INPUTS)


@pytest.fixture(scope="session")
def example_reports():
    return {path.stem: ReportLoader().load(path) for path in INPUTS.glob("*.json")}


@pytest.fixture
def reports(example_reports):
    return {name: report.model_copy(deep=True) for name, report in example_reports.items()}
