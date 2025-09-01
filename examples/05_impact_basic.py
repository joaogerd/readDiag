#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/05_impact_basic.py

Compute and plot TI/FI/FBI for a single OMF/OMA pair.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import ImpactAnalyzer

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--omf", required=True, help="*_01.YYYYMMDDHH")
    ap.add_argument("--oma", required=True, help="*_03.YYYYMMDDHH")
    ap.add_argument("--var", default=None, help="conv var (e.g. t, uv) or None for rad")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    ia = ImpactAnalyzer.from_pair(args.omf, args.oma, var=args.var)
    df = ia.compute_all_metrics()
    df.to_csv(outdir/"impact_metrics.csv", index=False)

    for metric in ("TI","FI","FBI"):
        ax = ia.plot_impact_bar(metric=metric, top_k=12, title=f"{metric} (top-12)")
        if args.save:
            ax.figure.savefig(outdir/f"impact_{metric.lower()}_bar.png", bbox_inches="tight")

    if not args.save:
        plt.show()
    plt.close("all")

if __name__ == "__main__":
    main()
