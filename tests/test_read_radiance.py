"""
Radiance structure checks.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest
from readDiag import diagAccess

@pytest.mark.usefixtures("rad01_path")
def test_radiance_structure(rad01_path: Path):
    diag = diagAccess(str(rad01_path))
    df = diag.get_data_frame()

    assert diag.get_data_type() == 2
    for key in ["sensor", "kx", "dataframes"]:
        assert key in df

    nested = df["dataframes"]
    assert isinstance(nested, dict)

    ch = nested.get("channel_df")
    db = nested.get("diagbuf_df")
    dbc = nested.get("diagbufchan_df")
    dbe = nested.get("diagbufex_df")

    assert isinstance(ch, pd.DataFrame) and ch.shape[0] > 0
    assert isinstance(db, pd.DataFrame) and not db.empty
    assert isinstance(dbc, list) and len(dbc) == ch.shape[0]
    assert all(isinstance(x, pd.DataFrame) and not x.empty for x in dbc)
    assert isinstance(dbe, pd.DataFrame) and not dbe.empty

