#!/usr/bin/env python3
"""Benchmark GSI diagnostics reading speed (conv & rad) with reader.py and diagAccess.

This script measures the time to open/read a **conventional** file and a **radiance**
file using both the modern reader (``reader.py`` / ``readDiag.reader``) and the legacy
reader (``diagAccess.py`` or ``diagAccess_legacy.py``). For the modern reader, it
times both ``use_memmap=False`` and ``use_memmap=True``.

The benchmark consists of an optional warm-up followed by repeated runs per case. The
reported metric is the mean ± standard deviation (in seconds).

Now includes three **conventional** modes for the modern reader:
- split : {var -> {kx -> DataFrame}} (default pipeline)
- compact : {var -> {"__ALL__" -> DataFrame}} (no split by kx)
- raw : {var -> {"data" -> ndarray, "sids" -> None|ndarray}} (no DataFrame)


Usage examples:
    python bench_readers.py --conv data/diag_conv_01.YYYYMMDDHH --rad data/diag_amsua_metop-a_01.YYYYMMDDHH
    python bench_readers.py --conv ... --rad ... --conv-modes split,raw --repeats 5 --warmup 1 --cold --verify

Notes:
    * Import discovery is flexible:
        - Tries ``from readDiag.reader import diagAccess`` (installed package).
        - Falls back to local ``reader.py`` in the working dir.
        - For the legacy reader, first tries ``from diagAccess import diagAccess``,
          then falls back to local ``diagAccess_legacy.py`` in the working dir.
    * The modern reader accepts ``use_memmap``; the legacy one does not.
    * The script *forces* a full parse by calling ``get_data_frame()``.

Example output:
    ┌───────────────────────────────┬─────────┬─────────┐
    │ Case                          │  Mean s │   Std s │
    ├───────────────────────────────┼─────────┼─────────┤
    │ modern conv (memmap=False)    │   0.412 │   0.018 │
    │ modern conv (memmap=True)     │   0.305 │   0.015 │
    │ modern rad  (memmap=False)    │   0.012 │   0.001 │
    │ modern rad  (memmap=True)     │   0.011 │   0.001 │
    │ legacy conv                   │   0.520 │   0.030 │
    │ legacy rad                    │   0.020 │   0.002 │
    └───────────────────────────────┴─────────┴─────────┘

"""
from __future__ import annotations

import argparse
import gc
import importlib
import importlib.util
import os
import statistics as stats
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

# ---------- Dynamic import helpers ----------

SCRIPT_DIR = Path(__file__).resolve().parent
SEARCH_DIRS = [
    Path.cwd(),                 # onde você está rodando
    SCRIPT_DIR,                 # pasta do bench
    SCRIPT_DIR.parent,          # pasta anterior (sua raiz)
    SCRIPT_DIR.parent / "src",                  # layouts com src/
    SCRIPT_DIR.parent / "src" / "readDiag",
    SCRIPT_DIR.parent / "readDiag",             # pacote local
]

