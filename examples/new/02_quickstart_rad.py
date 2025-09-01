#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import diagAccess, diagPlotter
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/diag_amsua_n19_01.2024013018")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args(); Path(a.outdir).mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-deep")
    d = diagAccess(a.file); p = diagPlotter(d)
    ax = p.plot_channel_stats_rad(metric="omf", agg="mean")
    if a.save: ax.figure.savefig(Path(a.outdir)/"qx_rad_channel_mean_omf.png", bbox_inches="tight")
    ax = p.plot_omf_distribution_rad(channel_index=0, corrected=False, bins=50)
    if a.save: ax.figure.savefig(Path(a.outdir)/"qx_rad_ch0_hist_omf.png", bbox_inches="tight")
    if not a.save: plt.show(); plt.close("all")
if __name__ == "__main__": main()
