#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Results reporting and export module for GlacierNET-KZ.

Provides functions for generating reports in multiple formats (JSON, CSV,
Markdown, HTML, GeoTIFF metadata) along with visualization helpers and
statistical summaries for glacier analysis results.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "generate_json_report",
    "generate_csv_report",
    "generate_markdown_report",
    "generate_html_report",
    "create_comparison_table",
    "create_summary_statistics",
    "export_geotiff_metadata",
    "format_metric",
    "create_color_scale",
    "generate_model_card",
]


def generate_json_report(results: dict, metadata: dict) -> str:
    """Generate a full JSON report with metadata, results, and summary.

    Parameters
    ----------
    results : dict
        Analysis results produced by the inference pipeline.  Expected to
        contain keys such as ``"predictions"``, ``"metrics"``, and
        ``"areas"``.
    metadata : dict
        Metadata about the run — model version, input paths, timestamps,
        environment details, etc.

    Returns
    -------
    str
        Pretty-printed JSON string.
    """
    summary = {}
    areas = results.get("areas", [])
    if areas and isinstance(areas, list):
        summary["summary_statistics"] = create_summary_statistics(areas)

    if "metrics" in results and isinstance(results["metrics"], dict):
        summary["model_metrics"] = results["metrics"]

    report = {
        "report_info": {
            "generator": "GlacierNET-KZ",
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "metadata": metadata,
        "results": results,
        "summary": summary,
    }
    return json.dumps(report, indent=2, default=str, ensure_ascii=False)


def generate_csv_report(results: list[dict], filename: str) -> str:
    """Export a list of result dictionaries to a CSV file.

    Parameters
    ----------
    results : list[dict]
        Each dict represents one row.  The union of all keys across dicts
        is used as column headers.
    filename : str | Path
        Destination file path.  Parent directories are created if needed.

    Returns
    -------
    str
        Absolute path of the written CSV file.

    Raises
    ------
    ValueError
        If *results* is empty.
    """
    if not results:
        raise ValueError("results must be a non-empty list of dicts")

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in results:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)

    filepath = Path(filename)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with filepath.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return str(filepath.resolve())


