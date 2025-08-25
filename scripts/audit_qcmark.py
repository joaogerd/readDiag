#!/usr/bin/env python3
# scripts/audit_idqc_diagAccess.py
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import math
import csv
import numpy as np
import pandas as pd

# Usa teu leitor atual
from readDiag.reader import diagAccess

def is_near_integer(x: float, tol: float) -> bool:
    # True se |x - round(x)| <= tol
    return abs(x - round(x)) <= tol

def audit_conv(df_dict, tol: float) -> Tuple[Dict[int, int], Dict[str, int], Dict[int, Dict[int, int]]]:
    """
    Retorna:
      - global_counts: histograma global de IDQC (inteiro arredondado)
      - near_counters: {"near": qtos ~inteiro, "total": total lidos}
      - per_kx_counts: histograma por kx: {kx: {idqc_int: count}}
    """
    global_counts: Dict[int, int] = {}
    near_counters = {"near": 0, "total": 0}
    per_kx_counts: Dict[int, Dict[int, int]] = {}

    # df_dict[var][kx] -> DataFrame
    # var definido internamente no diagAccess
    for kx, df in df_dict.items():
        if not isinstance(df, pd.DataFrame) or df.empty or "idqc" not in df.columns:
            continue

        vals = df["idqc"].to_numpy(dtype=float, copy=False)
        diffs = np.abs(vals - np.round(vals))
        near = int(np.sum(diffs <= tol))
        near_counters["near"] += near
        near_counters["total"] += vals.size

        qc_int = np.round(vals).astype(int)
        # global
        for v in qc_int:
            global_counts[v] = global_counts.get(v, 0) + 1
        # por kx
        bucket = per_kx_counts.setdefault(int(kx), {})
        for v in qc_int:
            bucket[v] = bucket.get(v, 0) + 1

    return global_counts, near_counters, per_kx_counts

def audit_rad(df_dict, tol: float) -> Tuple[Dict[int, int], Dict[str, int], Dict[int, Dict[int, int]]]:
    """
    Para radiância, df_dict["dataframes"]["diagbufchan_df"] é uma lista de DFs, um por canal.
    Retorna:
      - global_counts: histograma global de IDQC (inteiro arredondado)
      - near_counters: {"near": qtos ~inteiro, "total": total lidos}
      - per_channel_counts: histograma por canal: {ch_index: {idqc_int: count}}
    """
    global_counts: Dict[int, int] = {}
    near_counters = {"near": 0, "total": 0}
    per_channel_counts: Dict[int, Dict[int, int]] = {}

    df_list: List[pd.DataFrame] = df_dict["dataframes"]["diagbufchan_df"]
    for ich, df in enumerate(df_list, start=1):
        if not isinstance(df, pd.DataFrame) or df.empty or "idqc" not in df.columns:
            continue

        vals = df["idqc"].to_numpy(dtype=float, copy=False)
        diffs = np.abs(vals - np.round(vals))
        near = int(np.sum(diffs <= tol))
        near_counters["near"] += near
        near_counters["total"] += vals.size

        qc_int = np.round(vals).astype(int)
        # global
        for v in qc_int:
            global_counts[v] = global_counts.get(v, 0) + 1
        # por canal
        bucket = per_channel_counts.setdefault(int(ich), {})
        for v in qc_int:
            bucket[v] = bucket.get(v, 0) + 1

    return global_counts, near_counters, per_channel_counts

