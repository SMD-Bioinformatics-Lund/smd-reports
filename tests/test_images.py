"""Report plots accept declared formats and remain portable after source deletion."""

import base64
import io
import json
import re

import pytest
from PIL import Image

from smd_reports import ReportAssetError, ReportLoader, ReportRenderer


@pytest.mark.parametrize(
    "extension,format",
    [
        ("png", "PNG"),
        ("jpg", "JPEG"),
        ("webp", "WEBP"),
        ("gif", "GIF"),
        ("tiff", "TIFF"),
        ("bmp", "BMP"),
    ],
)
def test_inline_plot_formats_and_portable_json(payloads, tmp_path, extension, format):
    path = tmp_path / ("plot." + extension)
    Image.new("RGB", (100, 30), color=(10, 30, 200)).save(path, format=format)
    data = payloads["pgx"]
    data["branding"] = {}
    data["sections"] = [
        {
            "kind": "table",
            "key": "cnvs",
            "heading": "CNV",
            "columns": [{"label": "Gene"}],
            "rows": [["EXAMPLE"]],
            "images": [
                {
                    "source": path.name,
                    "caption": {"en": "Profile", "sv": "Profil"},
                    "width_percent": 80,
                }
            ],
        }
    ]
    document = ReportLoader().loads(json.dumps(data), base_dir=tmp_path)
    path.unlink()
    restored = ReportLoader().loads(document.model_dump_json())
    html = ReportRenderer().render_html(restored)
    assert "Profil" in html and "width: 80.0%" in html
    image = re.search(r'src="(data:image/(?:png|jpeg);base64,[^\"]+)"', html)[1]
    decoded = Image.open(io.BytesIO(base64.b64decode(image.split(",", 1)[1])))
    assert decoded.size == (100, 30)
    assert html.index("EXAMPLE") < html.index("<figure")


def test_tiff_frame_selection_and_format_policy_survive_normalization(payloads, tmp_path):
    path = tmp_path / "plot.tif"
    first = Image.new("RGB", (10, 10), (255, 0, 0))
    second = Image.new("RGB", (10, 10), (0, 0, 255))
    first.save(path, save_all=True, append_images=[second])
    data = payloads["pgx"]
    data["branding"] = {}
    data["presentation"]["accepted_image_formats"] = ["tiff"]
    data["sections"] = [{"kind": "image", "key": "plot", "source": path.name, "frame": 1}]
    document = ReportLoader().loads(json.dumps(data), base_dir=tmp_path)
    assert document.sections[0].source.startswith("data:image/tiff;")
    restored = ReportLoader().loads(document.model_dump_json())
    html = ReportRenderer().render_html(restored)
    encoded = re.search(r'src="data:image/png;base64,([^\"]+)"', html)[1]
    decoded = Image.open(io.BytesIO(base64.b64decode(encoded)))
    assert decoded.getpixel((5, 5)) == (0, 0, 255, 255)
    data["sections"][0]["frame"] = 5
    with pytest.raises(ReportAssetError):
        ReportLoader().loads(json.dumps(data), base_dir=tmp_path)
    data["sections"][0]["frame"] = 0
    data["presentation"]["accepted_image_formats"] = ["png"]
    with pytest.raises(ReportAssetError):
        ReportLoader().loads(json.dumps(data), base_dir=tmp_path)


@pytest.mark.parametrize("mismatched_mime", [False, True])
def test_invalid_raster_data_fails_validation(payloads, load, mismatched_mime):
    from pydantic import ValidationError

    raw = b"not an image"
    if mismatched_mime:
        stream = io.BytesIO()
        Image.new("RGB", (2, 2)).save(stream, format="JPEG")
        raw = stream.getvalue()
    data = payloads["pgx"]
    data["sections"] = [
        {
            "kind": "image",
            "key": "plot",
            "source": "data:image/png;base64," + base64.b64encode(raw).decode(),
        }
    ]
    with pytest.raises(ValidationError):
        load(data)
