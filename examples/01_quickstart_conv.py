#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/01_quickstart_conv.py

Minimal conventional diagnostics quickstart.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import open_diagnostic, diagPlotter, PlotConfig

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Path to diag_conv_01.*")
    ap.add_argument("--outdir", default="outputs/examples", help="Output dir")
    ap.add_argument("--save", action="store_true", help="Save instead of show")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # Style
    cfg = PlotConfig(style="seaborn-v0_8-deep")
    plt.style.use(cfg.style)

    d = open_diagnostic(args.file)
    p = diagPlotter(d)

    var = d.get_variables()[0]
    kx = int(d.get_kx_list(var)[0])

    ax = p.plot_kx_count(); ax.set_title("Obs per KX")
    if args.save: ax.figure.savefig(outdir/"qx_conv_kx_count.png", bbox_inches="tight")

    ax = p.plot_hist_conv(var, kx, col="omf", bins=50, title=f"{var}/kx={kx} O–F")
    if args.save: ax.figure.savefig(outdir/f"qx_conv_hist_{var}_kx{kx}.png", bbox_inches="tight")

    try:
        ax = p.plot_spatial_conv(var, kx, param="omf", mask="iuse == 1")
        if args.save: ax.figure.savefig(outdir/f"qx_conv_spatial_{var}_kx{kx}.png", bbox_inches="tight")
    except Exception as e:
        print(f"[warn] spatial skipped: {e}")

    if not args.save:
        plt.show()
    plt.close("all")

if __name__ == "__main__":
    main()
