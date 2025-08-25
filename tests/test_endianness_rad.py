"""
Endianness sanity for radiance: ensure DataFrame operations don't crash.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest
from readDiag import diagAccess

@pytest.mark.usefixtures("rad01_path")
def test_endianness_df_ops(rad01_path: Path):
    d = diagAccess(str(rad01_path))
    data = d.get_data_frame()
    dbc = data["dataframes"]["diagbufchan_df"]
    assert isinstance(dbc, list) and len(dbc) > 0
    # Must not raise (used to raise on big-endian buffers)
    head = dbc[0].head()
    desc = dbc[0].describe()
    assert isinstance(head, pd.DataFrame)
    assert isinstance(desc, pd.DataFrame)

