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
    a = ap.parse_args()
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-deep")
    d = diagAccess(a.file); p = diagPlotter(d)
    var = d.get_variables()[0]; kx = int(d.get_kx_list(var)[0])
    figs = [p.plot_kx_count().figure,
            p.plot_variable_count(var, column="iuse").figure,
            p.plot_hist_conv(var, kx, col="omf", bins=60).figure]
    try: figs.append(p.plot_spatial_conv(var, kx, param="omf", mask="iuse==1").figure)
    except Exception as e: print("[warn] spatial skipped:", e)
    if a.save:
        for f,n in zip(figs, ["conv_kx_count","conv_value_counts","conv_hist","conv_spatial"]):
            f.savefig(outdir/f"{n}.png", bbox_inches="tight")
    else: plt.show()
    plt.close("all")
if __name__ == "__main__": main()
