"""Scalar and timestamp behavior."""

import pytest
from pydantic import ValidationError

from smd_reports.rendering import display


def test_scalar_values_remain_distinct():
    assert display(0) == "0"
    assert display(False) == "Nej"
    assert display(None) == "-"
    assert display({"en": "English", "sv": "Svenska"}, "sv") == "Svenska"


def test_naive_timestamp_rejected(payloads, load):
    values = payloads["pgx"]
    values["report"]["generated_at"] = "2026-01-01T12:00:00"
    with pytest.raises(ValidationError):
        load(values)
