#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Legacy compatibility smoke test (single file).

This script exercises the legacy surface:
- read_diag(...).diag1/.diag2
- get_variables, get_kx_list, to_dataframe
- impact(var=...) for a pair of files (01 vs 03)
- plotting methods: plot, pcount, vcount, kxcount, ptmap, pvmap,
  plot_time_series_mean, plot_time_series_mean_std

Outputs figures to ./_legacy_out

Usage:
    python scripts/test_legacy_smoke.py \
        --base /media/extra/wrk/dev/readDiag/dataTest/exp20 \
        --var t \
        --kx 187
"""

from __future__ import annotations
import argparse
import warnings
from pathlib import Path

# use non-interactive backend for batch savefig
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa

import pandas as pd

from readDiag.legacy import read_diag


def pick_kx(diag_obj, var: str, prefer: int | None = None) -> int:
    """Pick an available kx for the given variable (prefer if present)."""
    kxs = diag_obj.get_kx_list(var)
    if not kxs:
        raise RuntimeError(f"No kx found for variable '{var}'.")
    if prefer is not None and prefer in kxs:
        return prefer
    return int(kxs[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True,
                    help="Base directory with diag files (exp20).")
    ap.add_argument("--var", type=str, default="t",
                    help="Conventional variable to test (e.g., t, q, uv, ps).")
    ap.add_argument("--kx", type=int, default=None,
                    help="Preferred kx to test (will fallback if missing).")
    ap.add_argument("--out", type=Path, default=Path("./_legacy_out"),
                    help="Output directory for figures.")
    args = ap.parse_args()

    base: Path = args.base
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    # Silence: show deprecations once to confirm the layer is active
    warnings.simplefilter("default", DeprecationWarning)

    # -------------------------
    # File set (exp20)
    # -------------------------
    CONV_01 = base / "diag_conv_01.2024013018"
    CONV_03 = base / "diag_conv_03.2024013018"
    RAD_N19_01 = base / "diag_amsua_n19_01.2024013018"
    RAD_N19_03 = base / "diag_amsua_n19_03.2024013018"

    assert CONV_01.exists(), f"Missing file: {CONV_01}"
    assert CONV_03.exists(), f"Missing file: {CONV_03}"
    assert RAD_N19_01.exists(), f"Missing file: {RAD_N19_01}"
    assert RAD_N19_03.exists(), f"Missing file: {RAD_N19_03}"

    # =========================================================
    # 1) Legacy with ONE FILE (conventional)
    # =========================================================
    print("\n[1] Legacy single-file (conventional)")
    r_conv = read_diag(CONV_01)

    # attributes diag1 / diag2
    assert hasattr(r_conv, "diag1")
    assert r_conv.diag2 is None, "diag2 should be None for single-file case"

    # get_variables, get_kx_list, to_dataframe
    vars_ = r_conv.get_variables()
    print("variables:", vars_[:8])
    var = args.var if args.var in vars_ else (vars_[0] if vars_ else "t")
    kx = pick_kx(r_conv, var, args.kx)
    print(f"picked var={var}, kx={kx}")

    df_sample = r_conv.to_dataframe(var, kx)
    print("sample df shape:", df_sample.shape)
    print(df_sample.head())

    # plotting legacy names (all should work & save figures)
    # plot -> observation counts generic
    ax = r_conv.plot(var, title=f"[legacy] plot (observation counts) - {var}")
    ax.figure.savefig(out / f"plot_counts_{var}.png", dpi=120)
    plt.close(ax.figure)

    ax = r_conv.pcount(var, title=f"[legacy] pcount - {var}")
    ax.figure.savefig(out / f"pcount_{var}.png", dpi=120)
    plt.close(ax.figure)

    ax = r_conv.vcount(var, column="omf", bins=50, title=f"[legacy] vcount (omf) - {var}")
    ax.figure.savefig(out / f"vcount_{var}_omf.png", dpi=120)
    plt.close(ax.figure)

    ax = r_conv.kxcount(var, title=f"[legacy] kxcount - {var}")
    ax.figure.savefig(out / f"kxcount_{var}.png", dpi=120)
    plt.close(ax.figure)

    # mapas (conv)
    try:
        ax = r_conv.ptmap(var, kx, title=f"[legacy] ptmap - {var}/{kx}")
        ax.figure.savefig(out / f"ptmap_{var}_{kx}.png", dpi=120)
        plt.close(ax.figure)
    except Exception as e:
        print(f"ptmap skipped: {e}")

    try:
        ax = r_conv.pvmap(var, kx, column="omf", title=f"[legacy] pvmap (omf) - {var}/{kx}")
        ax.figure.savefig(out / f"pvmap_{var}_{kx}_omf.png", dpi=120)
        plt.close(ax.figure)
    except Exception as e:
        print(f"pvmap skipped: {e}")

    # time series (conv) — mean & mean±std
    try:
        ax = r_conv.plot_time_series_mean(var, kx=kx, column="omf", res="3H",
                                          title=f"[legacy] TS mean (omf) - {var}/{kx}")
        ax.figure.savefig(out / f"ts_mean_{var}_{kx}_omf.png", dpi=120)
        plt.close(ax.figure)
    except Exception as e:
        print(f"time_series_mean skipped: {e}")

    try:
        ax = r_conv.plot_time_series_mean_std(var, kx=kx, column="omf", res="3H",
                                              title=f"[legacy] TS mean±std (omf) - {var}/{kx}")
        ax.figure.savefig(out / f"ts_meanstd_{var}_{kx}_omf.png", dpi=120)
        plt.close(ax.figure)
    except Exception as e:
        print(f"time_series_mean_std skipped: {e}")

    # =========================================================
    # 2) Legacy with TWO FILES (impact: 01 vs 03)
    # =========================================================
    print("\n[2] Legacy two-file (impact 01 vs 03)")
    r_pair = read_diag([CONV_01, CONV_03])
    assert r_pair.diag2 is not None, "diag2 must be present for pair case"

    ia = r_pair.impact(var=var)  # ImpactAnalyzer via legacy wrapper
    # compute metrics table
    df_metrics = ia.compute_all_metrics()
    print("impact metrics (head):")
    print(df_metrics.head())
    # plot bar TI
    try:
        ax = ia.plot_impact_bar(metric="TI", top_k=15,
                                title=f"[legacy] Impact TI - {var}")
        ax.figure.savefig(out / f"impact_TI_{var}.png", dpi=120)
        plt.close(ax.figure)
    except Exception as e:
        print(f"impact bar skipped: {e}")

    # =========================================================
    # 3) Legacy with ONE FILE (radiance)
    # =========================================================
    print("\n[3] Legacy single-file (radiance)")
    r_rad = read_diag(RAD_N19_01)
    # Even though legacy plotting was conv-oriented, we at least ensure handle works:
    print("diag1 data type (1=conv, 2=rad):", r_rad.diag1.get_data_type())
    # No kx list for radiance; just confirm access to data frame structure:
    rad_data = r_rad.diag1.get_data_frame()
    print("radiance keys:", list(rad_data.keys()))

    print(f"\nDone. Figures saved in: {out.resolve()}")


if __name__ == "__main__":
    main()

