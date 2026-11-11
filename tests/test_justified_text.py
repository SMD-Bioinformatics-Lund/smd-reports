"""Description prose uses justified text without changing heading or table alignment."""

import pytest

from smd_reports import ReportRenderer
from smd_reports.rendering import _offline_url_fetcher


@pytest.mark.parametrize("format", ["plain", "markdown"])
def test_description_prose_is_justified_in_screen_and_print(payloads, load, format):
    weasyprint = pytest.importorskip("weasyprint")
    data = payloads["generic"]
    data["sections"] = [
        {
            "kind": "description",
            "key": "method",
            "format": format,
            "text": "Narrative prose for the analysis method. " * 12,
        }
    ]
    html = ReportRenderer().render_html(load(data))
    assert f'class="justified-text {format}"' in html
    for media in ["screen", "print"]:
        rendered = weasyprint.HTML(
            string=html, media_type=media, url_fetcher=_offline_url_fetcher()
        ).render()
        prose = [
            box
            for page in rendered.pages
            for box in page._page_box.descendants()
            if type(box).__name__ == "BlockBox"
            and "Narrative prose" in "".join(box.element.itertext())
            and (
                (format == "markdown" and box.element_tag == "p")
                or (format == "plain" and box.element.get("class") == "justified-text plain")
            )
        ]
        assert prose and all(box.style["text_align_all"] == "justify" for box in prose)
