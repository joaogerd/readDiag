import os
import sys
import pytest
import pandas as pd
from readDiag import diagAccess
from datetime import datetime

# Garante que o diretório ROOT (raiz do projeto) esteja no sys.path
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
    df = diag.get_data_frame()

    # [1] Tipo de dado deve ser radiância
    assert diag.get_data_type() == 2, "Esperado data_type=2 para arquivos de radiância"

    # [2] Estrutura de topo deve conter 'sensor', 'kx' e 'dataframes'
    for key in ["sensor", "kx", "dataframes"]:
        assert key in df, f"'{key}' ausente na estrutura de topo para radiância"

    nested = df["dataframes"]

    # [3] Estrutura 'channel_df'
    ch = nested.get("channel_df")
    assert isinstance(ch, pd.DataFrame), "'channel_df' deve ser DataFrame"
    nchanl = ch.shape[0]
    assert nchanl > 0, "channel_df não pode estar vazio"

    # [4] Estrutura 'diagbuf_df'
    db = nested.get("diagbuf_df")
    assert isinstance(db, pd.DataFrame), "'diagbuf_df' deve ser DataFrame"
    assert not db.empty, "'diagbuf_df' está vazio"

    # [5] Estrutura 'diagbufchan_df'
    dbc = nested.get("diagbufchan_df")
    assert isinstance(dbc, list), "'diagbufchan_df' deve ser uma lista"
    assert len(dbc) == nchanl, "diagbufchan_df deve conter um DataFrame por canal"
    for i, df_chan in enumerate(dbc):
        assert isinstance(df_chan, pd.DataFrame), f"Canal {i} não é DataFrame"
        assert not df_chan.empty, f"Canal {i} está vazio"

    # [6] Estrutura 'diagbufex_df'
    dbe = nested.get("diagbufex_df")
    assert isinstance(dbe, pd.DataFrame), "'diagbufex_df' deve ser DataFrame"
    assert not dbe.empty, "'diagbufex_df' está vazio"

    # [7] get_date() agora deve funcionar também para radiância
    dt = diag.get_date()
    assert isinstance(dt, datetime), "get_date() deve retornar datetime"
    assert dt == datetime(2020, 1, 1, 0), f"Data incorreta: {dt}"

