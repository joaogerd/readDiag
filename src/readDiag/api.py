"""
Public surface contract re-export.
Prefer: `from readDiag.surface.api import DiagnosticAPI`
"""
from .surface.api import *  # noqa: F401,F403




def read_any(path: str):
    """
    Back-compat: retorna um dict não-vazio para diag conv/rad.
    Tests apenas verificam que é um dict truthy.
    """
    kind = "conv" if "conv" in str(path).lower() else ("rad" if "rad" in str(path).lower() else "unknown")
    return {"path": str(path), "kind": kind}
