#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import diagAccess, diagPlotter
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/diag_conv_01.2024013018")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args(); Path(a.outdir).mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-deep")
    d = diagAccess(a.file); p = diagPlotter(d)
    var = d.get_variables()[0]; kx = int(d.get_kx_list(var)[0])
    ax = p.plot_kx_count()
    if a.save: ax.figure.savefig(Path(a.outdir)/"qx_conv_kx_count.png", bbox_inches="tight")
    ax = p.plot_hist_conv(var, kx, col="omf", bins=50, title=f"{var}/kx={kx} O–F")
    if a.save: ax.figure.savefig(Path(a.outdir)/f"qx_conv_hist_{var}_kx{kx}.png", bbox_inches="tight")
    try:
        ax = p.plot_spatial_conv(var, kx, param="omf", mask="iuse == 1")
        if a.save: ax.figure.savefig(Path(a.outdir)/f"qx_conv_spatial_{var}_kx{kx}.png", bbox_inches="tight")
    except Exception as e: print("[warn] spatial skipped:", e)
    if not a.save: plt.show(); plt.close("all")
if __name__ == "__main__": main()
