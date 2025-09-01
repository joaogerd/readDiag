#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/kitchen_sink.py

A single, end-to-end example showcasing the main features of the refactored
readDiag package: reading, plotting (conv & rad), impact metrics (TI/FI/FBI),
legacy compatibility, and centralized plotting style.

Run:
  python examples/kitchen_sink.py \
      --conv data/diag_conv_01.2020010100 \
      --rad data/diag_amsua_n15_01.2020010100 \
      --impact-omf data/diag_conv_01.2020010100 \
      --impact-oma data/diag_conv_03.2020010100 \
      --outdir outputs/examples --save

Notes:
  - The spatial map requires `cartopy` installed.
  - Paths above are examples; adapt them to your local layout.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt

# Import the public API from your package
# If running this file standalone, ensure the project root is on sys.path
from readDiag import (
    read_any,          # autodetects conv/rad
    diagAccess,        # modern accessor
    diagPlotter,       # modern plotting wrapper
    PlotConfig,        # central plot styling
    ImpactAnalyzer,    # TI/FI/FBI metrics & plots
    ExperimentComparator,
    ComparisonPlotter,
    read_diag,         # legacy wrapper (deprecated; kept for compat)
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_outdir(path: str | Path) -> Path:
    outdir = Path(path).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def _setup_style() -> PlotConfig:
    """Apply a consistent style using PlotConfig.
    
    Returns:
        PlotConfig: The applied configuration (useful if you want to reuse).
    """
    cfg = PlotConfig(
        style="seaborn-v0_8-deep",
        rc_params={
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "grid.linestyle": ":",
            "grid.color": "#BBBBBB",
            "grid.linewidth": 0.8,
            "figure.dpi": 110,
        },
        show_spines=True,
        spines_sides=["left", "bottom"],
        zero_line_kwargs={"y": 0.0, "ls": "--", "c": "gray", "alpha": 0.6},
    )
    plt.style.use(cfg.style)
    plt.rcParams.update(cfg.rc_params)
    return cfg


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def section_read_and_export(conv_file: Optional[str], rad_file: Optional[str], outdir: Path) -> None:
    """Read conv/rad using read_any and diagAccess, and export illustrative CSVs."""
    if conv_file:
        print(f"[read] conventional → {conv_file}")
        conv = diagAccess(conv_file)
        # Use the first var/kx available as a demo slice:
        var = conv.get_variables()[0]
        kx = int(conv.get_kx_list(var)[0])
        csv_path = outdir / f"conv_slice_{var}_kx{kx}.csv"
        conv.export_to_csv(csv_path, var=var, kx=kx)
        print(f"[export] wrote {csv_path}")
    if rad_file:
        print(f"[read] radiance → {rad_file}")
        rad = diagAccess(rad_file)
        csv_path = outdir / "rad_channel0.csv"
        rad.export_to_csv(csv_path, channel=0)
        print(f"[export] wrote {csv_path}")


def section_conv_plots(conv_file: Optional[str], outdir: Path, save: bool) -> None:
    """Conventional plots: kx counts, variable counts, hist per kx/col, spatial map (cartopy)."""
    if not conv_file:
        return
    d = diagAccess(conv_file)
    p = diagPlotter(d)

    var = d.get_variables()[0]
    kx = int(d.get_kx_list(var)[0])

    # 1) total obs per KX (stacked if multiple variables)
    ax = p.plot_kx_count()
    ax.set_title("Total observations per KX (stacked)")
    if save:
        ax.figure.savefig(outdir / "conv_kx_count.png", bbox_inches="tight")

    # 2) counts per categorical column for a given variable
    ax = p.plot_variable_count(var, column="iuse")
    ax.set_title(f"{var}: counts of 'iuse'")
    if save:
        ax.figure.savefig(outdir / f"conv_value_counts_{var}_iuse.png", bbox_inches="tight")

    # 3) histogram for a numeric column in a given KX
    ax = p.plot_hist_conv(var, kx, col="omf", bins=60, title=f"Histogram {var}/kx={kx} (omf)")
    if save:
        ax.figure.savefig(outdir / f"conv_hist_{var}_kx{kx}_omf.png", bbox_inches="tight")

    # 4) spatial map (requires cartopy)
    try:
        ax = p.plot_spatial_conv(var, kx, param="omf", mask="iuse == 1")
        if save:
            ax.figure.savefig(outdir / f"conv_spatial_{var}_kx{kx}_omf.png", bbox_inches="tight")
    except Exception as e:
        print(f"[conv] Skipping spatial map (cartopy/data columns missing): {e}")


def section_rad_plots(rad_file: Optional[str], outdir: Path, save: bool) -> None:
    """Radiance plots: per-channel stats and O–F histogram by channel."""
    if not rad_file:
        return
    d = diagAccess(rad_file)
    p = diagPlotter(d)

    ax = p.plot_channel_stats_rad(metric="omf", agg="mean")
    ax.set_title("Radiance: mean OMF per channel")
    if save:
        ax.figure.savefig(outdir / "rad_channel_mean_omf.png", bbox_inches="tight")

    ax = p.plot_omf_distribution_rad(channel_index=0, corrected=False, bins=50)
    ax.set_title("Radiance: O–F distribution (ch 0)")
    if save:
        ax.figure.savefig(outdir / "rad_channel0_hist_omf.png", bbox_inches="tight")


def section_impact(omf_file: Optional[str], oma_file: Optional[str], outdir: Path, save: bool) -> None:
    """Impact examples: single analyzer, series (mean±std), and multi-experiment compare."""
    if not (omf_file and oma_file):
        return

    # Choose var automatically for conv (optional)
    var = "t" if "conv" in Path(omf_file).name else None
    ia = ImpactAnalyzer.from_pair(omf_file, oma_file, var=var)

    # table with all metrics
    df = ia.compute_all_metrics()
    df.to_csv(outdir / "impact_metrics.csv", index=False)

    # 1) bar plot for TI (top 12)
    ax = ia.plot_impact_bar(metric="TI", top_k=12, title="Total Impact (top-12)")
    if save:
        ax.figure.savefig(outdir / "impact_ti_bar.png", bbox_inches="tight")

    # 2) demo series (reusing the same analyzer three times just for layout)
    ax = ia.plot_metric_series([ia, ia, ia], label="Demo EXP", metric="TI")
    if save:
        ax.figure.savefig(outdir / "impact_ti_series.png", bbox_inches="tight")

    # 3) multi-experiment comparator (demo: IA vs IA again)
    comp = ExperimentComparator([(omf_file, oma_file)], [(omf_file, oma_file)], var=var)
    comp.compare()
    plotter = ComparisonPlotter(comp.comparison_df)
    ax = plotter.plot_diff(metric="mean_diff")
    ax.set_title("Experiment comparison (demo)")
    if save:
        ax.figure.savefig(outdir / "impact_comparison_demo.png", bbox_inches="tight")


def section_legacy(any_file: Optional[str], outdir: Path, save: bool) -> None:
    """Legacy compat: read_diag(...).plot/ptmap/pvmap"""
    if not any_file:
        return
    r = read_diag(any_file)  # deprecated legacy shim
    try:
        var = r.get_variables()[0]
    except Exception:
        var = None

    # plot() (often mapped to observation counts for a variable)
    try:
        ax = r.plot(var) if var else r.plot()
        ax.set_title("legacy.plot(...)")
        if save:
            ax.figure.savefig(outdir / "legacy_plot.png", bbox_inches="tight")
    except Exception as e:
        print(f"[legacy] plot skipped: {e}")

    # ptmap/pvmap may require specific columns. Try both guarded.
    for fn_name in ("ptmap", "pvmap"):
        try:
            fn = getattr(r, fn_name, None)
            if fn is None:
                continue
            ax = fn(var) if var else fn()
            ax.set_title(f"legacy.{fn_name}(...)")
            if save:
                ax.figure.savefig(outdir / f"legacy_{fn_name}.png", bbox_inches="tight")
        except Exception as e:
            print(f"[legacy] {fn_name} skipped: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="All-in-one readDiag example")
    p.add_argument("--conv", type=str, help="Path to a conventional diag file")
    p.add_argument("--rad", type=str, help="Path to a radiance diag file")
    p.add_argument("--impact-omf", type=str, help="Path to diag OMF (e.g., *_01.YYYYMMDDHH)")
    p.add_argument("--impact-oma", type=str, help="Path to diag OMA (e.g., *_03.YYYYMMDDHH)")
    p.add_argument("--outdir", type=str, default="outputs/examples", help="Output directory")
    p.add_argument("--save", action="store_true", help="Save plots instead of showing them")
    return p


def main() -> None:
    args = build_parser().parse_args()
    outdir = _ensure_outdir(args.outdir)
    _ = _setup_style()

    # 1) Read & export
    section_read_and_export(args.conv, args.rad, outdir)

    # 2) Conventional plots
    section_conv_plots(args.conv, outdir, args.save)

    # 3) Radiance plots
    section_rad_plots(args.rad, outdir, args.save)

    # 4) Impact (TI/FI/FBI)
    section_impact(args.impact_omf, args.impact_oma, outdir, args.save)

    # 5) Legacy compat
    any_file = args.conv or args.rad or args.impact_omf or args.impact_oma
    section_legacy(any_file, outdir, args.save)

    # Show if not saving
    if not args.save:
        plt.show()
    plt.close("all")
    print(f"[done] outputs → {outdir}")


if __name__ == "__main__":
    main()
