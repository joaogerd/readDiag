#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/03_plots_conv.py

Conventional plotting gallery.
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

    var = d.get_variables()[0]
    kx = int(d.get_kx_list(var)[0])

    figs = []
    figs.append(p.plot_kx_count().figure)
    figs.append(p.plot_variable_count(var, column="iuse").figure)
    figs.append(p.plot_hist_conv(var, kx, col="omf", bins=60).figure)
    try:
        figs.append(p.plot_spatial_conv(var, kx, param="omf", mask="iuse==1").figure)
    except Exception as e:
        print(f"[warn] spatial skipped: {e}")

    if args.save:
        names = ["conv_kx_count","conv_value_counts","conv_hist","conv_spatial"]
        for f, n in zip(figs, names):
            f.savefig(outdir/f"{n}.png", bbox_inches="tight")
    else:
        plt.show()
    plt.close("all")

if __name__ == "__main__":
    main()
