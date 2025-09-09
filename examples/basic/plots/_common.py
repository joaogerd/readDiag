# Utilitário comum importável pelos demais scripts (mesmo diretório).
from __future__ import annotations
import sys
from pathlib import Path

def discover_base() -> Path:
    """Return the project root (directory containing test assets).

    The heuristic assumes this file lives under ``tests/``; therefore
    the parent directory of this file is treated as the project root.

    Returns
    -------
    pathlib.Path
        Absolute path to the project root.
    """
    here = Path(__file__).resolve()
    root = here
    while root.name != "readDiag" and root.parent != root:
        root = root.parent
    return root

def open_diag(path: str):
    try:
        import readDiag as rd
        if hasattr(rd, "open_diagnostic"):
            return rd.open_diagnostic(path)
    except Exception:
        pass
    # fallback ao backend clássico
    from readDiag.io.reader import diagAccess
    return diagAccess(path)

def ensure_outdir() -> Path:
    out = Path("_out")
    out.mkdir(exist_ok=True, parents=True)
    return out

def arg_or_default(i: int, default):
    try:
        return sys.argv[i]
    except Exception:
        return default

# Absolute project root (used to derive default data locations)
PROJECT_ROOT: Path = discover_base()

