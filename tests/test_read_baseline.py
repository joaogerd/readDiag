import os
import sys
import pytest
import pandas as pd
from datetime import datetime

# garante que o ROOT (com diagAccess.py) esteja no PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# importa a classe legacy
from readDiag import diagAccess

TEST_FILES = [
    "data/diag_conv_01.2020010100",
    "data/diag_conv_03.2020010100",
    "data/diag_amsua_n15_01.2020010100",
    "data/diag_amsua_n15_03.2020010100",
]

@pytest.mark.parametrize("relpath", TEST_FILES)
def test_read_baseline(relpath):
    path = os.path.join(ROOT, relpath)
    diag = diagAccess(path)
    df_dict = diag.get_data_frame()

    # 1) sempre um dict não‐vazio
    assert isinstance(df_dict, dict)
    assert df_dict, "o dicionário de dataframes não pode ser vazio"

    if "diag_conv" in relpath:
        # 2) para conv: cada entrada deve ser DataFrame ou dict de DataFrames não‐vazios
        for var, blk in df_dict.items():
            if isinstance(blk, dict):
                for chan, df in blk.items():
                    assert isinstance(df, pd.DataFrame), f"{var}[{chan}] não é DataFrame"
                    assert not df.empty, f"{var}[{chan}] retornou vazio"
            else:
                assert isinstance(blk, pd.DataFrame), f"{var} não é DataFrame"
                assert not blk.empty, f"{var} retornou vazio"

        # 3) date ok para conv
        dt = diag.get_date()
        assert isinstance(dt, datetime)
        assert dt == datetime(2020, 1, 1, 0), f"esperava 2020-01-01 00:00, veio {dt}"

    else:
        # apenas garantimos que radiância (_amsua_) infelizmente não inicializa data
        with pytest.raises(AttributeError):
            diag.get_date()
        # e que o dict retornado tem ao menos uma chave
        assert len(df_dict) > 0

