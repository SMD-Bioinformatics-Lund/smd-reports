"""Rectangular compact matrices and theme-tinted full-width detail labels."""

import json
from collections import defaultdict

import pytest

from smd_reports import ReportLoader, ReportRenderer


@pytest.mark.parametrize(
    "items,maximum",
    [
        ([], 15),
        (["CALR"], 15),
        (["CALR", "JAK2", "MPL"], 2),
        (["C7orf55-LUC7L2", "A", "BRAF"] * 21, 15),
    ],
)
def test_print_matrix_is_full_width_centered_and_rectangular(payloads, load, items, maximum):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML

    from smd_reports.rendering import _compact_tables, _offline_url_fetcher

    data = payloads["coyote3-dna"]
    data["sections"] = [
        {
            "key": "genes",
            "kind": "compact_table",
            "items": items,
            "columns": maximum,
            "caption": "Tabell 1: Gener",
        }
    ]
    report = load(data)
    renderer = ReportRenderer()
    html = renderer.render_html(report)
    assert report.sections[0].items == items
    assert json.loads(report.model_dump_json())["sections"][0]["items"] == items
    assert ReportLoader().loads(report.model_dump_json()) == report
    assert 'class="table-caption"' in html and "Tabell 1: Gener" in html
    rendered = HTML(string=html, url_fetcher=_offline_url_fetcher()).render()
    cells = [
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if type(box).__name__ == "TableCellBox"
        and "compact-cell" in box.element.get("class", "").split()
    ]
    if not items:
        assert not cells and '<p class="empty">' in html
        return
    layout = _compact_tables(report, renderer.themes[report.theme_name])["genes"]
    count = len(layout["widths"])
    assert count <= maximum
    assert len(cells) == ((len(items) + count - 1) // count) * count
    assert max(c.border_width() for c in cells) == pytest.approx(
        min(c.border_width() for c in cells), abs=0.01
    )
    assert max(c.border_height() for c in cells) == pytest.approx(
        min(c.border_height() for c in cells), abs=0.01
    )
    rows = defaultdict(list)
    content = []
    for cell in cells:
        rows[cell.position_y].append(cell)
        assert cell.style["text_align_all"] == "center"
        assert cell.style["vertical_align"] == "middle"
        assert all(
            getattr(cell, f"border_{edge}_width") > 0 for edge in ["top", "right", "bottom", "left"]
        )
        lines = [box for box in cell.descendants() if type(box).__name__ == "LineBox"]
        if "compact-empty" in cell.element.get("class", ""):
            assert cell.element.get("aria-hidden") == "true" and not lines
        else:
            assert len(lines) == 1 and lines[0].width <= cell.width
            content.append(
                "".join(
                    box.text for box in lines[0].descendants() if type(box).__name__ == "TextBox"
                )
            )
    assert content == items
    assert {len(row) for row in rows.values()} == {count}
    for row in rows.values():
        right = row[-1].position_x + row[-1].border_width()
        assert right - row[0].position_x == pytest.approx(178 * 96 / 25.4 - 1, abs=1)


@pytest.mark.parametrize("preset", ["coyote3-dna", "coyote3-rna"])
@pytest.mark.parametrize("kind", ["details", "grid"])
def test_print_full_width_detail_labels_use_theme_tint(payloads, load, preset, kind):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML

    from smd_reports.rendering import _offline_url_fetcher

    data = payloads[preset]
    section = {
        "kind": kind,
        "key": "finding",
        "columns": {"sv": ["Klassificering", "Kommentar"]},
        "column_options": {
            "0": {"full_width": True},
            "1": {"full_width": True, "format": "markdown"},
        },
        "rows": [["Tier I", "Long comment. " * 80]],
    }
    if kind == "grid":
        section.update(
            grid_columns=6, layout=[{"cells": [{"column": i, "span": 6}]} for i in range(2)]
        )
    data["sections"] = [section]
    report = load(data)
    renderer = ReportRenderer()
    theme = renderer.themes[report.theme_name]
    expected = tuple(int(theme.tint[i : i + 2], 16) / 255 for i in [1, 3, 5])
    rendered = HTML(
        string=renderer.render_html(report), url_fetcher=_offline_url_fetcher()
    ).render()
    labels = [
        box
        for page in rendered.pages
        for box in page._page_box.descendants()
        if type(box).__name__ == "BlockBox"
        and box.element_tag == "th"
        and box.element.get("class") == "report_key"
    ]
    assert len(labels) == 2
    assert all(
        tuple(box.style["background_color"].coordinates) == pytest.approx(expected)
        for box in labels
    )
