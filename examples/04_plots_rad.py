#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/04_plots_rad.py

Radiance plotting gallery.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import diagAccess, diagPlotter

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-deep")

    d = diagAccess(args.file)
    p = diagPlotter(d)

    figs = []
    figs.append(p.plot_channel_stats_rad(metric="omf", agg="mean").figure)
    figs.append(p.plot_channel_stats_rad(metric="omf", agg="std").figure)
    figs.append(p.plot_omf_distribution_rad(channel_index=0, corrected=False, bins=50).figure)

    if args.save:
        names = ["rad_mean_omf","rad_std_omf","rad_ch0_hist_omf"]
        for f, n in zip(figs, names):
            f.savefig(outdir/f"{n}.png", bbox_inches="tight")
    else:
        plt.show()
    plt.close("all")

if __name__ == "__main__":
    main()
