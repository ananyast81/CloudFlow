import base64
import json
from html.parser import HTMLParser

import pytest
from PIL import Image

from agents.eval_report_agent.html_report import write_html_report


class ImageSources(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.sources = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.sources.append(dict(attrs)["src"])


@pytest.fixture
def report_artifacts(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    image = directory / "eda/plots/distribution.png"
    image.parent.mkdir(parents=True)
    Image.new("RGB", (3, 2), "blue").save(image)
    for name in ("comparison-chart.json", "evaluation-chart.json", "importance-chart.json"):
        (directory / name).write_text(json.dumps({"data": [], "layout": {"title": {"text": "SHAP · résumé"}}},
                                                ensure_ascii=False), encoding="utf-8")
    return directory, {"path": "eda/plots/distribution.png", "title": 'Age < 30 & "Churn"',
                       "description": "Training rows <script>alert('x')</script>"}


def test_report_embeds_original_png_and_preserves_utf8(report_artifacts):
    directory, plot = report_artifacts
    exported = write_html_report(directory, "# Résumé\n<script>alert('x')</script>", [plot])
    document = exported.read_text(encoding="utf-8")
    sources = ImageSources(document).sources
    assert len(sources) == 1
    assert sources[0].startswith("data:image/png;base64,")
    assert base64.b64decode(sources[0].split(",", 1)[1], validate=True) == (directory / plot["path"]).read_bytes()
    assert "SHAP · résumé" in document and "SHAP Â" not in document
    assert "<script>alert('x')</script>" not in document
    assert 'alt="Age &lt; 30 &amp; &quot;Churn&quot;"' in document


@pytest.mark.parametrize("problem", ["missing", "corrupt", "outside"])
def test_invalid_image_does_not_replace_existing_report(report_artifacts, problem):
    directory, plot = report_artifacts
    destination = directory / "report.html"
    destination.write_text("previous report", encoding="utf-8")
    if problem == "missing":
        plot["path"] = "eda/plots/missing.png"
    elif problem == "corrupt":
        (directory / plot["path"]).write_bytes(b"not a PNG")
    else:
        plot["path"] = "../outside.png"
    with pytest.raises((ValueError, FileNotFoundError)):
        write_html_report(directory, "report", [plot])
    assert destination.read_text(encoding="utf-8") == "previous report"
