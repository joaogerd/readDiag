from __future__ import annotations
from datetime import datetime

import pandas as pd
import pytest


@pytest.fixture()
def rd(fakepkg):
    mod = __import__(f"{fakepkg}.__main__", fromlist=["*"])
    # Instancia normalmente (usa os stubs); após __init__, obsInfo deve existir
    return mod.read_diag(diag_file="data/diag_conv_01.2024013018")


def test_obsinfo_is_multiindex_and_has_geometry(rd):
    # obsInfo é concatenado e tem MultiIndex ['idate', 'var', 'kx']
    assert isinstance(rd.obsInfo, pd.DataFrame)
    assert list(rd.obsInfo.index.names) == ["idate", "var", "kx"]
    # Coluna 'geometry' (stub) deve existir
    assert "geometry" in rd.obsInfo.columns
    # idate vindo do stub
    assert rd.obsInfo.index.get_level_values("idate").unique()[0] == datetime(2024, 1, 30, 18)


def test_overview_and_internal_state(rd):
    # _overview é chamado dentro de _process_conventional_data
    assert isinstance(rd.varNames, list) and set(rd.varNames) >= {"t", "q"}
    assert isinstance(rd._variablesList, dict)
    assert "t" in rd._variablesList and 120 in rd._variablesList["t"]


def test_summarize_happy_path(rd):
    # Escolhe uma combinação existente (var='t', kx=120) e um idate válido
    idate = rd.obsInfo.index.get_level_values("idate").unique()[0]
    out = rd.summarize(varName="t", kx=120, idate=idate)
    assert isinstance(out, pd.DataFrame)
    assert not out.empty

