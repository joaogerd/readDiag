from __future__ import annotations
from pathlib import Path
import os
import pytest

from readDiag.open import open_diagnostic
from readDiag.reader import diagAccess
from readDiag.adapters.access import AccessAdapter

DATA_DIR = Path(os.environ.get("READDIAG_TEST_DATA_DIR", "tests/data"))

def _maybe(name: str) -> str | None:
    p = DATA_DIR / name
    return str(p) if p.exists() else None

# Roda os mesmos testes tanto com a Surface API (open_diagnostic)
# quanto com o backend embrulhado no AccessAdapter (diagAccess).
@pytest.fixture(params=["surface", "diagaccess"])
def handle_conv(request):
    path = _maybe("diag_conv_01.2024013018")
    if not path:
        pytest.skip("conv test data missing")
    if request.param == "surface":
        return open_diagnostic(path)
    else:
        return AccessAdapter(diagAccess(path))

@pytest.fixture(params=["surface", "diagaccess"])
def handle_rad(request):
    path = _maybe("diag_amsua_n15_01.2024013018") or _maybe("diag_rad_01.2024013018")
    if not path:
        pytest.skip("rad test data missing")
    if request.param == "surface":
        return open_diagnostic(path)
    else:
        return AccessAdapter(diagAccess(path))


