#!/usr/bin/env python3
# scripts/audit_idqc.py
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple

import math
import csv
import numpy as np

# Ajuste o import abaixo conforme a localização do seu reader
# Ex.: from readDiag.reader import RadianceDiagReader
from readDiag.reader import RadianceDiagReader, RadianceRecord, RadianceHeader


@dataclass(frozen=True)
class AuditConfig:
    qc_index: int        # índice (zero-based) da linha do diagbufchan que contém o QC/IDQC
    max_records: int     # máximo de registros a percorrer (0 = todos)
    output_csv: Path     # caminho do CSV de saída
    per_channel: bool    # salvar histograma por canal
    tolerance: float     # tolerância para considerar “quase inteiro”


def _iter_records(path: Path) -> Iterable[RadianceRecord]:
    with RadianceDiagReader(path) as rdr:
        hdr: RadianceHeader = rdr.header  # type: ignore[assignment]
        if hdr is None:
            raise RuntimeError("Header not read — is this a valid diag file?")
        yield from rdr.iter_records()


def _update_histograms(
    rec: RadianceRecord,
    qc_index: int,
    per_channel_counts: Dict[int, Dict[int, int]],
    global_counts: Dict[int, int],
    near_integer_counter: Dict[str, int],
    near_integer_total: Dict[str, int],
) -> None:
    """
    Atualiza contagens a partir de um registro:
    - Extrai a linha qc_index de diagbufchan (tamanho nchan)
    - Arredonda valores próximos de inteiro e acumula histogramas
    """
    ch_mat = rec.diagbufchan  # (idiag, nchan)
    if qc_index < 0 or qc_index >= ch_mat.shape[0]:
        raise IndexError(
            f"qc_index={qc_index} fora do intervalo [0, {ch_mat.shape[0]-1}]"
        )

    qc_vec = ch_mat[qc_index, :]  # (nchan,)
    # Contabiliza proximidade de inteiro
    diffs = np.abs(qc_vec - np.round(qc_vec))
    near_int = np.sum(diffs <= 0.05)  # tolerância padrão
    near_integer_counter["near"] += int(near_int)
    near_integer_total["total"] += qc_vec.size

    # Histograma global
    qc_int = np.round(qc_vec).astype(int)
    for v in qc_int:
        global_counts[v] = global_counts.get(v, 0) + 1

    # Histograma por canal (coluna → um canal fixo)
    for ich, v in enumerate(qc_int, start=1):  # canais 1..n
        if ich not in per_channel_counts:
            per_channel_counts[ich] = {}
        per_channel_counts[ich][v] = per_channel_counts[ich].get(v, 0) + 1


def _print_summary(
    file_path: Path,
    hdr: RadianceHeader,
    qc_index: int,
    global_counts: Dict[int, int],
    near_integer_counter: Dict[str, int],
    near_integer_total: Dict[str, int],
) -> None:
    total = near_integer_total["total"]
    near = near_integer_counter["near"]
    frac = (near / total) if total else float("nan")
    top = sorted(global_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    print("\n================= IDQC AUDIT =================")
    print(f"Arquivo:         {file_path.name}")
    print(f"Sensor/obstype:  {hdr.obstype} (isis={hdr.isis})  plataforma={hdr.dplat}")
    print(f"Iteração:        jiter={hdr.jiter}  data={hdr.ianldate}")
    print(f"nchan={hdr.nchanl_diag}  idiag={hdr.idiag}  ireal={hdr.ireal_radiag}")
    print(f"qc_index         linha #{qc_index} (zero-based) em diagbufchan")
    print(f"Quase-inteiros:  {near}/{total} = {frac:.3%}")
    print("Top-10 códigos (global):")
    for val, cnt in top:
        print(f"  {val:>4d}: {cnt}")
    print("==============================================\n")


def _save_csv(
    output_csv: Path,
    hdr: RadianceHeader,
    global_counts: Dict[int, int],
    per_channel_counts: Dict[int, Dict[int, int]] | None,
) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Tabela global
    with output_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# obstype", hdr.obstype])
        w.writerow(["# platform", hdr.dplat])
        w.writerow(["# isis", hdr.isis])
        w.writerow(["# nchan", hdr.nchanl_diag])
        w.writerow([])
        w.writerow(["idqc", "count_global"])
        for k, v in sorted(global_counts.items()):
            w.writerow([k, v])

    # Opcional: por canal (canal, idqc, count)
    if per_channel_counts is not None:
        per_ch_csv = output_csv.with_name(output_csv.stem + "_per_channel.csv")
        with per_ch_csv.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["# obstype", hdr.obstype])
            w.writerow(["# platform", hdr.dplat])
            w.writerow(["# isis", hdr.isis])
            w.writerow(["# nchan", hdr.nchanl_diag])
            w.writerow([])
            w.writerow(["channel_index", "idqc", "count"])
            for ich in sorted(per_channel_counts):
                for k, v in sorted(per_channel_counts[ich].items()):
                    w.writerow([ich, k, v])


