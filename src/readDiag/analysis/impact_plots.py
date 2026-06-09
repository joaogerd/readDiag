"""Nature-style plotting helpers for observation-impact diagnostics.

The functions in this module operate on tables returned by
``ImpactAnalyzer.compute_all_metrics()`` or on concatenated tables containing a
``data`` cycle column. They intentionally keep plotting separate from metric
calculation so that the numerical impact workflow remains stable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Literal, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import ScalarFormatter

from ..plotting.style import NatureFigureStyle

Metric = Literal["TI", "FI", "FBI"]

__all__ = [
    "signed_log10",
    "select_top_kx",
    "plot_impact_ranked_bar",
    "plot_impact_cycle_comparison",
    "plot_impact_heatmap",
    "plot_impact_summary_bar",
    "save_impact_figure",
]


def signed_log10(values) -> np.ndarray:
    """Return a signed log10 transform for positive and negative impacts."""
    arr = np.asarray(values, dtype=float)
    return np.sign(arr) * np.log10(np.abs(arr) + 1.0)


def select_top_kx(table: pd.DataFrame, metric: str = "FI", top_k: int = 15) -> list[int]:
    """Select KX values by accumulated absolute impact."""
    if table.empty or metric not in table.columns:
        return []

    return (
        table.groupby("kx")[metric]
        .apply(lambda s: s.abs().sum())
        .sort_values(ascending=False)
        .head(top_k)
        .index.astype(int)
        .tolist()
    )


def _style_or_default(style: Optional[NatureFigureStyle] = None) -> NatureFigureStyle:
    if style is not None:
        style.set_global_style()
        return style
    style = NatureFigureStyle()
    style.set_global_style()
    return style


def _metric_label(metric: str, use_signed_log: bool = False) -> str:
    if use_signed_log:
        return rf"sign({metric}) log10(|{metric}| + 1)"
    return metric


def _format_scientific_x(ax) -> None:
    formatter = ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.xaxis.set_major_formatter(formatter)


def _prepare_ranked_data(
    table: pd.DataFrame,
    metric: str,
    top_k: int,
    cycle: Optional[str] = None,
    kx_order: Optional[Sequence[int]] = None,
    use_signed_log: bool = False,
) -> tuple[pd.DataFrame, str]:
    data = table.copy()
    if cycle is not None and "data" in data.columns:
        data = data[data["data"].astype(str) == str(cycle)].copy()

    if data.empty:
        return data, metric

    if kx_order is not None:
        wanted = [int(k) for k in kx_order]
        data = data[data["kx"].astype(int).isin(wanted)].copy()
    else:
        data["_abs_metric"] = data[metric].abs()
        data = data.sort_values("_abs_metric", ascending=False).head(top_k)

    plot_metric = metric
    if use_signed_log:
        plot_metric = f"signed_log10_{metric}"
        data[plot_metric] = signed_log10(data[metric])

    data = data.sort_values(plot_metric, ascending=True)
    return data, plot_metric


def plot_impact_ranked_bar(
    table: pd.DataFrame,
    metric: Metric = "FI",
    cycle: Optional[str] = None,
    top_k: int = 15,
    use_signed_log: bool = False,
    ax: Optional[plt.Axes] = None,
    style: Optional[NatureFigureStyle] = None,
    title: Optional[str] = None,
):
    """Plot a compact horizontal ranked bar chart for one impact metric.

    Parameters
    ----------
    table : pandas.DataFrame
        Impact table containing at least ``kx`` and the selected metric. A
        ``data`` column is optional and can be used with ``cycle``.
    metric : {'TI', 'FI', 'FBI'}, default 'FI'
        Metric to plot.
    cycle : str, optional
        Cycle identifier to filter when ``table`` contains multiple cycles.
    top_k : int, default 15
        Number of KX values to show, selected by largest absolute metric.
    use_signed_log : bool, default False
        If True, use a signed log10 transform. This is especially useful for TI.
    ax : matplotlib.axes.Axes, optional
        Existing axes. If omitted, a Nature-style figure is created.
    style : NatureFigureStyle, optional
        Style object. If omitted, the default Nature-inspired style is used.
    title : str, optional
        Custom title.
    """
    style = _style_or_default(style)
    data, plot_metric = _prepare_ranked_data(
        table=table,
        metric=metric,
        top_k=top_k,
        cycle=cycle,
        use_signed_log=use_signed_log,
    )

    if ax is None:
        height_mm = max(55.0, 6.0 * max(len(data), 1) + 22.0)
        fig, ax = style.create_figure(kind="single", height_mm=height_mm, aspect=0.8)
    else:
        fig = ax.figure

    if data.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    palette = style.get_palette()
    color = palette[5] if len(palette) > 5 else palette[0]
    ax.barh(data["kx"].astype(str), data[plot_metric], color=color)
    ax.axvline(0.0, color="black", linewidth=style.axis_width)

    if title is None:
        if cycle is None:
            title = f"{metric} impact — top {top_k} KX"
        else:
            title = f"{metric} impact — {cycle} — top {top_k} KX"
        if use_signed_log:
            title += " — signed log"

    style.apply_to_axes(
        ax,
        xlabel=_metric_label(metric, use_signed_log),
        ylabel="KX",
        title=title,
        grid=False,
        despine_top=False,
        despine_right=False,
    )

    if metric == "TI" and not use_signed_log:
        _format_scientific_x(ax)

    fig.canvas.draw_idle()
    return ax


def plot_impact_cycle_comparison(
    table: pd.DataFrame,
    metric: Metric = "FI",
    top_k: int = 15,
    use_signed_log: bool = False,
    style: Optional[NatureFigureStyle] = None,
):
    """Plot one aligned panel per cycle using the same top-K KX set."""
    if table.empty:
        style = _style_or_default(style)
        fig, ax = style.create_figure(kind="single", height_mm=45.0)
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    style = _style_or_default(style)
    cycles = sorted(table["data"].astype(str).unique()) if "data" in table.columns else [None]
    top_kx = select_top_kx(table, metric=metric, top_k=top_k)

    nrows = len(cycles)
    height_mm = min(style.max_main_height_mm, max(55.0, 45.0 * nrows))
    fig, axes = style.create_figure(
        kind="double",
        height_mm=height_mm,
        nrows=nrows,
        ncols=1,
        sharex=True,
        squeeze=False,
    )
    axes_flat = list(axes.ravel())

    values_for_xlim = []
    prepared = []
    for cycle in cycles:
        data, plot_metric = _prepare_ranked_data(
            table=table,
            metric=metric,
            top_k=top_k,
            cycle=cycle,
            kx_order=top_kx,
            use_signed_log=use_signed_log,
        )
        prepared.append((cycle, data, plot_metric))
        if not data.empty:
            values_for_xlim.extend(data[plot_metric].tolist())

    max_abs = float(np.nanmax(np.abs(values_for_xlim))) if values_for_xlim else 1.0
    if not np.isfinite(max_abs) or max_abs == 0:
        max_abs = 1.0
    xlim = (-1.08 * max_abs, 1.08 * max_abs)

    palette = style.get_palette()
    color = palette[5] if len(palette) > 5 else palette[0]

    for ax, (cycle, data, plot_metric) in zip(axes_flat, prepared):
        if data.empty:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            continue

        ax.barh(data["kx"].astype(str), data[plot_metric], color=color)
        ax.axvline(0.0, color="black", linewidth=style.axis_width)
        ax.set_xlim(xlim)

        subtitle = f"Cycle {cycle}" if cycle is not None else "Impact"
        style.apply_to_axes(ax, ylabel="KX", title=subtitle, grid=False)
        if metric == "TI" and not use_signed_log:
            _format_scientific_x(ax)

    axes_flat[-1].set_xlabel(_metric_label(metric, use_signed_log))
    fig.suptitle(f"{metric} impact by cycle — top {top_k} KX", fontsize=style.max_fontsize)
    fig.canvas.draw_idle()
    return axes_flat[-1]


def plot_impact_heatmap(
    table: pd.DataFrame,
    metric: Metric = "FI",
    top_k: int = 20,
    use_signed_log: bool = False,
    style: Optional[NatureFigureStyle] = None,
):
    """Plot a compact cycle-by-KX heatmap centered at zero."""
    style = _style_or_default(style)

    if table.empty:
        fig, ax = style.create_figure(kind="single", height_mm=45.0)
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    top_kx = select_top_kx(table, metric=metric, top_k=top_k)
    data = table[table["kx"].astype(int).isin(top_kx)].copy()

    plot_metric = metric
    if use_signed_log:
        plot_metric = f"signed_log10_{metric}"
        data[plot_metric] = signed_log10(data[metric])

    pivot = (
        data.pivot_table(index="kx", columns="data", values=plot_metric, aggfunc="sum")
        .reindex(top_kx)
        .fillna(0.0)
    )

    values = pivot.values
    vmax = float(np.nanmax(np.abs(values))) if values.size else 1.0
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    height_mm = min(style.max_main_height_mm, max(65.0, 5.0 * len(pivot.index) + 25.0))
    fig, ax = style.create_figure(kind="single", height_mm=height_mm, aspect=0.9)

    image = ax.imshow(
        values,
        aspect="auto",
        cmap="coolwarm",
        norm=TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax),
    )

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns.astype(str), rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index.astype(str))

    style.apply_to_axes(
        ax,
        xlabel="Cycle",
        ylabel="KX",
        title=f"{metric} heatmap — top {top_k} KX",
        grid=False,
    )

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label(_metric_label(metric, use_signed_log), fontsize=style.base_fontsize)
    cbar.ax.tick_params(labelsize=style.min_fontsize, width=style.axis_width, length=style.tick_length)

    fig.canvas.draw_idle()
    return ax


def plot_impact_summary_bar(
    summary: pd.DataFrame,
    metric: str = "FI_mean",
    top_k: int = 15,
    style: Optional[NatureFigureStyle] = None,
):
    """Plot a compact summary bar chart from a KX summary table."""
    style = _style_or_default(style)

    if summary.empty or metric not in summary.columns:
        fig, ax = style.create_figure(kind="single", height_mm=45.0)
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    data = summary.copy()
    data["_abs_metric"] = data[metric].abs()
    data = data.sort_values("_abs_metric", ascending=False).head(top_k)
    data = data.sort_values(metric, ascending=True)

    height_mm = max(55.0, 6.0 * len(data) + 22.0)
    fig, ax = style.create_figure(kind="single", height_mm=height_mm, aspect=0.8)

    palette = style.get_palette()
    color = palette[5] if len(palette) > 5 else palette[0]
    ax.barh(data["kx"].astype(str), data[metric], color=color)
    ax.axvline(0.0, color="black", linewidth=style.axis_width)

    style.apply_to_axes(
        ax,
        xlabel=metric,
        ylabel="KX",
        title=f"Top {top_k} KX by |{metric}|",
        grid=False,
    )

    if metric.startswith("TI"):
        _format_scientific_x(ax)

    fig.canvas.draw_idle()
    return ax


def save_impact_figure(
    ax_or_fig,
    filename: str | Path,
    style: Optional[NatureFigureStyle] = None,
    mode: str = "main",
    validate: bool = False,
) -> list[str]:
    """Save an impact figure using the Nature-style exporter."""
    style = _style_or_default(style)

    fig = ax_or_fig
    if hasattr(ax_or_fig, "figure"):
        fig = ax_or_fig.figure

    return style.export(fig, filename, mode=mode, validate=validate)
