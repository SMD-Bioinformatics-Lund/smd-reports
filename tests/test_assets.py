"""Branding conditions and non-lossy scalar presentation."""

import base64

import pytest
from pydantic import ValidationError

from smd_reports import Branding, ReportMetadata, ReportRenderer
from smd_reports.rendering import display


def test_accreditation_requires_both_flag_and_logo(reports):
    artwork = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        b'<rect width="10" height="10"/></svg>'
    )
    logo = "data:image/svg+xml;base64," + base64.b64encode(artwork).decode("ascii")
    document = reports["genexus"].build()
    document.branding = Branding(accredited=False, accreditation_logo=logo)
    assert 'class="accreditation"' not in ReportRenderer().render_html(document)
    document.branding.accredited = True
    assert 'class="accreditation"' in ReportRenderer().render_html(document)
    document.branding.accreditation_logo = None
    assert 'class="accreditation"' not in ReportRenderer().render_html(document)


def test_scalar_values_remain_distinct():
    assert display(0) == "0"
    assert display(False) == "Nej"
    assert display(None) == "-"


def test_naive_timestamp_rejected(reports):
    values = reports["pgx"].data.metadata.model_dump()
    values["generated_at"] = "2026-01-01T12:00:00"
    with pytest.raises(ValidationError):
        ReportMetadata.model_validate(values)
