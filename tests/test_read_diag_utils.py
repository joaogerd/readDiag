from __future__ import annotations
from datetime import datetime

import pandas as pd
import pytest


@pytest.fixture()
def rd(fakepkg):
    mod = __import__(f"{fakepkg}.__main__", fromlist=["*"])
    return mod.read_diag(diag_file="data/diag_conv_01.2024013018")


def test_filter_multiindex(rd):
    # Usa a própria obsInfo para testar o filtro
    idate = rd.obsInfo.index.get_level_values("idate").unique()[0]
    df_filtered = rd.filter_multiindex(
        rd.obsInfo, [("idate", idate), ("var", "t"), ("kx", 120)]
    )
    assert isinstance(df_filtered, pd.DataFrame)
    assert not df_filtered.empty
    # Garante consistência do filtro
    assert set(df_filtered.index.get_level_values("var")) == {"t"}
    assert set(df_filtered.index.get_level_values("kx")) == {120}


def test_get_unique_helpers(rd):
    # Datas
    dates = rd.get_unique_dates()
    assert isinstance(dates, list) and dates, "get_unique_dates deve retornar lista não-vazia"

    # kx e vars (sem data)
    kx_all = rd.get_unique_kx()
    vars_all = rd.get_unique_vars()
    assert 120 in kx_all and 100 in kx_all
    assert "t" in vars_all and "q" in vars_all

    # Com data específica
    d0 = rd.obsInfo.index.get_level_values("idate").unique()[0]
    kx_d0 = rd.get_unique_kx(d0)
    vars_d0 = rd.get_unique_vars(d0)
    assert isinstance(kx_d0, list) and isinstance(vars_d0, list)

