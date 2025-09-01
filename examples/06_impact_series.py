#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/06_impact_series.py

Mean±std series and multi-experiment comparison.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import ImpactAnalyzer, ExperimentComparator, ComparisonPlotter

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", required=True,
                    help="List like OMF1 OMA1 OMF2 OMA2 ... (must be even length)")
    ap.add_argument("--var", default=None)
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # Build analyzers from pairs
    toks = args.pairs
    if len(toks) % 2 != 0:
        raise SystemExit("pairs must be even length: OMF1 OMA1 OMF2 OMA2 ...")

    analyzers = []
    file_pairs = []
    for i in range(0, len(toks), 2):
        omf, oma = toks[i], toks[i+1]
        analyzers.append(ImpactAnalyzer.from_pair(omf, oma, var=args.var))
        file_pairs.append((omf, oma))

    # Series plot (re-using analyzers as a pseudo-series)
    ax = analyzers[0].plot_metric_series(analyzers, label="EXP", metric="TI")
    if args.save:
        ax.figure.savefig(outdir/"impact_ti_series.png", bbox_inches="tight")

    # Multi-experiment demo: compare first half vs second half, if possible
    half = len(file_pairs)//2 or 1
    exp1, exp2 = file_pairs[:half], file_pairs[half:]
    if exp2:
        comp = ExperimentComparator(exp1, exp2, var=args.var)
        comp.compare()
        plotter = ComparisonPlotter(comp.comparison_df)
        ax = plotter.plot_diff(metric="mean_diff")
        ax.set_title("Experiment comparison")
        if args.save:
            ax.figure.savefig(outdir/"impact_comparison.png", bbox_inches="tight")

    if not args.save:
        plt.show()
    plt.close("all")

if __name__ == "__main__":
    main()
