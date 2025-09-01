#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import (
    read_any, diagAccess, diagPlotter, PlotConfig,
    ImpactAnalyzer, ExperimentComparator, ComparisonPlotter, read_diag
)

def _ensure_outdir(p: str|Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def _style():
    cfg = PlotConfig(style="seaborn-v0_8-deep",
                     rc_params={"figure.dpi":110},
                     zero_line_kwargs={"y":0,"ls":"--","c":"gray","alpha":0.6})
    plt.style.use(cfg.style); plt.rcParams.update(cfg.rc_params)

def read_and_export(conv, rad, outdir: Path):
    if conv:
        d = diagAccess(conv)
        var = d.get_variables()[0]; kx = int(d.get_kx_list(var)[0])
        d.export_to_csv(outdir/f"conv_slice_{var}_kx{kx}.csv", var=var, kx=kx)
    if rad:
        d = diagAccess(rad)
        d.export_to_csv(outdir/"rad_channel0.csv", channel=0)

def conv_plots(conv, outdir: Path, save: bool):
    if not conv: return
    d = diagAccess(conv); p = diagPlotter(d)
    var = d.get_variables()[0]; kx = int(d.get_kx_list(var)[0])
    figs = [
        p.plot_kx_count().figure,
        p.plot_variable_count(var, column="iuse").figure,
        p.plot_hist_conv(var, kx, col="omf", bins=60).figure,
    ]
    try: figs.append(p.plot_spatial_conv(var, kx, param="omf", mask="iuse==1").figure)
    except Exception as e: print("[conv] spatial skipped:", e)
    if save:
        names = ["conv_kx_count","conv_value_counts","conv_hist","conv_spatial"]
        for f,n in zip(figs, names): f.savefig(outdir/f"{n}.png", bbox_inches="tight")

def rad_plots(rad, outdir: Path, save: bool):
    if not rad: return
    d = diagAccess(rad); p = diagPlotter(d)
    figs = [
        p.plot_channel_stats_rad(metric="omf", agg="mean").figure,
        p.plot_omf_distribution_rad(channel_index=0, corrected=False, bins=50).figure,
    ]
    if save:
        names = ["rad_channel_mean_omf","rad_channel0_hist_omf"]
        for f,n in zip(figs, names): f.savefig(outdir/f"{n}.png", bbox_inches="tight")

def impact(omf, oma, outdir: Path, save: bool):
    if not (omf and oma): return
    ia = ImpactAnalyzer.from_pair(omf, oma, var="t")
    df = ia.compute_all_metrics(); df.to_csv(outdir/"impact_metrics.csv", index=False)
    ax = ia.plot_impact_bar(metric="TI", top_k=12, title="Total Impact (top-12)")
    if save: ax.figure.savefig(outdir/"impact_ti_bar.png", bbox_inches="tight")
    ax = ia.plot_metric_series([ia, ia, ia], label="Demo EXP", metric="TI")
    if save: ax.figure.savefig(outdir/"impact_ti_series.png", bbox_inches="tight")
    comp = ExperimentComparator([(omf, oma)], [(omf, oma)], var="t"); comp.compare()
    ax = ComparisonPlotter(comp.comparison_df).plot_diff(metric="mean_diff")
    if save: ax.figure.savefig(outdir/"impact_comparison_demo.png", bbox_inches="tight")

def legacy(any_file, outdir: Path, save: bool):
    if not any_file: return
    r = read_diag(any_file)
    try: var = r.get_variables()[0]
    except Exception: var = None
    for name in ("plot","ptmap","pvmap"):
        fn = getattr(r, name, None)
        if not fn: continue
        try:
            ax = fn(var) if var else fn()
            if save: ax.figure.savefig(outdir/f"legacy_{name}.png", bbox_inches="tight")
        except Exception as e:
            print(f"[legacy] {name} skipped:", e)

def main():
    ap = argparse.ArgumentParser(description="Kitchen sink")
    ap.add_argument("--conv", default="data/diag_conv_01.2024013018")
    ap.add_argument("--rad", default="data/diag_amsua_n19_01.2024013018")
    ap.add_argument("--impact-omf", default="data/diag_conv_01.2024013018")
    ap.add_argument("--impact-oma", default="data/diag_conv_03.2024013018")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    outdir = _ensure_outdir(args.outdir); _style()
    read_and_export(args.conv, args.rad, outdir)
    conv_plots(args.conv, outdir, args.save)
    rad_plots(args.rad, outdir, args.save)
    impact(args.impact_omf, args.impact_oma, outdir, args.save)
    legacy(args.conv or args.rad or args.impact_omf or args.impact_oma, outdir, args.save)
    if not args.save: plt.show(); plt.close("all")
    print("[done]", outdir)

if __name__ == "__main__":
    main()
