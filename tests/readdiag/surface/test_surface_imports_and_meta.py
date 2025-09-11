# tests/readdiag/surface/test_surface_imports_and_meta.py
from datetime import datetime
from readDiag.surface import Metadata, DiagnosticAPI, Kind  # só valida import público

def test_metadata_pretty_basic():
    m = Metadata(
        file_name="diag_amsua_n15_2024013018",
        date=datetime(2024, 1, 30, 18),
        kind="rad",
        sensor="amsua",
        platform="n15",
        n_channels=15,
        n_obs=1234,
    )
    s = m.pretty()
    # linhas previstas pela doc/impl da função pretty (rótulos e “–” para None)
    assert "Arquivo :" in s and "Data    :" in s and "Tipo    :" in s  # :contentReference[oaicite:0]{index=0}

