#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/02_quickstart_rad.py

Minimal radiance diagnostics quickstart.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import diagAccess, diagPlotter, PlotConfig

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Path to diag_amsua_*_01.*")
    ap.add_argument("--outdir", default="outputs/examples", help="Output dir")
    ap.add_argument("--save", action="store_true", help="Save instead of show")
    args = ap.parse_args()

    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-deep")

    d = diagAccess(args.file)
    p = diagPlotter(d)

    ax = p.plot_channel_stats_rad(metric="omf", agg="mean")
    ax.set_title("Mean OMF per channel")
    if args.save: ax.figure.savefig(Path(args.outdir)/"qx_rad_channel_mean_omf.png", bbox_inches="tight")

    ax = p.plot_omf_distribution_rad(channel_index=0, corrected=False, bins=50)
    ax.set_title("O–F distribution (ch 0)")
    if args.save: ax.figure.savefig(Path(args.outdir)/"qx_rad_ch0_hist_omf.png", bbox_inches="tight")

    if not args.save:
        plt.show()
    plt.close("all")

if __name__ == "__main__":
    main()
