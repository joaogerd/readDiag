"""Modern academic plotting helpers for observation-impact diagnostics.

The functions in this module operate on tables returned by
``ImpactAnalyzer.compute_all_metrics()`` or on concatenated tables containing a
``data`` cycle column. They intentionally keep plotting separate from metric
calculation so that the numerical impact workflow remains stable.

The visual style is academic-modern rather than strictly minimalist: compact
panels, readable annotations, subtle reference shading, accessible colours,
clear zero lines, and editable vector export.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
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


NEGATIVE_COLOR = "#0072B2"
POSITIVE_COLOR = "#D55E00"
NEUTRAL_COLOR = "#4D4D4D"
SHADE_COLOR = "#F2F2F2"


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
    """Return a readable academic style based on NatureFigureStyle."""
    if style is not None:
        style.set_global_style()
        return style

    style = NatureFigureStyle(
        base_fontsize=7.0,
        min_fontsize=6.0,
        max_fontsize=9.0,
        panel_label_size=10.0,
        axis_width=0.6,
        line_width=0.8,
        tick_length=3.0,
        dpi=450,
        use_grid=False,
    )
    style.set_global_style()
    return style


def _metric_label(metric: str, use_signed_log: bool = False) -> str:
    """Return publication-friendly metric labels."""
    if use_signed_log:
        return rf"sign({metric}) log$_{{10}}$(|{metric}| + 1)"
    if metric in {"FI", "FBI"}:
        return f"{metric} (%)"
    return metric


def _format_scientific_x(ax) -> None:
    formatter = ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.xaxis.set_major_formatter(formatter)


def _impact_cmap() -> LinearSegmentedColormap:
    """Return a blue-white-vermillion diverging colormap."""
    return LinearSegmentedColormap.from_list(
        "readDiagImpactDiverging",
        [NEGATIVE_COLOR, "#FFFFFF", POSITIVE_COLOR],
        N=256,
    )


def _bar_colors(values) -> list[str]:
    """Assign accessible colours by sign."""
    arr = np.asarray(values, dtype=float)
    return [POSITIVE_COLOR if value > 0 else NEGATIVE_COLOR for value in arr]


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


def _apply_academic_axes(
    ax,
    style: NatureFigureStyle,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    show_xgrid: bool = True,
) -> None:
    """Apply modern academic axes styling."""
    style.apply_to_axes(
        ax,
        xlabel=xlabel,
        ylabel=ylabel,
        title=title,
        grid=False,
        despine_top=True,
        despine_right=True,
    )

    if show_xgrid:
        ax.grid(
            True,
            axis="x",
            linestyle="--",
            linewidth=0.45,
            alpha=0.35,
            color="0.55",
        )
    ax.grid(False, axis="y")

    ax.tick_params(axis="both", labelsize=style.min_fontsize)
    ax.title.set_fontweight("bold")


def _shade_negative_side(ax) -> None:
    """Shade the negative-impact side, similar to a contextual phase band."""
    xmin, xmax = ax.get_xlim()
    if xmin < 0:
        ax.axvspan(xmin, min(0.0, xmax), color=SHADE_COLOR, zorder=0)
    ax.set_xlim(xmin, xmax)


def _add_panel_cycle_label(ax, label: str, style: NatureFigureStyle) -> None:
    """Add a cycle label inside the axes to avoid title/suptitle overlap."""
    ax.text(
        0.012,
        0.955,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=style.max_fontsize,
        fontweight="bold",
        color="black",
        bbox={
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.88,
            "pad": 1.8,
        },
        zorder=10,
    )


def _format_annotation_value(metric: str, value: float, use_signed_log: bool) -> str:
    """Format annotation values without exposing internal column names."""
    if use_signed_log:
        return f"{metric}={value:.2e}"
    if metric in {"FI", "FBI", "FI_mean", "FI_min", "FI_max", "FBI_mean", "FBI_min", "FBI_max"}:
        return f"{metric}={value:.2f}%"
    return f"{metric}={value:.2e}"


def _annotate_extremes(
    ax,
    data: pd.DataFrame,
    plot_metric: str,
    metric: str,
    use_signed_log: bool,
    style: NatureFigureStyle,
) -> None:
    """Annotate the strongest negative and positive KX only."""
    if data.empty:
        return

    candidates = []
    if (data[plot_metric] < 0).any():
        candidates.append(data.loc[data[plot_metric].idxmin()])
    if (data[plot_metric] > 0).any():
        candidates.append(data.loc[data[plot_metric].idxmax()])

    y_lookup = {str(label.get_text()): pos for pos, label in enumerate(ax.get_yticklabels())}
    x_span = ax.get_xlim()[1] - ax.get_xlim()[0]

    for row in candidates:
        kx_label = str(int(row["kx"]))
        if kx_label not in y_lookup:
            continue

        x = float(row[plot_metric])
        y = y_lookup[kx_label]
        raw = float(row[metric]) if metric in row else x
        ha = "left" if x >= 0 else "right"
        dx = 0.025 * x_span if x >= 0 else -0.025 * x_span
        text = f"KX {kx_label}\n{_format_annotation_value(metric, raw, use_signed_log)}"

        ax.annotate(
            text,
            xy=(x, y),
            xytext=(x + dx, y),
            ha=ha,
            va="center",
            fontsize=style.min_fontsize,
            color="black",
            arrowprops={
                "arrowstyle": "-",
                "color": NEUTRAL_COLOR,
                "lw": 0.6,
                "shrinkA": 0,
                "shrinkB": 4,
            },
        )


def plot_impact_ranked_bar(
    table: pd.DataFrame,
    metric: Metric = "FI",
    cycle: Optional[str] = None,
    top_k: int = 15,
    use_signed_log: bool = False,
    ax: Optional[plt.Axes] = None,
    style: Optional[NatureFigureStyle] = None,
    title: Optional[str] = None,
    annotate_extremes: bool = True,
):
    """Plot a modern horizontal ranked bar chart for one impact metric."""
    style = _style_or_default(style)
    data, plot_metric = _prepare_ranked_data(
        table=table,
        metric=metric,
        top_k=top_k,
        cycle=cycle,
        use_signed_log=use_signed_log,
    )

    if ax is None:
        height_mm = max(70.0, 6.5 * max(len(data), 1) + 30.0)
        fig, ax = style.create_figure(kind="double", height_mm=height_mm, aspect=0.55)
    else:
        fig = ax.figure

    if data.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    values = data[plot_metric].to_numpy(dtype=float)
    colors = _bar_colors(values)
    y_labels = data["kx"].astype(str)

    ax.barh(
        y_labels,
        values,
        color=colors,
        edgecolor="white",
        linewidth=0.4,
        alpha=0.92,
        zorder=2,
    )
    ax.scatter(
        values,
        np.arange(len(values)),
        s=22,
        c=colors,
        edgecolors="white",
        linewidths=0.7,
        zorder=4,
    )

    max_abs = float(np.nanmax(np.abs(values))) if values.size else 1.0
    if not np.isfinite(max_abs) or max_abs == 0:
        max_abs = 1.0
    ax.set_xlim(-1.18 * max_abs, 1.18 * max_abs)
    _shade_negative_side(ax)
    ax.axvline(0.0, color="black", linewidth=0.7, zorder=3)

    if title is None:
        cycle_text = f" — {cycle}" if cycle is not None else ""
        title = f"{metric} impact{cycle_text}: top {top_k} KX"
        if use_signed_log:
            title += " (signed log scale)"

    _apply_academic_axes(
        ax,
        style,
        xlabel=_metric_label(metric, use_signed_log),
        ylabel="KX",
        title=title,
        show_xgrid=True,
    )

    if metric == "TI" and not use_signed_log:
        _format_scientific_x(ax)

    if annotate_extremes:
        _annotate_extremes(ax, data, plot_metric, metric, use_signed_log, style)

    fig.canvas.draw_idle()
    return ax


def plot_impact_cycle_comparison(
    table: pd.DataFrame,
    metric: Metric = "FI",
    top_k: int = 15,
    use_signed_log: bool = False,
    style: Optional[NatureFigureStyle] = None,
    annotate_extremes: bool = False,
):
    """Plot one aligned panel per cycle using the same top-K KX set."""
    style = _style_or_default(style)

    if table.empty:
        fig, ax = style.create_figure(kind="double", height_mm=55.0)
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    cycles = sorted(table["data"].astype(str).unique()) if "data" in table.columns else [None]
    top_kx = select_top_kx(table, metric=metric, top_k=top_k)
    nrows = len(cycles)

    height_mm = min(style.max_main_height_mm, max(78.0, 58.0 * nrows + 8.0))
    fig, axes = style.create_figure(
        kind="double",
        height_mm=height_mm,
        nrows=nrows,
        ncols=1,
        sharex=True,
        squeeze=False,
    )
    axes_flat = list(axes.ravel())

    prepared = []
    values_for_xlim = []
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
            values_for_xlim.extend(data[plot_metric].to_numpy(dtype=float).tolist())

    max_abs = float(np.nanmax(np.abs(values_for_xlim))) if values_for_xlim else 1.0
    if not np.isfinite(max_abs) or max_abs == 0:
        max_abs = 1.0
    xlim = (-1.18 * max_abs, 1.18 * max_abs)

    for ax, (cycle, data, plot_metric) in zip(axes_flat, prepared):
        if data.empty:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            continue

        values = data[plot_metric].to_numpy(dtype=float)
        colors = _bar_colors(values)
        y_labels = data["kx"].astype(str)

        ax.barh(
            y_labels,
            values,
            color=colors,
            edgecolor="white",
            linewidth=0.35,
            alpha=0.92,
            zorder=2,
        )
        ax.scatter(
            values,
            np.arange(len(values)),
            s=18,
            c=colors,
            edgecolors="white",
            linewidths=0.6,
            zorder=4,
        )
        ax.set_xlim(xlim)
        _shade_negative_side(ax)
        ax.axvline(0.0, color="black", linewidth=0.7, zorder=3)

        _apply_academic_axes(ax, style, ylabel="KX", title=None, show_xgrid=True)
        subtitle = f"Cycle {cycle}" if cycle is not None else "Impact"
        _add_panel_cycle_label(ax, subtitle, style)

        if metric == "TI" and not use_signed_log:
            _format_scientific_x(ax)
        if annotate_extremes:
            _annotate_extremes(ax, data, plot_metric, metric, use_signed_log, style)

    axes_flat[-1].set_xlabel(_metric_label(metric, use_signed_log))
    fig.suptitle(
        f"{metric} impact by cycle — top {top_k} KX",
        fontsize=style.max_fontsize + 1,
        fontweight="bold",
        y=0.995,
    )
    fig.canvas.draw_idle()
    return axes_flat[-1]


def plot_impact_heatmap(
    table: pd.DataFrame,
    metric: Metric = "FI",
    top_k: int = 20,
    use_signed_log: bool = False,
    style: Optional[NatureFigureStyle] = None,
    annotate: Optional[bool] = None,
):
    """Plot a compact cycle-by-KX heatmap centered at zero."""
    style = _style_or_default(style)

    if table.empty:
        fig, ax = style.create_figure(kind="double", height_mm=55.0)
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

    height_mm = min(style.max_main_height_mm, max(75.0, 5.2 * len(pivot.index) + 32.0))
    fig, ax = style.create_figure(kind="double", height_mm=height_mm, aspect=0.55)

    image = ax.imshow(
        values,
        aspect="auto",
        cmap=_impact_cmap(),
        norm=TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax),
        zorder=1,
    )

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns.astype(str), rotation=35, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index.astype(str))

    ax.set_xticks(np.arange(-0.5, len(pivot.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(pivot.index), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.6)
    ax.tick_params(which="minor", bottom=False, left=False)

    if annotate is None:
        annotate = values.size <= 60 and metric in {"FI", "FBI"} and not use_signed_log

    if annotate:
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                value = values[i, j]
                label = f"{value:.1f}" if metric in {"FI", "FBI"} else f"{value:.1e}"
                color = "white" if abs(value) > 0.55 * vmax else "black"
                ax.text(
                    j,
                    i,
                    label,
                    ha="center",
                    va="center",
                    fontsize=max(style.min_fontsize - 1.0, 5.0),
                    color=color,
                )

    _apply_academic_axes(
        ax,
        style,
        xlabel="Cycle",
        ylabel="KX",
        title=f"{metric} impact heatmap — top {top_k} KX",
        show_xgrid=False,
    )

    cbar = fig.colorbar(image, ax=ax, shrink=0.88, pad=0.02)
    cbar.set_label(_metric_label(metric, use_signed_log), fontsize=style.base_fontsize)
    cbar.ax.tick_params(labelsize=style.min_fontsize, width=style.axis_width, length=style.tick_length)
    cbar.outline.set_linewidth(style.axis_width)

    fig.canvas.draw_idle()
    return ax


def plot_impact_summary_bar(
    summary: pd.DataFrame,
    metric: str = "FI_mean",
    top_k: int = 15,
    style: Optional[NatureFigureStyle] = None,
    annotate_extremes: bool = True,
):
    """Plot a modern compact summary bar chart from a KX summary table."""
    style = _style_or_default(style)

    if summary.empty or metric not in summary.columns:
        fig, ax = style.create_figure(kind="double", height_mm=55.0)
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    data = summary.copy()
    data["_abs_metric"] = data[metric].abs()
    data = data.sort_values("_abs_metric", ascending=False).head(top_k)
    data = data.sort_values(metric, ascending=True)

    height_mm = max(70.0, 6.5 * len(data) + 30.0)
    fig, ax = style.create_figure(kind="double", height_mm=height_mm, aspect=0.55)

    values = data[metric].to_numpy(dtype=float)
    colors = _bar_colors(values)
    ax.barh(
        data["kx"].astype(str),
        values,
        color=colors,
        edgecolor="white",
        linewidth=0.4,
        alpha=0.92,
        zorder=2,
    )
    ax.scatter(
        values,
        np.arange(len(values)),
        s=22,
        c=colors,
        edgecolors="white",
        linewidths=0.7,
        zorder=4,
    )

    max_abs = float(np.nanmax(np.abs(values))) if values.size else 1.0
    if not np.isfinite(max_abs) or max_abs == 0:
        max_abs = 1.0
    ax.set_xlim(-1.18 * max_abs, 1.18 * max_abs)
    _shade_negative_side(ax)
    ax.axvline(0.0, color="black", linewidth=0.7, zorder=3)

    xlabel = metric
    if metric in {"FI_mean", "FI_min", "FI_max", "FBI_mean", "FBI_min", "FBI_max"}:
        xlabel = f"{metric} (%)"

    _apply_academic_axes(
        ax,
        style,
        xlabel=xlabel,
        ylabel="KX",
        title=f"Summary impact — top {top_k} KX by |{metric}|",
        show_xgrid=True,
    )

    if metric.startswith("TI"):
        _format_scientific_x(ax)

    if annotate_extremes:
        tmp = data.copy()
        tmp["_summary_metric"] = tmp[metric]
        tmp["kx"] = data["kx"].astype(int)
        _annotate_extremes(
            ax,
            tmp,
            "_summary_metric",
            metric,
            False,
            style,
        )

    fig.canvas.draw_idle()
    return ax


def save_impact_figure(
    ax_or_fig,
    filename: str | Path,
    style: Optional[NatureFigureStyle] = None,
    mode: str = "main",
    validate: bool = False,
) -> list[str]:
    """Save an impact figure using the style exporter."""
    style = _style_or_default(style)

    fig = ax_or_fig
    if hasattr(ax_or_fig, "figure"):
        fig = ax_or_fig.figure

    return style.export(fig, filename, mode=mode, validate=validate)