def save_global_csv(output_csv: Path, meta: Dict[str, str], global_counts: Dict[int, int]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as f:
        w = csv.writer(f)
        # metadados simples
        for k, v in meta.items():
            w.writerow([f"#{k}", v])
        w.writerow([])
        w.writerow(["idqc", "count_global"])
        for k in sorted(global_counts):
            w.writerow([k, global_counts[k]])

def save_per_bucket_csv(per_csv: Path, meta: Dict[str, str], per_counts: Dict[int, Dict[int, int]], bucket_name: str) -> None:
    # bucket_name: "channel_index" ou "kx"
    with per_csv.open("w", newline="") as f:
        w = csv.writer(f)
        for k, v in meta.items():
            w.writerow([f"#{k}", v])
        w.writerow([])
        w.writerow([bucket_name, "idqc", "count"])
        for b in sorted(per_counts):
            for k, v in sorted(per_counts[b].items()):
                w.writerow([b, k, v])

def summarize(title: str, meta: Dict[str, str], near: Dict[str, int], global_counts: Dict[int, int]) -> None:
    total = near["total"]
    near_n = near["near"]
    frac = (near_n / total) if total else float("nan")
    top = sorted(global_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    print("\n================= IDQC AUDIT =================")
    print(f"{title}")
    for k, v in meta.items():
        print(f"{k:>10}: {v}")
    print(f"{'near-int':>10}: {near_n}/{total} = {frac:.3%}")
    print("Top-10 (global):")
    for val, cnt in top:
        print(f"  {val:>4d}: {cnt}")
    print("==============================================\n")

def run_one(file_path: Path, tol: float, per_channel: bool, output_csv: Path) -> None:
    if not file_path.exists():
        print(f"[WARN] Ignorando: {file_path} (não existe)")
        return

    d = diagAccess(str(file_path))
    data_type = d.get_data_type()  # 1=conv, 2=rad (no teu reader)
    df_dict = d.get_data_frame()

    # metadados disponíveis via header_dict() se tiver no teu reader; senão, usa básicos
    meta = {"file": file_path.name}
    try:
        h = d.header_dict()  # se teu diagAccess tiver
        for k in ("obstype", "dplat", "isis", "nchanl", "idiag", "ireal", "jiter", "idate"):
            if k in h:
                meta[k] = str(h[k])
    except Exception:
        pass

    if data_type == 1:
        # conv
        var = getattr(d, "var", None)
        if var is None:
            # alguns readers retornam já df_dict = {kx: df}; trata os dois casos
            group = df_dict
        else:
            group = df_dict[var]
        global_counts, near_counters, per_kx_counts = audit_conv(group, tol)
        summarize(f"Arquivo: {file_path.name} (CONV)", meta, near_counters, global_counts)
        save_global_csv(output_csv, meta, global_counts)
        if per_channel:
            per_csv = output_csv.with_name(output_csv.stem + "_per_kx.csv")
            save_per_bucket_csv(per_csv, meta, per_kx_counts, bucket_name="kx")
    else:
        # radiância
        global_counts, near_counters, per_channel_counts = audit_rad(df_dict, tol)
        summarize(f"Arquivo: {file_path.name} (RAD)", meta, near_counters, global_counts)
        save_global_csv(output_csv, meta, global_counts)
        if per_channel:
            per_csv = output_csv.with_name(output_csv.stem + "_per_channel.csv")
            save_per_bucket_csv(per_csv, meta, per_channel_counts, bucket_name="channel_index")

def main() -> None:
    p = argparse.ArgumentParser(
        description="Audita IDQC em diag_* do GSI (conv/rad) usando diagAccess, considerando 'quase inteiros' com tolerância."
    )
    p.add_argument("files", nargs="+", help="Arquivos diag_* (binário).")
    p.add_argument("--tolerance", type=float, default=5e-2, help="Tolerância para 'quase inteiro' (default: 0.05).")
    p.add_argument("--per-channel", action="store_true", help="Salvar CSV também por canal (rad) / por kx (conv).")
    p.add_argument("--output-csv", type=Path, default=Path("data_processed/idqc_audit.csv"),
                   help="CSV global de saída (um por arquivo; o nome será reutilizado por arquivo).")
    args = p.parse_args()

    # processa cada arquivo separadamente, cada um com seu CSV (mesmo nome base)
    for f in args.files:
        out = args.output_csv
        # se passou vários arquivos, cria nomes distintos automaticamente
        if len(args.files) > 1:
            out = out.with_name(out.stem + f"_{Path(f).stem}.csv")
        run_one(Path(f), args.tolerance, args.per_channel, out)

if __name__ == "__main__":
    main()

