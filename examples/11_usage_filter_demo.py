#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/11_usage_filter_demo.py

End-to-end demo for the GSI usage helpers added to `readDiag.utils`:
- decode_iuse: human-friendly reason/category for `iuse` (pre-analysis)
- attach_iuse_decoded: adds `iuse_label` and `iuse_category` to a DataFrame
- apply_usage_filter: canonical filters for pre/post usage

Works on conventional diagnostics (conv).

Usage examples:
  # Inspect UV over a few KX and show "assimilated" points (post-analysis)
  python examples/11_usage_filter_demo.py \
    --file data/diag_conv_01.2024013018 \
    --var uv --kx 254 242 221 \
    --mode post:assimilated --limit 15 --save-csv

  # Inspect pressure & temperature, pre-analysis usable, with extra QC mask
  python examples/11_usage_filter_demo.py \
    --file data/diag_conv_01.2024013018 \
    --var ps t --mode pre:used --mask "iqc==0" --limit 10

  # Just print distributions without filtering
  python examples/11_usage_filter_demo.py \
    --file data/diag_conv_01.2024013018 \
    --var uv ps t q --mode all --limit 5
"""
from __future__ import annotations

import argparse
from typing import List, Tuple, Optional
from pathlib import Path
import sys

import pandas as pd
import matplotlib.pyplot as plt

try:
    from readDiag import diagAccess
    from readDiag.utils import (
        attach_iuse_decoded,
        apply_usage_filter,
    )
except Exception as e:
    print("[fatal] Could not import readDiag (diagAccess/utils). Is the package on PYTHONPATH?", file=sys.stderr)
    raise

def available_kx(diag, var: str) -> list[int]:
    fn = getattr(diag, "get_kx_list", None)
    if callable(fn):
        try: return [int(k) for k in fn(var)]
        except Exception: pass
    d = diag.get_data_frame().get(var, {})
    return [int(k) for k in d.keys()] if isinstance(d, dict) else []

def get_df(diag, var: str, kx: int) -> pd.DataFrame:
    if hasattr(diag, "get_dataframe"):
        return diag.get_dataframe(var, kx)
    return diag.get_data_frame()[var][kx]

def value_counts_safe(df: pd.DataFrame, col: str, top: int = 10) -> str:
    if col not in df.columns:
        return f"(no column '{col}')"
    s = df[col].value_counts(dropna=False).head(top)
    return s.to_string()

def quick_scatter(df: pd.DataFrame, out: Optional[Path] = None, title: str = "") -> None:
    """Minimal lon/lat scatter (no basemap) for a fast visual sanity-check."""
    if not {"lon","lat"}.issubset(df.columns) or df.empty:
        return
    fig = plt.figure(figsize=(8,4))
    ax = fig.add_subplot(1,1,1)
    ax.scatter(df["lon"].to_numpy(), df["lat"].to_numpy(), s=4, alpha=0.5, linewidths=0)
    ax.set_xlim([-180,180]); ax.set_ylim([-90,90])
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude"); ax.set_title(title or "lon/lat")
    fig.tight_layout()
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=140)
        print(f"[saved] {out}")
    plt.close(fig)

def main() -> None:
    ap = argparse.ArgumentParser(description="Demo: decode_iuse / attach_iuse_decoded / apply_usage_filter")
    ap.add_argument("--file", default="data/diag_conv_01.2024013018", help="Path to diag_conv_* file")
    ap.add_argument("--var", nargs="*", default=["uv"], help="Variables to inspect (e.g., uv ps t q)")
    ap.add_argument("--kx", nargs="*", type=int, default=None, help="KX list; default: all available per var")
    ap.add_argument("--mode", default="all",
                    choices=("all","pre:used","pre:monitored","post:assimilated","post:monitored"),
                    help="Usage filter mode (pre/post). See README in utils.")
    ap.add_argument("--stage", default="auto", choices=("auto","pre","post"),
                    help="Stage hint for column detection (usually keep 'auto').")
    ap.add_argument("--field", default="auto", choices=("auto","iuse","use","iusev","analysis_use"),
                    help="Force a specific column if desired.")
    ap.add_argument("--mask", default=None, help="Extra pandas.query mask after usage filtering, e.g. 'iqc==0'")
    ap.add_argument("--limit", type=int, default=10, help="Rows to preview per var/KX for head()")
    ap.add_argument("--outdir", default="outputs/usage_demo", help="Where to save CSV/plots if requested")
    ap.add_argument("--save-csv", action="store_true", help="Save filtered head() CSVs")
    ap.add_argument("--save-plot", action="store_true", help="Save a minimal lon/lat scatter (no basemap)")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    if args.save_csv or args.save_plot:
        outdir.mkdir(parents=True, exist_ok=True)

    d = diagAccess(args.file)
    print(f"[info] file: {args.file}")
    print(f"[info] vars: {args.var} | mode={args.mode} | stage={args.stage} | field={args.field} | mask={args.mask}")

    for var in args.var:
        kxs = available_kx(d, var)
        if args.kx:
            kxs = [k for k in args.kx if k in kxs]
        print("\n" + "="*80)
        print(f"[var] {var} | KX available: {kxs}")
        if not kxs:
            print(f"[warn] var={var}: no KX found")
            continue

        for kx in kxs:
            try:
                df0 = get_df(d, var, kx)
            except Exception as e:
                print(f"[skip] var={var} kx={kx}: cannot read dataframe ({e})")
                continue

            print(f"\n[var={var} kx={kx}] shape={df0.shape}")
            # Distributions: iuse / iusev / use
            print("  iuse  counts:"); print("  " + value_counts_safe(df0, "iuse").replace("\n", "\n  "))
            print("  iusev counts:"); print("  " + value_counts_safe(df0, "iusev").replace("\n", "\n  "))
            print("  use   counts:"); print("  " + value_counts_safe(df0, "use").replace("\n", "\n  "))

            # Attach human labels for iuse (pre stage)
            df_lbl = attach_iuse_decoded(df0) if "iuse" in df0.columns else df0
            if "iuse_category" in df_lbl.columns:
                cat_counts = df_lbl["iuse_category"].value_counts(dropna=False)
                print("  iuse_category:")
                print("  " + cat_counts.to_string().replace("\n","\n  "))

            # Apply usage filter (pre/post)
            df_f, used_col = apply_usage_filter(df0, mode=args.mode, stage=args.stage, field=args.field)
            if args.mask:
                try:
                    df_f = df_f.query(args.mask)
                except Exception as e:
                    print(f"  [mask-error] {e}")
            print(f"  after usage='{args.mode}' (col={used_col}) & mask='{args.mask}': {len(df_f)} rows")

            # head preview
            if not df_f.empty:
                cols_pref = [c for c in ["lat","lon","iuse","iusev","use","iqc","omf","oma","end_err"] if c in df_f.columns]
                print(f"  head({args.limit}):")
                try:
                    print(df_f[cols_pref].head(args.limit).to_string(index=False))
                except Exception:
                    print(df_f.head(args.limit).to_string(index=False))

                if args.save_csv:
                    out = outdir / f"{var}_kx{kx}_head.csv"
                    df_f.head(args.limit).to_csv(out, index=False)
                    print(f"  [saved] {out}")

                if args.save_plot:
                    png = outdir / f"{var}_kx{kx}_scatter.png"
                    quick_scatter(df_f, out=png, title=f"{var} kx={kx} ({args.mode})")

    print("\n[done]")

if __name__ == "__main__":
    main()
