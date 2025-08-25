"""
Baseline reads for conv and rad files.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd
import pytest
from readDiag import diagAccess

@pytest.mark.usefixtures("conv01_path", "rad01_path")
def test_read_baseline(conv01_path: Path, rad01_path: Path):
    # Conventional
    d_conv = diagAccess(str(conv01_path))
    df_dict = d_conv.get_data_frame()
    assert isinstance(df_dict, dict) and df_dict
    dt = d_conv.get_date()
    assert isinstance(dt, datetime)

    # Conventional structure {var -> {kx -> DataFrame}}
    any_df = False
    for var, sub in df_dict.items():
        assert isinstance(sub, dict)
        for kx, df in sub.items():
            assert isinstance(df, pd.DataFrame)
            any_df = any_df or not df.empty
    assert any_df, "All conventional frames are empty."

    # Radiance
    d_rad = diagAccess(str(rad01_path))
    rad = d_rad.get_data_frame()
    for key in ["sensor", "kx", "dataframes"]:
        assert key in rad
    assert any(isinstance(x, pd.DataFrame) for x in rad["dataframes"].values())

