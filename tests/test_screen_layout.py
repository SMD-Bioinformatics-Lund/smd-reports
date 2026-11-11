"""Optional Chromium checks for compact matrices and dense description prose."""

import os
from pathlib import Path

import pytest

from smd_reports import ReportRenderer


@pytest.mark.parametrize("width", [320, 390, 768, 1440])
@pytest.mark.parametrize("columns", [None, 1])
def test_browser_matrices_have_borders_and_no_horizontal_scroll(
    payloads, load, tmp_path, width, columns
):
    executable = os.environ.get("SMD_REPORTS_CHROMIUM")
    if not executable or not Path(executable).is_file():
        pytest.skip("Set SMD_REPORTS_CHROMIUM to run browser layout checks")
    playwright = pytest.importorskip("playwright.sync_api")
    data = payloads["generic"]
    genes = ["C7orf55-LUC7L2", "BRAF", "ALK", "APC"] * 10 + ["TP53", "PTEN", "JAK2"]
    data["sections"] = [
        {"kind": "compact_table", "key": "small", "items": ["CALR", "JAK2", "MPL"]},
        {"kind": "compact_table", "key": "large", "items": genes, "columns": columns},
        {"kind": "compact_table", "key": "long", "items": ["LONG-GENE-" * 10]},
        {
            "kind": "compact_table",
            "key": "styled",
            "items": ["**BRAF** GENE"],
            "format": "markdown",
        },
        {"kind": "description", "key": "description", "text": "Compact narrative prose. " * 40},
    ]
    source = tmp_path / "report.html"
    source.write_text(ReportRenderer().render_html(load(data)), encoding="utf-8")
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=executable)
        try:
            page = browser.new_page(viewport={"width": width, "height": 1000})
            page.goto(source.as_uri())
            page.evaluate("document.fonts.ready")
            for key, expected in [("small", 3), ("large", len(genes)), ("long", 1), ("styled", 1)]:
                result = page.locator(f"#{key} .compact-table").evaluate(
                    """table => {
                      const rect = table.getBoundingClientRect();
                      return {scroll: table.scrollWidth, client: table.clientWidth,
                        overflow: getComputedStyle(table).overflowX,
                        right: rect.right, bottom: rect.bottom,
                        cells: [...table.querySelectorAll('td')].filter(cell =>
                          getComputedStyle(cell).display !== 'none').map(cell => {
                          const r = cell.getBoundingClientRect(), s = getComputedStyle(cell);
                          return {width: r.width, right: r.right, bottom: r.bottom,
                            border: s.borderRightWidth, text: cell.textContent,
                            height: r.height, left: r.left, top: r.top,
                            align: s.textAlign, vertical: s.alignItems,
                            scroll: cell.scrollWidth, client: cell.clientWidth};
                        })};
                    }"""
                )
                cells = result["cells"]
                assert len([cell for cell in cells if cell["text"].strip()]) == expected
                assert result["right"] == pytest.approx(
                    page.locator(f"#{key}").bounding_box()["x"]
                    + page.locator(f"#{key}").bounding_box()["width"],
                    abs=0.1,
                )
                assert max(cell["height"] for cell in cells) == pytest.approx(
                    min(cell["height"] for cell in cells), abs=0.05
                ), cells
                assert all(cell["align"] == "center" for cell in cells)
                assert all(cell["vertical"] == "center" for cell in cells)
                rows = {}
                for cell in cells:
                    rows.setdefault(round(cell["top"], 1), []).append(cell)
                assert len({len(row) for row in rows.values()}) == 1
                expected_text = ["CALR", "JAK2", "MPL"] if key == "small" else genes
                if key == "long":
                    expected_text = ["LONG-GENE-" * 10]
                if key == "styled":
                    expected_text = ["BRAF GENE"]
                assert [cell["text"] for cell in cells if cell["text"].strip()] == expected_text
                assert result["scroll"] <= result["client"] + 1
                assert result["overflow"] not in {"auto", "scroll"}
                assert (
                    max(cell["width"] for cell in cells) - min(cell["width"] for cell in cells)
                    < 0.05
                )
                assert all(cell["border"] == "1px" for cell in cells)
                assert all(cell["scroll"] <= cell["client"] + 1 for cell in cells), (key, cells)
                assert all(cell["right"] <= result["right"] + 0.1 for cell in cells)
                assert all(cell["bottom"] <= result["bottom"] + 0.1 for cell in cells)
            gap = page.locator("#styled .compact-value").evaluate(
                "e => { const r = document.createRange();"
                "r.setStart(e.lastChild, 1); r.setEnd(e.lastChild, 2);"
                "return r.getBoundingClientRect().left - "
                "e.firstChild.getBoundingClientRect().right; }"
            )
            assert gap > 0
            prose = page.locator(".justified-text").evaluate(
                "e => ({size: parseFloat(getComputedStyle(e).fontSize), "
                "line: parseFloat(getComputedStyle(e).lineHeight)})"
            )
            assert prose["size"] == pytest.approx(8 * 96 / 72, abs=0.01)
            assert prose["line"] / prose["size"] == pytest.approx(1.2, abs=0.01)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        finally:
            browser.close()


@pytest.mark.parametrize("preset", ["coyote3-dna", "coyote3-rna"])
@pytest.mark.parametrize("kind", ["details", "grid"])
def test_browser_full_width_labels_keep_the_theme_background(
    payloads, load, tmp_path, preset, kind
):
    executable = os.environ.get("SMD_REPORTS_CHROMIUM")
    if not executable or not Path(executable).is_file():
        pytest.skip("Set SMD_REPORTS_CHROMIUM to run browser layout checks")
    playwright = pytest.importorskip("playwright.sync_api")
    data = payloads[preset]
    section = {
        "kind": kind,
        "key": "detail",
        "columns": {"sv": ["Klassificering", "Kommentar"]},
        "column_options": {
            "0": {"full_width": True},
            "1": {"full_width": True, "format": "markdown"},
        },
        "rows": [["Tier I", "Wrapped comment. " * 100]],
    }
    if kind == "grid":
        section.update(
            grid_columns=6, layout=[{"cells": [{"column": i, "span": 6}]} for i in range(2)]
        )
    data["sections"] = [section]
    source = tmp_path / "labels.html"
    source.write_text(ReportRenderer().render_html(load(data)), encoding="utf-8")
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=executable)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 1000})
            page.goto(source.as_uri())
            page.evaluate("document.fonts.ready")
            for media in ["screen", "print"]:
                page.emulate_media(media=media)
                styles = page.locator(".detail-wide-row > th.report_key").evaluate_all(
                    "elements => elements.map(e => ({"
                    "background: getComputedStyle(e).backgroundColor,"
                    " tint: getComputedStyle(e).getPropertyValue('--tint').trim(),"
                    " value: getComputedStyle(e.nextElementSibling).backgroundColor}))"
                )
                assert len(styles) == 2
                for style in styles:
                    expected = tuple(int(style["tint"][i : i + 2], 16) for i in [1, 3, 5])
                    assert style["background"] == f"rgb{expected}"
                    assert style["value"] == "rgba(0, 0, 0, 0)"
        finally:
            browser.close()
