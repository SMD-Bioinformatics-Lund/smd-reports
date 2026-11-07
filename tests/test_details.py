"""Finding cards preserve caller-owned data, order and interpretation text."""

import pytest
from pydantic import ValidationError

from smd_reports import DetailField, DetailRecord, DetailSection, ReportRenderer


def test_analysis_details_follow_summary_and_precede_method(reports):
    report = reports["coyote3-dna"].build()
    keys = [section.key for section in report.sections]
    assert keys.index("summary") < keys.index("snv-details") < keys.index("description")
    assert keys.index("description") < keys.index("covered-genes") < keys.index("references")
    html = ReportRenderer().render_html(report)
    for value in ["NM_004333.6", "c.1799T&gt;A", "140753336", "100 kb", "Instabila markörer"]:
        assert value in html
    assert "<strong>Synthetic example.</strong>" in html


@pytest.mark.parametrize("pairs", [1, 2, 3])
def test_detail_fields_preserve_order_values_and_escaping(reports, pairs):
    report = reports["coyote3-dna"].build()
    fields = [
        DetailField(label="A", value=0),
        DetailField(label="B", value=False),
        DetailField(
            label="Wide",
            value="**Reviewed** <script>bad()</script>",
            full_width=True,
            format="markdown",
        ),
        DetailField(label="C", value=None),
        DetailField(label="D", value="<PATIENT>"),
        DetailField(label="E", value="FINAL-FIELD"),
    ]
    report.sections = [
        DetailSection(
            key="details",
            title="Details",
            fields_per_row=pairs,
            records=[DetailRecord(key="one", title="Finding", fields=fields)],
        )
    ]
    html = ReportRenderer().render_html(report)
    assert html.index("<strong>Reviewed</strong>") < html.index("FINAL-FIELD")
    assert "<script>" not in html
    assert "&lt;PATIENT&gt;" in html
    assert ">0</td>" in html
    assert ">Nej</td>" in html
    assert ">-</td>" in html
    assert report == type(report).model_validate_json(report.model_dump_json())


def test_invalid_detail_records_rejected():
    with pytest.raises(ValidationError):
        DetailRecord(key="empty", title="Empty", fields=[])
    record = DetailRecord(key="one", title="One", fields=[DetailField(label="X", value=1)])
    with pytest.raises(ValidationError, match="Duplicate"):
        DetailSection(key="details", title="Details", records=[record, record])
    with pytest.raises(ValidationError):
        DetailField(label="X", value={"unknown": "nested data"})


def test_disabled_analysis_omits_its_details(reports):
    builder = reports["coyote3-dna"]
    builder.data.enabled_analyses = ["SNV"]
    keys = {section.key for section in builder.build().sections}
    assert "snv-details" in keys
    assert not {"cnvs", "cnv-details", "biomarkers", "biomarker-details"} & keys


def test_sequence_and_pgx_supporting_material_order(reports):
    cll = reports["cll-genie-positive"].build()
    keys = [section.key for section in cll.sections]
    assert keys.index("summary") < keys.index("cll-detail-0") < keys.index("description")
    pgx = reports["pgx"].build()
    keys = [section.key for section in pgx.sections]
    assert keys.index("pgx-variants") < keys.index("summary")
    assert keys.index("description") < keys.index("pgx-genes") < keys.index("references")
    assert keys.index("pgx-genes") < keys.index("pgx-targets")


def test_cll_sequence_rows_preserve_source_grouping(reports):
    import re

    document = reports["cll-genie-positive"].build()
    section = next(s for s in document.sections if s.key == "cll-detail-0")
    assert section.kind == "cll_sequences"
    assert document == type(document).model_validate_json(document.model_dump_json())
    html = ReportRenderer().render_html(document)
    article = re.search(r'<article class="cll-sequence".*?</article>', html, re.S)[0]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", article, re.S)
    v_row = next(row for row in rows if "V-GENE and allele" in row)
    j_row = next(row for row in rows if "J-GENE and allele" in row)
    for value in ["IGHV3-21*01", "Score:</strong> 1500", "313/321", "97.2% (312/321)"]:
        assert value in v_row
    for value in ["IGHJ6*02", "Score:</strong> 230", "60/60"]:
        assert value in j_row
    for row in rows:
        cells = re.findall(r"<(?:th|td)\b([^>]*)>", row)
        assert (
            sum(
                int(re.search(r'colspan="(\d+)"', cell)[1]) if "colspan=" in cell else 1
                for cell in cells
            )
            == 5
        )
    assert "D-REGION reading frame" in article and "FR-IMGT lengths" in article
    assert "DEMO-V {N1} DEMO-D {N2} DEMO-J" in article
    assert "0.0%" in article
    assert "Seq1 - 321 nt (Borderline (granskad))" in article
    assert 'class="cll-highlight"' in article


def test_cll_supplied_functionality_and_indel_text_are_never_inferred(reports):
    builder = reports["cll-genie-positive"]
    sequence = builder.data.sequences[0]
    sequence.identity_with_indels = None
    sequence.indel_summary = "<img src=x>Reviewed insertion description"
    sequence.functionality_label = "Authoritative application label"
    sequence.productivity = "Reviewed status, without rule evaluation"
    sequence.functionality_comment = None
    html = builder.render_html()
    assert "&lt;img src=x&gt;Reviewed insertion description" in html
    assert "<img src=x>" not in html
    assert "Authoritative application label" in html
    assert "Reviewed status, without rule evaluation" in html
    assert "automatically removed" not in html


def test_genexus_uses_its_own_complete_detail_groups(reports):
    document = reports["genexus"].build()
    html = ReportRenderer().render_html(document)
    for title in [
        "Detekterade mutationer",
        "Detekterade kopietalsförändringar",
        "Detaljerade fusionsresultat",
        "Detaljer för övriga fynd",
    ]:
        assert title in html
    for value in [
        "Hotspot",
        "CNV-kvot",
        "DEMO-FUSION-001",
        "Oncomine-drivargen",
        "Unika molekyler",
        "Obalansvärde",
        "Brytpunktsintervall",
    ]:
        assert value in html
    assert html.count('class="variant-detail genexus-detail"') == 5
    assert "Spanning pairs" not in html and "Prober" not in html
    assert "EXAMPLE2: p.(Example34del)" in html


@pytest.mark.parametrize("pairs", [1, 2, 3])
def test_genexus_batches_compact_fields_before_wide_annotations(reports, pairs):
    document = reports["genexus"].build()
    document.sections = [
        DetailSection(
            key="details",
            title="Details",
            fields_per_row=pairs,
            records=[
                DetailRecord(
                    key="finding",
                    title="Finding",
                    fields=[
                        DetailField(label="Gene", value="FIRST-COMPACT"),
                        DetailField(label="Classification", value="FULL-WIDTH", full_width=True),
                        DetailField(label="Final", value="LAST-COMPACT"),
                    ],
                )
            ],
        )
    ]
    html = ReportRenderer().render_html(document)
    assert html.index("FIRST-COMPACT") < html.index("LAST-COMPACT") < html.index("FULL-WIDTH")
    assert 'class="report_comment report_annotation"' in html
