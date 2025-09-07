from __future__ import annotations
import argparse
import json
import os
import platform
import sys
from importlib import metadata as im
from typing import Dict, Any, List

from .open import open_diagnostic


def _pkg_version(name: str) -> str:
    """Return installed package version or 'not installed'."""
    try:
        return im.version(name)
    except im.PackageNotFoundError:
        return "not installed"
    except Exception:
        return "unknown"


def _readDiag_version() -> str:
    # Tenta pegar via importlib.metadata; se falhar, tenta atributo __version__
    v = _pkg_version("readDiag")
    if v not in ("not installed", "unknown"):
        return v
    try:
        import readDiag as _rd  # type: ignore
        return getattr(_rd, "__version__", "unknown")
    except Exception:
        return "unknown"


def _collect_versions(extra: bool = False) -> Dict[str, Any]:
    """Coleta informações de ambiente com dependências opcionais."""
    info: Dict[str, Any] = {
        "readDiag": _readDiag_version(),
        "Python": platform.python_version(),
        "OS": platform.platform(),
        "Executable": sys.executable,
    }

    # Pacotes principais
    libs = [
        ("NumPy", "numpy"),
        ("Pandas", "pandas"),
        ("Matplotlib", "matplotlib"),
        ("Cartopy", "cartopy"),
        ("GeoPandas", "geopandas"),
    ]

    # Extras úteis
    if extra:
        libs.extend([
            ("SciPy", "scipy"),
            ("xarray", "xarray"),
            ("netCDF4", "netCDF4"),
            ("Shapely", "shapely"),
            ("PyProj", "pyproj"),
            ("CFGRIB", "cfgrib"),
            ("eccodes", "eccodes"),
        ])

    for label, pkg in libs:
        info[label] = _pkg_version(pkg)

    return info


def _print_versions_table(info: Dict[str, Any]) -> None:
    width = max(len(k) for k in info) + 2
    for k, v in info.items():
        print(f"{k:<{width}}: {v}")


def cli() -> int:
    p = argparse.ArgumentParser(
        prog="readDiag",
        description="Lightweight CLI for readDiag: environment checks and quick file inspection.",
    )
    p.add_argument("file", nargs="?", help="Diagnostic file to inspect (conv or rad)")
    p.add_argument("--version", action="store_true", help="Show readDiag package version and exit")
    p.add_argument(
        "--show-versions",
        action="store_true",
        help="Show environment versions (Python, OS, NumPy, Pandas, Matplotlib, Cartopy, ...)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="When used with --show-versions, print JSON instead of a table",
    )
    p.add_argument(
        "--extra",
        action="store_true",
        help="When used with --show-versions, include extra packages (scipy, xarray, netCDF4, shapely, pyproj, cfgrib, eccodes)",
    )
    args = p.parse_args()

    # 1) Apenas versão do pacote
    if args.version:
        print(_readDiag_version())
        return 0

    # 2) Tabela (ou JSON) de versões/ambiente
    if args.show_versions:
        info = _collect_versions(extra=args.extra)
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            _print_versions_table(info)
        return 0

    # 3) Sem flags -> se passou arquivo, faz um "inspect" rápido
    if args.file:
        api = open_diagnostic(args.file)
        m = api.meta()
        print(f"{m.kind} | date={m.date} | file={m.file_name}")
        if m.kind == "conv":
            for v in api.variables():
                kx = api.kx_list(v)
                print(f"  var={v} kx={kx}")
        else:
            print(f"  channels={api.channels()}")
        return 0

    # 4) Sem nada — mostra ajuda
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())