def run_audit(paths: list[Path], cfg: AuditConfig) -> None:
    """
    Executa auditoria de IDQC sobre uma lista de arquivos de diagnóstico.
    """
    if not paths:
        raise SystemExit("Nenhum arquivo informado.")

    for file_path in paths:
        if not file_path.exists():
            print(f"[WARN] Ignorando: {file_path} (não existe)")
            continue

        per_channel_counts: Dict[int, Dict[int, int]] = {}
        global_counts: Dict[int, int] = {}
        near_integer_counter = {"near": 0}
        near_integer_total = {"total": 0}

        with RadianceDiagReader(file_path) as rdr:
            hdr = rdr.header  # type: ignore[assignment]
            if hdr is None:
                raise RuntimeError("Header não lido — arquivo inválido?")

            # Itera registros (até max_records se definido)
            nrec = 0
            for rec in rdr.iter_records():
                _update_histograms(
                    rec,
                    cfg.qc_index,
                    per_channel_counts,
                    global_counts,
                    near_integer_counter,
                    near_integer_total,
                )
                nrec += 1
                if cfg.max_records and nrec >= cfg.max_records:
                    break

            # Resumo no terminal
            _print_summary(
                file_path, hdr, cfg.qc_index, global_counts,
                near_integer_counter, near_integer_total
            )

            # Salva CSV(s)
            _save_csv(
                cfg.output_csv,
                hdr,
                global_counts,
                per_channel_counts if cfg.per_channel else None,
            )


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Audita o campo IDQC/QC nos diagnósticos de radiância do GSI, "
            "extraindo-o do vetor por-canal (diagbufchan) e gerando histogramas."
        )
    )
    p.add_argument(
        "files", nargs="+",
        help="Arquivos de diagnóstico (binário unformatted do GSI). Aceita glob via shell."
    )
    p.add_argument(
        "--qc-index", type=int, default=4,
        help="Índice (zero-based) da linha de diagbufchan onde está o QC/IDQC (default: 4)."
    )
    p.add_argument(
        "--max-records", type=int, default=0,
        help="Máximo de registros a processar (0 = todos). Útil para amostras rápidas."
    )
    p.add_argument(
        "--per-channel", action="store_true",
        help="Salvar também um CSV com histograma por canal."
    )
    p.add_argument(
        "--output-csv", type=Path, default=Path("data_processed/idqc_audit.csv"),
        help="Caminho do CSV de saída global."
    )
    p.add_argument(
        "--tolerance", type=float, default=0.05,
        help="Tolerância para considerar valores 'quase inteiros' (default: 0.05)."
    )
    args = p.parse_args()

    cfg = AuditConfig(
        qc_index=args.qc_index,
        max_records=args.max_records,
        output_csv=args.output_csv,
        per_channel=args.per_channel,
        tolerance=args.tolerance,
    )

    paths = [Path(s) for s in args.files]
    run_audit(paths, cfg)


if __name__ == "__main__":
    main()

