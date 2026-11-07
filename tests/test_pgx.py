"""Clinical report preparation tests using explicitly synthetic TSV inputs."""

import csv

import pytest

from smd_reports import PGxData, PGxFiles, PGxReport
from smd_reports.plugins.pgx import FAULTY_RECOMMENDATION


def inputs(tmp_path, *, ad="20,10", depth="99"):
    tables = {
        "detected_variants": (
            ["GENE", "ID", "#CHROM", "POS", "GT", "AD"],
            [["DPYD", "rsDEMO", "1", "100", "0/1", ad]],
        ),
        "haplotype_definitions": (
            ["ID", "HAPLOTYPE"],
            [["rsDEMO", "DPYD-*2A"], ["rsOTHER", "TPMT-*3A"]],
        ),
        "possible_diplotypes": (
            ["gene", "Haplotype1", "Haplotype2", "Guideline", "Activity"],
            [["DPYD", "DPYD-*1", "DPYD-*2A", "Synthetic guideline", "1"]],
        ),
        "possible_interactions": (
            ["haplotypes", "Guideline"],
            [["TPMT-*1,TPMT-*3A,NUDT15-*1,NUDT15-*1", "Interaction"]],
        ),
        "missing_annotated_depth": (["ID", "Locus", "Total_Depth"], [["rsDEMO", "1:100", depth]]),
        "target_rsids": (
            ["chr", "start", "end", "rsID", "gene"],
            [["1", "99", "100", "rsDEMO", "DPYD"]],
        ),
    }
    paths = {}
    for name, (header, rows) in tables.items():
        path = tmp_path / f"{name}.tsv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, delimiter="\t")
            writer.writerow(header)
            writer.writerows(rows)
        paths[name] = path
    return PGxFiles(**paths)


def test_duplication_suppresses_guideline_and_depth_below_threshold(tmp_path, reports):
    files = inputs(tmp_path)
    context = reports["pgx"].data
    report = PGxReport.from_files(files, data=context, config=reports["pgx"].config)
    assert report.data.variants[0].frequency_percent == 33.33
    assert report.data.variants[0].possible_duplication is True
    assert report.data.recommendations[0].text == FAULTY_RECOMMENDATION
    assert report.data.low_depth_targets[0].depth == 99
    assert report.data.genes == ["DPYD"]
    assert "PGX_QC_PASS" not in report.render_html()
    assert not list(tmp_path.glob("*.depth.tsv"))


@pytest.mark.parametrize("ad,duplication", [("10,10", False), ("0,10", False), ("30,10", True)])
def test_allele_balance_and_exact_depth_boundary(tmp_path, reports, ad, duplication):
    report = PGxReport.from_files(
        inputs(tmp_path, ad=ad, depth="100"), data=reports["pgx"].data, config=reports["pgx"].config
    )
    assert report.data.variants[0].possible_duplication is duplication
    assert report.data.low_depth_targets == []
    assert "PGX_QC_PASS" in report.render_html()
    if not duplication:
        assert report.data.recommendations[0].text == "Synthetic guideline"


@pytest.mark.parametrize("ad", ["0,0", "-1,4", "1,2,3", "not-numeric"])
def test_invalid_allele_depths_fail(tmp_path, reports, ad):
    with pytest.raises(ValueError):
        PGxReport.from_files(
            inputs(tmp_path, ad=ad), data=reports["pgx"].data, config=reports["pgx"].config
        )


def test_zero_alt_and_empty_tables(tmp_path, reports):
    files = inputs(tmp_path, ad="20,0", depth="100")
    report = PGxReport.from_files(files, data=reports["pgx"].data, config=reports["pgx"].config)
    assert report.data.variants == []
    assert "Inga detekterade varianter" in report.render_html()
    # Header-only variant tables are a valid empty result, unlike unreadable/malformed files.
    files.detected_variants.write_text("GENE\tID\t#CHROM\tPOS\tGT\tAD\n", encoding="utf-8")
    assert PGxReport.from_files(files, data=report.data, config=report.config).data.variants == []


def test_prepared_inputs_reject_extra_clinical_fields(reports):
    values = reports["pgx"].data.model_dump()
    values["recommendations"][0]["unexpected"] = "discarding this would be unsafe"
    with pytest.raises(ValueError):
        PGxData.model_validate(values)
