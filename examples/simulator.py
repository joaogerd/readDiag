#!/usr/bin/env python3
# File: examples/simulator.py

"""
Simulate processing of large volumes of diagnostic files using the refactored reader,
and automatically find the maximum number of days you can process without exceeding
a memory threshold.

PROJECT STRUCTURE:
  project_root/
  ├── data/
  │   ├── diag_center_2020010100   # Any files matching diag_* in this dir
  │   ├── diag_center_2020010106
  │   ├── diag_center_2020010112
  │   ├── diag_center_2020010118
  │   └── ... all files for ONE “day” ...
  ├── examples/
  │   └── simulator.py

KEY CONCEPTS:
  • daily_files
      – Defined by: sorted(data_dir.glob("diag_*"))
      – Represents ONE “day” of diagnostics. 
      – If you have 4 files per day (00, 06, 12, 18 UTC), ensure only those are in data/,
        or apply the filtering shown in the NOTE below.
  • replicate_days
      – Number of “days” to simulate in each memory test.
      – Total files processed = len(daily_files) × replicate_days.
  • --step-days
      – Increment (in days) between each test iteration.
  • --max-days
      – Upper bound (in days) for the search.
  • --threshold-mb
      – Peak‐memory threshold in MB. Once a run exceeds this, we stop.
  • --workers
      – Number of parallel threads passed to read_time_series.
  • --var
      – Which diagnostic variable to load (e.g. “uv”, “t”, etc.).

EXAMPLE:
  If daily_files has 4 entries and you test --step-days 10 up to --max-days 100:
    • First attempt: 10 days →  4×10 = 40 files
    • Second:       20 days →  4×20 = 80 files
    • … until peak memory > threshold or days > max-days.
  The script reports the maximum “safe” days & total files.

NOTE (Filtering by UTC hours):
  To pick only the 00, 06, 12, 18 UTC files from a larger set, replace the
  daily_files definition with:

    all_files = sorted(data_dir.glob("diag_*"))
    daily_files = [
        p for p in all_files
        if any(p.name.endswith(f"{hour:02d}") for hour in (0, 6, 12, 18))
    ]
"""

import sys
import tracemalloc
from pathlib import Path
from typing import List
import argparse

# Permite importar reader.py (ajuste se você usa pacote readDiag)
examples_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(examples_dir.parent))
from readDiag import diagAccess


def simulate_memory_peak(
    daily_files: List[Path],
    replicate_days: int,
    var: str,
    workers: int
) -> float:
    """
    Executa a leitura em paralelo e retorna o pico de memória (MB).
    Pode lançar MemoryError se não houver memória suficiente.
    """
    files = [str(p) for p in daily_files] * replicate_days
    tracemalloc.start()
    # dispara a rotina de leitura
    _ = diagAccess.read_time_series(files, var=var, n_workers=workers)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1e6


def find_max_safe_days(
    daily_files: List[Path],
    var: str,
    workers: int,
    max_days: int,
    step_days: int,
    threshold_mb: float
) -> int:
    """
    Tenta processar de step_days em step_days até ultrapassar threshold_mb.
    Retorna o último número de dias seguro.
    """
    safe_days = 0
    print(f"🔍 Testando até {max_days} dias, passo de {step_days} dias, "
          f"limite {threshold_mb:.0f} MB\n")
    for days in range(step_days, max_days + step_days, step_days):
        days = min(days, max_days)
        total_files = len(daily_files) * days
        print(f"➡️  Tentativa: {days} dias → {total_files} arquivos...", end=" ")
        try:
            peak = simulate_memory_peak(daily_files, days, var, workers)
        except MemoryError:
            print("❌ MemoryError")
            break
        print(f"🏔 pico={peak:.0f} MB")
        if peak > threshold_mb:
            print(f"⚠️  Excedeu o limiar ({threshold_mb:.0f} MB).")
            break
        safe_days = days

    print(f"\n✅ Máximo seguro: {safe_days} dias "
          f"({len(daily_files) * safe_days} arquivos)")
    return safe_days


def main():
    # Parse dos parâmetros
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-days",    type=int,   default=365)
    parser.add_argument("--step-days",   type=int,   default=10)
    parser.add_argument("--threshold-mb",type=float, default=2048)
    parser.add_argument("--workers",     type=int,   default=8)
    parser.add_argument("--var",         type=str,   default="uv")
    args = parser.parse_args()

    # Localiza arquivos de 1 dia
    data_dir = examples_dir.parent / "data"
    daily_files = sorted(data_dir.glob("diag_*"))
    if not daily_files:
        print(f"❌ Nenhum arquivo diag_* encontrado em {data_dir}")
        return

    # Roda a busca incremental
    find_max_safe_days(
        daily_files=daily_files,
        var=args.var,
        workers=args.workers,
        max_days=args.max_days,
        step_days=args.step_days,
        threshold_mb=args.threshold_mb,
    )


if __name__ == "__main__":
    main()

