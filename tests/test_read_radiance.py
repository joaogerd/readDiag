import os, sys
import pytest
import pandas as pd
from readDiag import diagAccess
from datetime import datetime

# garante que ROOT esteja no PATH (similar ao baseline)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

RAD_FILES = [
    "data/diag_amsua_metop-a_01.2020010100",
    "data/diag_amsua_metop-a_03.2020010100",
    "data/diag_amsua_n15_01.2020010100",
    "data/diag_amsua_n15_03.2020010100",
    "data/diag_amsua_n18_01.2020010100",
    "data/diag_amsua_n18_03.2020010100",
    "data/diag_amsua_n19_01.2020010100",
    "data/diag_amsua_n19_03.2020010100",
]

@pytest.mark.parametrize("relpath", RAD_FILES)
def test_radiance_structure(relpath):
    path = os.path.join(ROOT, relpath)
    diag = diagAccess(path)

    # 1) data_type == 2
    assert diag.get_data_type() == 2, "esperado data_type 2 para radiância"

    df = diag.get_data_frame()
    # 2) chaves de topo
    assert 'obstype' in df
    assert 'dplat' in df
    assert 'dataframes' in df

    nested = df['dataframes']
    # 3) channel_df
    ch = nested['channel_df']
    assert isinstance(ch, pd.DataFrame), "channel_df deve ser DataFrame"
    nchanl = ch.shape[0]
    assert nchanl > 0, "nchanl deve ser > 0"

    # 4) diagbuf_df
    db = nested['diagbuf_df']
    assert isinstance(db, pd.DataFrame) and not db.empty, "diagbuf_df inválido"

    # 5) diagbufchan_df
    dbc = nested['diagbufchan_df']
    assert isinstance(dbc, list), "diagbufchan_df deve ser lista"
    assert len(dbc) == nchanl, "lista de diagbufchan_df deve ter comprimento nchanl"
    assert all(isinstance(x, pd.DataFrame) and not x.empty for x in dbc)

    # 6) diagbufex_df
    dbe = nested['diagbufex_df']
    assert isinstance(dbe, pd.DataFrame) and not dbe.empty, "diagbufex_df inválido"

    # 7) get_date() não se aplica a radância
    with pytest.raises(AttributeError):
        diag.get_date()

