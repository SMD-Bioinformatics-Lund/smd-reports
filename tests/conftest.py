"""JSON input fixtures shared by rendering and command-line tests."""

import json
from pathlib import Path

import pytest

from smd_reports import ReportLoader

INPUTS = Path(__file__).parents[1] / "examples/inputs"


@pytest.fixture
def payloads():
    return {path.stem: json.loads(path.read_text()) for path in INPUTS.glob("*.json")}


@pytest.fixture
def load():
    return lambda payload: ReportLoader().loads(json.dumps(payload), base_dir=INPUTS)


@pytest.fixture
def reports():
    return {path.stem: ReportLoader().load(path) for path in INPUTS.glob("*.json")}
