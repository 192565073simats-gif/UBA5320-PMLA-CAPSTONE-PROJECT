"""
statistical_analysis/visualization.py — Plotly chart builders.

All functions return a dict that can be serialised to JSON and consumed
by the Plotly.js client.
"""

from typing import Any, Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from scipy import stats as scipy_stats


def _fig_to_dict(fig: go.Figure) -> Dict[str, Any]:
    return fig.to_dict()


def create_histogram(
    marks: List[float],
    title: str = "Marks Distribution",
    x_label: str = "Marks",
    nbins: int = 15,
) -> Dict[str, Any]:
    """Return a Plotly histogram dict for *marks*."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=marks,
        nbinsx=nbins,
        name="Frequency",
        marker_color="#1a73e8",
        opacity=0.75,
    ))
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="Frequency",
        bargap=0.05,
        template="plotly_white",
    )
    return _fig_to_dict(fig)


def create_box_plot(
    data: Dict[str, List[float]],
    title: str = "Score Distribution",
) -> Dict[str, Any]:
    """
    Return a Plotly box plot dict.

    Args:
        data: mapping of label → list of marks.
    """
    fig = go.Figure()
    for label, values in data.items():
        fig.add_trace(go.Box(y=values, name=label, boxpoints="outliers"))
    fig.update_layout(
        title=title,
        yaxis_title="Marks",
        template="plotly_white",
    )
    return _fig_to_dict(fig)


def create_normal_distribution_curve(
    marks: List[float],
    title: str = "Normal Distribution Fit",
) -> Dict[str, Any]:
    """Return a histogram + fitted normal-distribution overlay."""
    if len(marks) < 2:
        return create_histogram(marks, title)

    arr = np.array(marks, dtype=float)
    mu, sigma = scipy_stats.norm.fit(arr)
    x = np.linspace(arr.min() - 2 * sigma, arr.max() + 2 * sigma, 300)
    pdf = scipy_stats.norm.pdf(x, mu, sigma)

    # Scale PDF to histogram counts
    bin_width = (arr.max() - arr.min()) / 15 if arr.max() != arr.min() else 1
    pdf_scaled = pdf * len(arr) * bin_width

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=marks,
        nbinsx=15,
        name="Frequency",
        marker_color="#1a73e8",
        opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=x.tolist(),
        y=pdf_scaled.tolist(),
        mode="lines",
        name=f"Normal Fit (μ={mu:.1f}, σ={sigma:.1f})",
        line=dict(color="#d93025", width=2),
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Marks",
        yaxis_title="Frequency",
        template="plotly_white",
    )
    return _fig_to_dict(fig)


def create_subject_comparison_bar(
    subject_names: List[str],
    means: List[float],
    medians: Optional[List[float]] = None,
    title: str = "Subject Performance Comparison",
) -> Dict[str, Any]:
    """Return a grouped bar chart comparing subject means (and optionally medians)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=subject_names,
        y=means,
        name="Mean",
        marker_color="#1a73e8",
    ))
    if medians:
        fig.add_trace(go.Bar(
            x=subject_names,
            y=medians,
            name="Median",
            marker_color="#34a853",
        ))
    fig.update_layout(
        title=title,
        xaxis_title="Subject",
        yaxis_title="Marks",
        barmode="group",
        template="plotly_white",
    )
    return _fig_to_dict(fig)


def create_performance_pie_chart(
    categories: Dict[str, int],
    title: str = "Performance Category Distribution",
) -> Dict[str, Any]:
    """Return a Plotly pie chart for performance categories."""
    color_map = {
        "Excellent": "#34a853",
        "Good": "#1a73e8",
        "Average": "#fbbc04",
        "Below Average": "#d93025",
    }
    labels = list(categories.keys())
    values = list(categories.values())
    colors = [color_map.get(lbl, "#9aa0a6") for lbl in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker_colors=colors,
        hole=0.35,
    ))
    fig.update_layout(title=title, template="plotly_white")
    return _fig_to_dict(fig)
