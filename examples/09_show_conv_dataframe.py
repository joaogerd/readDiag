#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/09_show_conv_dataframe.py

Inspect conventional diagnostics (conv): list variables/KX, show DataFrame heads,
filter by usage (all/used/monitored) using either iuse or iusev (auto-detected),
and (optionally) save CSV samples.

Usage examples:
  python examples/09_show_conv_dataframe.py --file data/diag_conv_01.2024013018 --var uv --usage used --usage-field auto --mask "iqc==0" --limit 10 --save-csv
  python examples/09_show_conv_dataframe.py --file data/diag_conv_01.2024013018 --var uv ps t q --usage all --limit 5
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from typing import List
from pathlib import Path
import sys
import pandas as pd

try:
    from readDiag import diagAccess
except Exception as e:
    print("[fatal] Could not import readDiag.diagAccess:", e, file=sys.stderr)
    sys.exit(1)


@dataclass
class Args:
    file: str
    var: List[str] | None
    kx: List[int] | None
    usage: str
    usage_field: str
    mask: str | None
    limit: int
    outdir: str
    save_csv: bool


def parse_args() -> Args:
    ap = argparse.ArgumentParser(description="Show conv DataFrames (per var/KX)")
    ap.add_argument("--file", default="data/diag_conv_01.2024013018",
                    help="Path to diag_conv_* file")
    ap.add_argument("--var", nargs="*", default=None,
                    help="Variables to inspect (e.g., uv ps t q). Default: all")
    ap.add_argument("--kx", nargs="*", type=int, default=None,
                    help="Limit to these KX (integers). Default: all KX per var")
    ap.add_argument("--usage", choices=("all", "used", "monitored"), default="all",
                    help="Quick usage filter: all | used(iuse/iusev>=1) | monitored(iuse/iusev==-1)")
    ap.add_argument("--usage-field", choices=("auto", "iuse", "iusev"), default="auto",
                    help="Which column to use for usage filtering (default: auto)")
    ap.add_argument("--mask", default=None,
                    help="Extra pandas.query mask (applied after 'usage'), e.g., \"iqc==0\"")
    ap.add_argument("--limit", type=int, default=10,
                    help="Print head() with this many rows per var/KX")
    ap.add_argument("--outdir", default="outputs/debug_df",
                    help="Where to save CSV samples (when --save-csv)")
    ap.add_argument("--save-csv", action="store_true",
                    help="Save filtered head() to CSV for each var/KX")
    ns = ap.parse_args()
    return Args(**vars(ns))


def available_vars(diag) -> list[str]:
    fn = getattr(diag, "get_variables", None)
    if callable(fn):
        try:
            return list(fn())
        except Exception:
            pass
    df = diag.get_data_frame()
    return [k for k, v in df.items() if isinstance(v, dict)]


def available_kx(diag, var: str) -> list[int]:
    fn = getattr(diag, "get_kx_list", None)
    if callable(fn):
        try:
            return [int(k) for k in fn(var)]
        except Exception:
            pass
    d = diag.get_data_frame().get(var, {})
    try:
        return [int(k) for k in d.keys()]
    except Exception:
        return []


def get_df(diag, var: str, kx: int) -> pd.DataFrame:
    if hasattr(diag, "get_dataframe"):
        return diag.get_dataframe(var, kx)
    return diag.get_data_frame()[var][kx]


def choose_usage_column(df: pd.DataFrame, pref: str = "auto") -> str | None:
    """Return which column to use for usage filtering: 'iuse', 'iusev', or None."""
    if pref in ("iuse", "iusev"):
        return pref if pref in df.columns else None
    if "iuse" in df.columns:
        return "iuse"
    if "iusev" in df.columns:
        return "iusev"
    return None


def apply_usage(df: pd.DataFrame, usage: str, usage_field: str = "auto") -> tuple[pd.DataFrame, str | None]:
    """Apply usage filter using iuse/iusev. Returns (filtered_df, used_col)."""
    if usage == "all":
        col = choose_usage_column(df, usage_field)
        return df, col
    col = choose_usage_column(df, usage_field)
    if col is None:
        return df, None
    s = df[col]
    if usage == "used":
        return df[s >= 1], col
    if usage == "monitored":
        return df[s == -1], col
    return df, col


def value_counts_safe(df: pd.DataFrame, col: str, top: int = 10) -> str:
    if col not in df.columns:
        return f"(no column '{col}')"
    s = df[col].value_counts(dropna=False).head(top)
    return s.to_string()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    if args.save_csv:
        outdir.mkdir(parents=True, exist_ok=True)

    diag = diagAccess(args.file)
    vars_ = available_vars(diag)
    if args.var:
        vars_ = [v for v in args.var if v in vars_]

    print(f"[info] file: {args.file}")
    print(f"[info] variables detected: {vars_}")
    if not vars_:
        print("[warn] no variables found in this file")
        return

    for var in vars_:
        kxs = available_kx(diag, var)
        if args.kx:
            kxs = [k for k in args.kx if k in kxs]
        print("\n" + "="*80)
        print(f"[var] {var}  |  available KX: {kxs}")
        if not kxs:
            print(f"[warn] var={var}: no KX found")
            continue

        for kx in kxs:
            try:
                df = get_df(diag, var, kx)
            except Exception as e:
                print(f"[skip] var={var} kx={kx}: cannot read dataframe ({e})")
                continue

            n0 = len(df)
            cols = list(df.columns)
            has = lambda c: ("✓" if c in cols else "—")
            print(f"\n[var={var} kx={kx}] shape={df.shape}")
            print(f"  columns present: lat:{has('lat')} lon:{has('lon')} iuse:{has('iuse')} iusev:{has('iusev')} iqc:{has('iqc')}")

            # quick distributions
            print("  iuse counts (top):")
            print("  " + value_counts_safe(df, "iuse").replace("\n", "\n  "))
            print("  iusev counts (top):")
            print("  " + value_counts_safe(df, "iusev").replace("\n", "\n  "))
            print("  iqc counts (top):")
            print("  " + value_counts_safe(df, "iqc").replace("\n", "\n  "))

            # apply usage + mask
            df_f, used_col = apply_usage(df, args.usage, args.usage_field)
            if args.mask:
                try:
                    df_f = df_f.query(args.mask)
                except Exception as e:
                    print(f"  [mask-error] skipping mask on var={var} kx={kx}: {e}")
            n1 = len(df_f)
            print(f"  after usage='{args.usage}' (col={used_col}) and mask='{args.mask}': {n1} rows (was {n0})")

            if n1 == 0:
                continue

            head_n = max(1, args.limit)
            print(f"  head({head_n}):")
            try:
                cols_pref = [c for c in ["lat","lon","iuse","iusev","iqc","omf","oma","end_err"] if c in df_f.columns]
                if cols_pref:
                    print(df_f[cols_pref].head(head_n).to_string(index=False))
                else:
                    print(df_f.head(head_n).to_string(index=False))
            except Exception:
                print(df_f.head(head_n).to_string())

            if args.save_csv:
                out = outdir / f"{var}_kx{kx}_head.csv"
                try:
                    df_f.head(head_n).to_csv(out, index=False)
                    print(f"  [saved] {out}")
                except Exception as e:
                    print(f"  [save-error] {e}")

    print("\n[done]")


if __name__ == "__main__":
    main()