def generate_markdown_report(results: dict, title: str = "Glacier Analysis Report") -> str:
    """Generate a formatted Markdown report.

    Parameters
    ----------
    results : dict
        Analysis results to include.  Recognised top-level keys are
        ``"metrics"``, ``"areas"``, ``"details"``, and ``"model_info"``.
    title : str, optional
        Report title (default ``"Glacier Analysis Report"``).

    Returns
    -------
    str
        Markdown-formatted report string.
    """
    lines: list[str] = []
    lines.append(f"# {title}\n")
    lines.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")
    lines.append("---\n")

    # Model information
    model_info = results.get("model_info")
    if model_info and isinstance(model_info, dict):
        lines.append("## Model Information\n")
        for key, value in model_info.items():
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}:** {value}")
        lines.append("")

    # Metrics
    metrics = results.get("metrics")
    if metrics and isinstance(metrics, dict):
        lines.append("## Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for metric_name, metric_value in metrics.items():
            formatted_value = (
                format_metric(metric_value) if isinstance(metric_value, (int, float)) else str(metric_value)
            )
            label = metric_name.replace("_", " ").title()
            lines.append(f"| {label} | {formatted_value} |")
        lines.append("")

    # Area statistics
    areas = results.get("areas", [])
    if areas and isinstance(areas, list) and len(areas) > 0:
        stats = create_summary_statistics(areas)
        lines.append("## Area Statistics\n")
        lines.append("| Statistic | Value (km²) |")
        lines.append("|-----------|-------------|")
        for stat_name, stat_value in stats.items():
            label = stat_name.replace("_", " ").title()
            lines.append(f"| {label} | {format_metric(stat_value)} |")
        lines.append("")

    # Details / additional content
    details = results.get("details")
    if details:
        lines.append("## Details\n")
        if isinstance(details, dict):
            for key, value in details.items():
                label = key.replace("_", " ").title()
                if isinstance(value, dict):
                    lines.append(f"### {label}\n")
                    for k, v in value.items():
                        lines.append(f"- **{k}:** {v}")
                elif isinstance(value, list):
                    lines.append(f"- **{label}:** {', '.join(str(v) for v in value)}")
                else:
                    lines.append(f"- **{label}:** {value}")
        else:
            lines.append(str(details))
        lines.append("")

    lines.append("---\n")
    lines.append("*Report generated by GlacierNET-KZ*\n")
    return "\n".join(lines)


def generate_html_report(results: dict, title: str = "Glacier Analysis Report") -> str:
    """Generate a standalone HTML report with embedded CSS.

    Parameters
    ----------
    results : dict
        Analysis results to visualise.
    title : str, optional
        Page title (default ``"Glacier Analysis Report"``).

    Returns
    -------
    str
        Complete HTML document as a string.
    """
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    css = """\
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 900px; margin: 40px auto; padding: 0 20px;
       color: #333; background: #fafafa; line-height: 1.6; }
h1 { color: #1a5276; border-bottom: 2px solid #1a5276; padding-bottom: 8px; }
h2 { color: #2e86c1; margin-top: 32px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 24px; }
th, td { border: 1px solid #d5dbdb; padding: 8px 12px; text-align: left; }
th { background: #2e86c1; color: white; }
tr:nth-child(even) { background: #eaf2f8; }
.metric-value { font-weight: bold; color: #1a5276; }
.meta-info { color: #777; font-size: 0.9em; }
footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #ccc;
         color: #999; font-size: 0.85em; }
"""

    metrics_html = ""
    metrics = results.get("metrics")
    if metrics and isinstance(metrics, dict):
        rows = ""
        for k, v in metrics.items():
            formatted = format_metric(v) if isinstance(v, (int, float)) else str(v)
            label = k.replace("_", " ").title()
            rows += f'        <tr><td>{label}</td><td class="metric-value">{formatted}</td></tr>\n'
        metrics_html = f"""\
    <h2>Metrics</h2>
    <table>
        <thead><tr><th>Metric</th><th>Value</th></tr></thead>
        <tbody>
{rows}        </tbody>
    </table>
"""

    stats_html = ""
    areas = results.get("areas", [])
    if areas and isinstance(areas, list) and len(areas) > 0:
        stats = create_summary_statistics(areas)
        rows = ""
        for k, v in stats.items():
            label = k.replace("_", " ").title()
            rows += f'        <tr><td>{label}</td><td class="metric-value">{format_metric(v)} km²</td></tr>\n'
        stats_html = f"""\
    <h2>Area Statistics</h2>
    <table>
        <thead><tr><th>Statistic</th><th>Value (km²)</th></tr></thead>
        <tbody>
{rows}        </tbody>
    </table>
"""

    details_html = ""
    details = results.get("details")
    if details and isinstance(details, dict):
        items = ""
        for k, v in details.items():
            label = k.replace("_", " ").title()
            items += f"        <li><strong>{label}:</strong> {v}</li>\n"
        details_html = f"""\
    <h2>Details</h2>
    <ul>
{items}    </ul>
"""

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="meta-info">Generated: {generated} | Powered by GlacierNET-KZ</p>
{metrics_html}
{stats_html}
{details_html}
    <footer>
        GlacierNET-KZ &mdash; Glacier Detection and Analysis Pipeline
    </footer>
</body>
</html>"""
    return html


def create_comparison_table(models_results: list[dict], model_names: list[str]) -> str:
    """Create a Markdown table comparing results from multiple models.

    Parameters
    ----------
    models_results : list[dict]
        One metrics dict per model.  Each dict should map metric names
        to numeric values.
    model_names : list[str]
        Human-readable model names corresponding to *models_results*.

    Returns
    -------
    str
        Markdown table string.

    Raises
    ------
    ValueError
        If the lengths of *models_results* and *model_names* differ.
    """
    if len(models_results) != len(model_names):
        raise ValueError(
            f"models_results ({len(models_results)}) and model_names ({len(model_names)}) must have the same length"
        )

    # Collect the union of all metric keys
    all_metrics: list[str] = []
    seen: set[str] = set()
    for m in models_results:
        for k in m:
            if k not in seen:
                all_metrics.append(k)
                seen.add(k)

    if not all_metrics:
        return "_No metrics available for comparison._"

    col_widths = [max(len(n) for n in model_names + ["Metric"])]

    header = "| Metric | " + " | ".join(model_names) + " |"
    separator = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"
    # Build separator more robustly
    ["-"] * (1 + len(model_names))
    separator = "| " + " | ".join(f"{'-' * max(len(n), 8)}" for n in ["Metric"] + model_names) + " |"

    lines = [header, separator]
    for metric in all_metrics:
        row = f"| {metric.replace('_', ' ').title()} "
        for m in models_results:
            val = m.get(metric)
            formatted = format_metric(val) if isinstance(val, (int, float)) else str(val) if val is not None else "N/A"
            row += f"| {formatted} "
        row += "|"
        lines.append(row)

    return "\n".join(lines)


def create_summary_statistics(areas: list[float]) -> dict[str, float]:
    """Compute summary statistics for a list of area values.

    Parameters
    ----------
    areas : list[float]
        Area measurements (e.g. in km²).

    Returns
    -------
    dict[str, float]
        Dictionary with keys: ``mean``, ``std``, ``min``, ``max``,
        ``median``, ``q25``, ``q75``, ``total_area``.
    """
    if not areas:
        return {
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0,
            "q25": 0.0,
            "q75": 0.0,
            "total_area": 0.0,
        }

    sorted_areas = sorted(areas)
    n = len(sorted_areas)

    def _percentile(data: list[float], pct: float) -> float:
        """Linear-interpolation percentile (matches numpy default)."""
        k = (len(data) - 1) * pct / 100.0
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        return data[f] * (c - k) + data[c] * (k - f)

    std_val = statistics.stdev(areas) if n >= 2 else 0.0

    return {
        "mean": statistics.mean(areas),
        "std": std_val,
        "min": min(areas),
        "max": max(areas),
        "median": statistics.median(areas),
        "q25": _percentile(sorted_areas, 25),
        "q75": _percentile(sorted_areas, 75),
        "total_area": sum(areas),
    }


def export_geotiff_metadata(filename: str, metadata: dict) -> dict[str, Any]:
    """Prepare metadata dictionary suitable for GeoTIFF tag embedding.

    Parameters
    ----------
    filename : str
        Name of the GeoTIFF file these tags will be attached to.
    metadata : dict
        Arbitrary metadata (keys are normalised to upper-case with
        underscores replaced by hyphens for common TIFF tag names).

    Returns
    -------
    dict[str, Any]
        A dictionary ready to be passed to ``rasterio`` or ``tifffile``
        tag writers.
    """

    prepared: dict[str, Any] = {
        "TIFF_IMAGE_DESCRIPTION": metadata.get("description", f"GlacierNET-KZ output: {filename}"),
        "TIFF_SOFTWARE": metadata.get("software", "GlacierNET-KZ v1.0.0"),
        "TIFF_DATETIME": metadata.get("datetime", datetime.now(timezone.utc).strftime("%Y:%m:%d %H:%M:%S")),
    }

    for key, value in metadata.items():
        tag_key = f"TIFF_{key.upper().replace(' ', '_')}"
        if tag_key not in prepared:
            prepared[tag_key] = value

    prepared["_filename"] = filename
    prepared["_generated_at"] = datetime.now(timezone.utc).isoformat()
    return prepared


def format_metric(value: float, precision: int = 4) -> str:
    """Format a numeric metric with appropriate precision.

    Parameters
    ----------
    value : float
        The metric value to format.
    precision : int, optional
        Maximum number of significant digits (default 4).

    Returns
    -------
    str
        Formatted string.
    """
    if value is None:
        return "N/A"

    abs_val = abs(value)

    if abs_val == 0:
        return "0.0"

    if abs_val >= 1_000_000:
        return f"{value:,.{precision}f}"

    if abs_val >= 1:
        return f"{value:.{precision}f}"

    # For small values, use enough precision to show the first non-zero digit
    digits = max(precision, -int(math.floor(math.log10(abs_val))) + precision)
    formatted = f"{value:.{digits}g}"
    return formatted


def create_color_scale(
    values: list[float],
    colormap: str = "viridis",
    n_colors: int = 256,
) -> list[str]:
    """Generate a list of hex colours mapping *values* through a colormap.

    Parameters
    ----------
    values : list[float]
        Input values to map to colours.
    colormap : str, optional
        Matplotlib colormap name (default ``"viridis"``).
    n_colors : int, optional
        Number of discrete colours in the scale (default 256).

    Returns
    -------
    list[str]
        List of hex colour strings (``"#RRGGBB"``) with one entry per
        input value.  Falls back to a greyscale ramp when matplotlib is
        not installed.
    """
    if not values:
        return []

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.cm as cm

        cmap = cm.get_cmap(colormap, n_colors)
        vmin = min(values)
        vmax = max(values)
        span = vmax - vmin

        colours: list[str] = []
        for v in values:
            if span == 0:
                norm = 0.5
            else:
                norm = (v - vmin) / span
            r, g, b, _ = cmap(norm)
            colours.append(f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}")
        return colours

    except ImportError:
        # Greyscale fallback
        vmin = min(values)
        vmax = max(values)
        span = vmax - vmin
        colours = []
        for v in values:
            if span == 0:
                grey = 128
            else:
                grey = int(((v - vmin) / span) * 255)
            colours.append(f"#{grey:02x}{grey:02x}{grey:02x}")
        return colours


def generate_model_card(model_info: dict) -> str:
    """Generate a Markdown model card.

    Parameters
    ----------
    model_info : dict
        Expected keys: ``name``, ``description``, ``metrics`` (dict),
        ``limitations`` (str or list[str]), ``intended_use`` (str),
        and optional ``version``, ``architecture``, ``training_data``,
        ``date_trained``.

    Returns
    -------
    str
        Formatted Markdown string.
    """
    name = model_info.get("name", "Unknown Model")
    lines: list[str] = []

    lines.append(f"# Model Card: {name}\n")

    # Overview
    if "version" in model_info or "date_trained" in model_info:
        lines.append("## Overview\n")
        if "version" in model_info:
            lines.append(f"- **Version:** {model_info['version']}")
        if "architecture" in model_info:
            lines.append(f"- **Architecture:** {model_info['architecture']}")
        if "date_trained" in model_info:
            lines.append(f"- **Date Trained:** {model_info['date_trained']}")
        if "training_data" in model_info:
            lines.append(f"- **Training Data:** {model_info['training_data']}")
        lines.append("")

    # Description
    description = model_info.get("description", "No description provided.")
    lines.append("## Description\n")
    lines.append(f"{description}\n")

    # Intended use
    intended = model_info.get("intended_use", "Not specified.")
    lines.append("## Intended Use\n")
    lines.append(f"{intended}\n")

    # Metrics
    metrics = model_info.get("metrics")
    if metrics and isinstance(metrics, dict):
        lines.append("## Evaluation Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for m_name, m_value in metrics.items():
            formatted = format_metric(m_value) if isinstance(m_value, (int, float)) else str(m_value)
            label = m_name.replace("_", " ").title()
            lines.append(f"| {label} | {formatted} |")
        lines.append("")

    # Limitations
    limitations = model_info.get("limitations")
    if limitations:
        lines.append("## Limitations\n")
        if isinstance(limitations, list):
            for item in limitations:
                lines.append(f"- {item}")
        else:
            lines.append(f"{limitations}")
        lines.append("")

    lines.append("---\n")
    lines.append("*Generated by GlacierNET-KZ Model Card Generator*\n")
    return "\n".join(lines)
