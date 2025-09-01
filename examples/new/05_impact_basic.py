#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import ImpactAnalyzer
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--omf", default="data/diag_conv_01.2024013018")
    ap.add_argument("--oma", default="data/diag_conv_03.2024013018")
    ap.add_argument("--var", default="t")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    ia = ImpactAnalyzer.from_pair(a.omf, a.oma, var=a.var)
    df = ia.compute_all_metrics(); df.to_csv(outdir/"impact_metrics.csv", index=False)
    for metric in ("TI","FI","FBI"):
        ax = ia.plot_impact_bar(metric=metric, top_k=12, title=f"{metric} (top-12)")
        if a.save: ax.figure.savefig(outdir/f"impact_{metric.lower()}_bar.png", bbox_inches="tight")
    if not a.save: plt.show(); plt.close("all")
if __name__ == "__main__": main()
