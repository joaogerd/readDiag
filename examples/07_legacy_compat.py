#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/07_legacy_compat.py

Show legacy compatibility layer: read_diag(...).plot/ptmap/pvmap.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import read_diag

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Any supported diag file")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    r = read_diag(args.file)
    try:
        var = r.get_variables()[0]
    except Exception:
        var = None

    for name in ("plot","ptmap","pvmap"):
        fn = getattr(r, name, None)
        if fn is None:
            continue
        try:
            ax = fn(var) if var else fn()
            ax.set_title(f"legacy.{name}(...)")
            if args.save:
                ax.figure.savefig(outdir/f"legacy_{name}.png", bbox_inches="tight")
        except Exception as e:
            print(f"[warn] {name} skipped: {e}")

    if not args.save:
        plt.show()
    plt.close("all")

if __name__ == "__main__":
    main()
