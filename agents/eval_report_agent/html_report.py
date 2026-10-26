"""Portable HTML export: every EDA image and the Plotly runtime travel with the report."""
import base64
import html
import json
from pathlib import Path

import plotly.graph_objects as go


def write_html_report(run_dir: Path, markdown: str, plots: list[dict]) -> Path:
    directory = run_dir.resolve()
    images = []
    for plot in plots:
        path = (directory / plot["path"]).resolve()
        if not path.is_relative_to(directory) or path.suffix.lower() != ".png":
            raise ValueError("Report images must be PNG artifacts inside the run directory.")
        # Missing/corrupt artifacts fail explicitly instead of producing broken image links.
        contents = path.read_bytes()
        if not contents.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"Invalid PNG report image: {plot['path']}")
        source = "data:image/png;base64," + base64.b64encode(contents).decode("ascii")
        images.append(
            f'<figure><img alt="{html.escape(plot["title"], quote=True)}" src="{source}">'
            f'<figcaption>{html.escape(plot["description"])}</figcaption></figure>'
        )

    charts = []
    for index, name in enumerate(("comparison-chart.json", "evaluation-chart.json", "importance-chart.json")):
        # Windows' default text encoding corrupts UTF-8 chart titles (e.g. the middle dot).
        figure = go.Figure(json.loads((directory / name).read_text(encoding="utf-8")))
        charts.append(figure.to_html(full_html=False, include_plotlyjs=index == 0))

    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>CloudFlow report</title><style>'
        'body{font:16px/1.6 system-ui;max-width:1050px;margin:48px auto;padding:0 24px;color:#192849}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}'
        'img{display:block;max-width:100%;height:auto}figure{margin:32px 0}h1{color:#3558dd}'
        '@media print{figure{break-inside:avoid}}'
        '</style></head><body>'
        + '<pre>' + html.escape(markdown) + '</pre>'
        + ''.join(charts) + ''.join(images) + '</body></html>'
    )
    destination = directory / "report.html"
    temporary = destination.with_suffix(".html.tmp")
    temporary.write_text(document, encoding="utf-8")
    temporary.replace(destination)
    return destination
