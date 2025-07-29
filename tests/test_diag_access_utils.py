import os
import sys
import pytest
import pandas as pd
import numpy as np

# garante que o ROOT (com diagAccess.py) esteja no PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# importa a classe legacy
from readDiag import diagAccess

@pytest.fixture
def conv_diag():
    return diagAccess("data/diag_conv_01.2020010100", var="t")

@pytest.fixture
def rad_diag():
    return diagAccess("data/diag_amsua_n15_01.2020010100", use_memmap=False)

def test_get_variables(conv_diag):
    vars = conv_diag.get_variables()
    assert isinstance(vars, list)
    assert "t" in vars

def test_get_kx_list(conv_diag):
    kxs = conv_diag.get_kx_list("t")
    assert isinstance(kxs, list)
    #assert all(isinstance(k, int) for k in kxs)
    assert all(isinstance(k, (int, np.integer)) for k in kxs)

def test_get_dataframe(conv_diag):
    kxs = conv_diag.get_kx_list("t")
    df = conv_diag.get_dataframe("t", kxs[0])
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

def test_get_channels(rad_diag):
    chans = rad_diag.get_channels()
    assert isinstance(chans, list)
    assert all(isinstance(c, int) for c in chans)

def test_get_metadata_conv(conv_diag):
    meta = conv_diag.get_metadata()
    assert meta["data_type"] == "conv"
    assert "file_name" in meta
    assert "date" in meta

def test_get_metadata_rad(rad_diag):
    meta = rad_diag.get_metadata()
    assert meta["data_type"] == "rad"
    assert "sensor" in meta
    assert "kx" in meta