def _import_from_file(file_path: Path, attr_name: str):
    spec = importlib.util.spec_from_file_location(file_path.stem, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    if not hasattr(module, attr_name):
        raise ImportError(f"{file_path} does not define {attr_name}")
    return getattr(module, attr_name)

def load_modern_diagaccess() -> type:
    # 1) pacote instalado
    try:
        return getattr(importlib.import_module("readDiag.reader"), "diagAccess")
    except Exception:
        pass
    # 2) arquivos próximos (reader.py)
    CANDIDATES = ["reader.py", "readDiag/reader.py", "src/readDiag/reader.py"]
    for d in SEARCH_DIRS:
        for name in CANDIDATES:
            p = d / name
            if p.exists():
                return _import_from_file(p, "diagAccess")
    raise ImportError("modern diagAccess not found (tried installed, reader.py near script/root/src).")

def load_legacy_diagaccess() -> type:
    # 1) módulo legado instalado
    try:
        return getattr(importlib.import_module("diagAccess"), "diagAccess")
    except Exception:
        pass
    # 2) arquivos próximos (diagAccess.py ou diagAccess_legacy.py)
    CANDIDATES = ["diagAccess.py", "diagAccess_legacy.py"]
    for d in SEARCH_DIRS:
        for name in CANDIDATES:
            p = d / name
            if p.exists():
                return _import_from_file(p, "diagAccess")
    raise ImportError("legacy diagAccess not found (tried installed and nearby files).")
# ---------- Timing helpers ----------

@dataclass
class BenchResult:
    label: str
    mean_s: float
    std_s: float

def _bench_case(label: str, func: Callable[[], object], repeats: int, warmup: int) -> BenchResult:
    # Warm-up
    for _ in range(max(0, warmup)):
        try:
            func()
        except Exception as e:
            raise RuntimeError(f"Warm-up failed for '{label}': {e}") from e
        finally:
            gc.collect()

    # Timed runs
    times: List[float] = []
    for i in range(repeats):
        gc.collect()
        t0 = time.perf_counter()
        try:
            func()
        except Exception as e:
            raise RuntimeError(f"Run {i+1}/{repeats} failed for '{label}': {e}") from e
        finally:
            dt = time.perf_counter() - t0
            times.append(dt)
    mean_s = float(stats.mean(times)) if times else float("nan")
    std_s = float(stats.pstdev(times)) if len(times) > 1 else 0.0
    return BenchResult(label, mean_s, std_s)

# ---------- Bench drivers ----------

def make_modern_runner(diag_cls: type, file_path: Path, *, use_memmap: bool | None,
                       conv_mode: str | None = None) -> Callable[[], object]:
    """Return a callable that constructs modern diagAccess and forces full read.

    conv_mode: None|'split'|'compact'|'raw' (ignored for radiance files)
    """
    conv_mode = (conv_mode or "split").lower()

    def _run():
        kwargs: Dict[str, object] = {}
        if use_memmap is not None:
            kwargs["use_memmap"] = use_memmap
        # Conventional mode flags
        if conv_mode == "raw":
            kwargs["raw_numpy"] = True
            kwargs["compact"] = False
        elif conv_mode == "compact":
            kwargs["raw_numpy"] = False
            kwargs["compact"] = True
        else:  # split/default
            kwargs["raw_numpy"] = False
            kwargs["compact"] = False

        try:
            obj = diag_cls(str(file_path), **kwargs)  # type: ignore[arg-type]
        except TypeError:
            # Fallback for older implementations that don't accept the flags
            kwargs.pop("raw_numpy", None)
            kwargs.pop("compact", None)
            obj = diag_cls(str(file_path), **kwargs)  # type: ignore[arg-type]
        return obj.get_data_frame()
    return _run

def make_legacy_runner(diag_cls: type, file_path: Path) -> Callable[[], object]:
    def _run():
        obj = diag_cls(str(file_path))
        return obj.get_data_frame()
    return _run

# ---------- Table formatting ----------

def _fmt_row(cells: Tuple[str, str, str], widths: Tuple[int, int, int]) -> str:
    return "│ " + " │ ".join(c.ljust(w) for c, w in zip(cells, widths)) + " │"

def print_table(results: list[BenchResult]) -> None:
    col1 = "Case"
    col2 = "Mean s"
    col3 = "Std s"
    widths = (
        max(len(col1), *(len(r.label) for r in results)),
        max(len(col2), *(len(f"{r.mean_s:.3f}") for r in results)),
        max(len(col3), *(len(f"{r.std_s:.3f}") for r in results)),
    )
    border_top = "┌" + "┬".join(("─" * (w + 2)) for w in widths) + "┐"
    border_mid = "├" + "┼".join(("─" * (w + 2)) for w in widths) + "┤"
    border_bot = "└" + "┴".join(("─" * (w + 2)) for w in widths) + "┘"
    header = _fmt_row((col1, col2, col3), widths)
    print(border_top)
    print(header)
    print(border_mid)
    for r in results:
        print(_fmt_row((r.label, f"{r.mean_s:.3f}", f"{r.std_s:.3f}"), widths))
    print(border_bot)

# ---------- CLI ----------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark conv/rad read times with modern and legacy readers (incl. conv split/compact/raw).");
    p.add_argument("--conv", required=True, type=Path, help="Path to a conventional diag file (e.g., diag_conv_01.YYYYMMDDHH)")
    p.add_argument("--rad", required=True, type=Path, help="Path to a radiance diag file (e.g., diag_amsua_metop-a_01.YYYYMMDDHH)")
    p.add_argument("--repeats", type=int, default=3, help="Number of timed runs per case (default: 3)")
    p.add_argument("--warmup", type=int, default=1, help="Number of warm-up runs per case (default: 1)")
    p.add_argument("--skip_memmap", action="store_true", help="Do not run memmap=True cases for modern reader")
    p.add_argument("--cold", action="store_true", help="Also measure cold start (warmup=0) in a separate table")
    p.add_argument("--verify", action="store_true", help="After timing, print basic shapes parsed by each reader")
    p.add_argument("--conv-modes", type=str, default="split,compact,raw",
                   help="Comma-separated list of conv modes to run for the modern reader (subset of: split,compact,raw)")
    return p.parse_args()

def _parse_conv_modes(s: str) -> List[str]:
    raw = [t.strip().lower() for t in s.split(",") if t.strip()]
    valid = {"split", "compact", "raw"}
    modes = [m for m in raw if m in valid]
    return modes or ["split"]
# ---------- Main ----------

def main():
    args = parse_args()
    conv = args.conv
    rad = args.rad

    if not conv.exists():
        sys.exit(f"Conventional file not found: {conv}")
    if not rad.exists():
        sys.exit(f"Radiance file not found: {rad}")

    conv_modes = _parse_conv_modes(args.conv_modes)

    # Load readers
    Modern = load_modern_diagaccess()
    Legacy = load_legacy_diagaccess()

    # ---------- COLD START ----------
    if args.cold:
        cold_results: List[BenchResult] = []
        # Modern conv in requested modes
        for mode in conv_modes:
            label_base = f"modern conv[{mode}] cold"
            run = make_modern_runner(Modern, conv, use_memmap=False, conv_mode=mode)
            cold_results.append(_bench_case(f"{label_base} (memmap=False)", run, args.repeats, warmup=0))
            if not args.skip_memmap:
                run_mm = make_modern_runner(Modern, conv, use_memmap=True, conv_mode=mode)
                cold_results.append(_bench_case(f"{label_base} (memmap=True)", run_mm, args.repeats, warmup=0))

        # Modern rad (no modes)
        run = make_modern_runner(Modern, rad, use_memmap=False, conv_mode=None)
        cold_results.append(_bench_case("modern rad cold (memmap=False)", run, args.repeats, warmup=0))
        if not args.skip_memmap:
            run_mm = make_modern_runner(Modern, rad, use_memmap=True, conv_mode=None)
            cold_results.append(_bench_case("modern rad cold (memmap=True)", run_mm, args.repeats, warmup=0))

        # Legacy conv/rad
        cold_results.append(_bench_case("legacy conv cold", make_legacy_runner(Legacy, conv), args.repeats, warmup=0))
        cold_results.append(_bench_case("legacy rad cold",  make_legacy_runner(Legacy, rad),  args.repeats, warmup=0))

        print("\n[COLD START]")
        print_table(cold_results)

    # ---------- WARM / REGIME ----------
    results: List[BenchResult] = []

    # Modern conv (all requested modes)
    for mode in conv_modes:
        label_base = f"modern conv[{mode}]"
        run = make_modern_runner(Modern, conv, use_memmap=False, conv_mode=mode)
        results.append(_bench_case(f"{label_base} (memmap=False)", run, args.repeats, args.warmup))
        if not args.skip_memmap:
            run_mm = make_modern_runner(Modern, conv, use_memmap=True, conv_mode=mode)
            results.append(_bench_case(f"{label_base} (memmap=True)", run_mm, args.repeats, args.warmup))

    # Modern rad
    run = make_modern_runner(Modern, rad, use_memmap=False, conv_mode=None)
    results.append(_bench_case("modern rad (memmap=False)", run, args.repeats, args.warmup))
    if not args.skip_memmap:
        run_mm = make_modern_runner(Modern, rad, use_memmap=True, conv_mode=None)
        results.append(_bench_case("modern rad (memmap=True)", run_mm, args.repeats, args.warmup))

    # Legacy conv/rad
    results.append(_bench_case("legacy conv", make_legacy_runner(Legacy, conv), args.repeats, args.warmup))
    results.append(_bench_case("legacy rad",  make_legacy_runner(Legacy, rad),  args.repeats, args.warmup))

    print()
    print_table(results)

    # ---------- VERIFY (shapes) ----------
    if args.verify:
        def _new_modern(path: Path, memmap: bool = False, mode: str = "split"):
            kwargs: Dict[str, object] = {"use_memmap": memmap}
            if mode == "raw":
                kwargs["raw_numpy"] = True; kwargs["compact"] = False
            elif mode == "compact":
                kwargs["raw_numpy"] = False; kwargs["compact"] = True
            else:
                kwargs["raw_numpy"] = False; kwargs["compact"] = False
            try:
                return Modern(str(path), **kwargs)  # type: ignore[arg-type]
            except TypeError:
                kwargs.pop("raw_numpy", None)
                kwargs.pop("compact", None)
                return Modern(str(path), **kwargs)  # type: ignore[arg-type]

        def conv_rows_any(obj) -> int:
            out = obj.get_data_frame()
            # split mode
            if all(isinstance(v, dict) and any(isinstance(x, dict) for x in v.values()) for v in out.values()):
                return sum(df.shape[0] for var in out.values() for df in var.values())
            # compact
            if all(isinstance(v, dict) and "__ALL__" in v for v in out.values()):
                return sum(v["__ALL__"].shape[0] for v in out.values())
            # raw
            if all(isinstance(v, dict) and "data" in v for v in out.values()):
                return sum(v["data"].shape[0] for v in out.values())
            # fallback: try best-effort
            try:
                return sum(df.shape[0] for var in out.values() for df in var.values())
            except Exception:
                return 0

        def rad_shape(obj):
            out = obj.get_data_frame()
            ch_list = out["dataframes"].get("diagbufchan_df", [])
            n_channels = len(ch_list)
            n_rows = sum(df.shape[0] for df in ch_list) if ch_list else 0
            return n_channels, n_rows

        print("\n[VERIFY SHAPES]")
        # conv: compare rows across modes
        for mode in conv_modes:
            m_conv = _new_modern(conv, memmap=False, mode=mode)
            print(f"[verify] modern conv[{mode}] rows:", conv_rows_any(m_conv))
        l_conv = load_legacy_diagaccess()(str(conv))
        print("[verify] legacy conv rows:", conv_rows_any(l_conv))

        # rad
        m_rad = _new_modern(rad, memmap=False, mode="split")
        l_rad = load_legacy_diagaccess()(str(rad))
        ch_m, rows_m = rad_shape(m_rad)
        ch_l, rows_l = rad_shape(l_rad)
        print(f"[verify] modern rad channels={ch_m} rows={rows_m}")
        print(f"[verify] legacy rad channels={ch_l} rows={rows_l})")

if __name__ == "__main__":
    main()

