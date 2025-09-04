from __future__ import annotations
import os
from pathlib import Path
import pytest

# Marcação padrão da suíte legacy
pytestmark = pytest.mark.legacy

# Skip elegante de TODO o diretório legacy se não houver dados
DATA_DIR = Path(os.environ.get("READDIAG_TEST_DATA_DIR", "tests/data"))
_has_any_data = any(
    (DATA_DIR / name).exists()
    for name in [
        "diag_conv_01.2024013018",
        "diag_conv_03.2024013018",
        "diag_amsua_n15_01.2024013018",
        "diag_rad_01.2024013018",
    ]
)

def pytest_collection_modifyitems(config, items):
    if not _has_any_data:
        skip = pytest.mark.skip(reason="legacy tests require sample data under tests/data (or READDIAG_TEST_DATA_DIR)")
        for it in items:
            if str(it.fspath).startswith(str(Path(__file__).parent.resolve())):
                it.add_marker(skip)
