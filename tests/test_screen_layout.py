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
    genes = ["SMARCB1", "BRAF", "ALK", "APC"] * 10 + ["TP53", "PTEN", "JAK2"]
    data["sections"] = [
        {"kind": "compact_table", "key": "small", "items": ["CALR", "JAK2", "MPL"]},
        {"kind": "compact_table", "key": "large", "items": genes, "columns": columns},
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
            for key, expected in [("small", 3), ("large", len(genes))]:
                result = page.locator(f"#{key} .compact-table").evaluate(
                    """table => {
                      const rect = table.getBoundingClientRect();
                      return {scroll: table.scrollWidth, client: table.clientWidth,
                        overflow: getComputedStyle(table).overflowX,
                        right: rect.right, bottom: rect.bottom,
                        cells: [...table.querySelectorAll('td')].map(cell => {
                          const r = cell.getBoundingClientRect(), s = getComputedStyle(cell);
                          return {width: r.width, right: r.right, bottom: r.bottom,
                            border: s.borderLeftWidth,
                            scroll: cell.scrollWidth, client: cell.clientWidth};
                        })};
                    }"""
                )
                cells = result["cells"]
                assert len(cells) == expected
                assert result["scroll"] <= result["client"] + 1
                assert result["overflow"] not in {"auto", "scroll"}
                assert (
                    max(cell["width"] for cell in cells) - min(cell["width"] for cell in cells)
                    < 0.05
                )
                assert all(cell["border"] == "1px" for cell in cells)
                assert all(cell["scroll"] <= cell["client"] + 1 for cell in cells)
                assert all(cell["right"] <= result["right"] + 0.1 for cell in cells)
                assert all(cell["bottom"] <= result["bottom"] + 0.1 for cell in cells)
            prose = page.locator(".justified-text").evaluate(
                "e => ({size: parseFloat(getComputedStyle(e).fontSize), "
                "line: parseFloat(getComputedStyle(e).lineHeight)})"
            )
            assert prose["size"] == pytest.approx(8 * 96 / 72, abs=0.01)
            assert prose["line"] / prose["size"] == pytest.approx(1.2, abs=0.01)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        finally:
            browser.close()
