#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import ImpactAnalyzer, ExperimentComparator, ComparisonPlotter
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=["data/diag_conv_01.2024013018", "data/diag_conv_03.2024013018", "data/diag_conv_01.2024013018", "data/diag_conv_03.2024013018"])
    ap.add_argument("--var", default="t")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    toks = a.pairs; analyzers=[]; pairs=[]
    if len(toks)%2: raise SystemExit("pairs must be even length")
    for i in range(0,len(toks),2):
        omf,oma=toks[i],toks[i+1]
        analyzers.append(ImpactAnalyzer.from_pair(omf,oma,var=a.var))
        pairs.append((omf,oma))
    ax = analyzers[0].plot_metric_series(analyzers, label="EXP", metric="TI")
    if a.save: ax.figure.savefig(outdir/"impact_ti_series.png", bbox_inches="tight")
    if len(pairs)>1:
        half=len(pairs)//2 or 1
        comp = ExperimentComparator(pairs[:half], pairs[half:], var=a.var)
        comp.compare(); ax = ComparisonPlotter(comp.comparison_df).plot_diff(metric="mean_diff")
        if a.save: ax.figure.savefig(outdir/"impact_comparison.png", bbox_inches="tight")
    if not a.save: plt.show(); plt.close("all")
if __name__ == "__main__": main()
