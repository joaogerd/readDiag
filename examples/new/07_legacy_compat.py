#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from readDiag import read_diag
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/diag_conv_01.2024013018")
    ap.add_argument("--outdir", default="outputs/examples")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    r = read_diag(a.file)
    try: var = r.get_variables()[0]
    except Exception: var=None
    for name in ("plot","ptmap","pvmap"):
        fn=getattr(r,name,None)
        if not fn: continue
        try:
            ax = fn(var) if var else fn()
            if a.save: ax.figure.savefig(outdir/f"legacy_{name}.png", bbox_inches="tight")
        except Exception as e: print(f"[warn] {name} skipped:", e)
    if not a.save: plt.show(); plt.close("all")
if __name__ == "__main__": main()
