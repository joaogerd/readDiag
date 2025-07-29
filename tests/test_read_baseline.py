import os
import sys
import pytest
import pandas as pd
from datetime import datetime

# garante que o ROOT (com diagAccess.py) esteja no PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import os
import pytest
import pandas as pd
from datetime import datetime
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

    # [1] Estrutura básica
    assert isinstance(df_dict, dict), f"O retorno de get_data_frame() deve ser um dict, veio {type(df_dict)}"
    assert df_dict, "O dicionário retornado está vazio"

    # [2] Data deve estar presente e correta
    dt = diag.get_date()
    assert isinstance(dt, datetime), "get_date() deve retornar um datetime"
    assert dt == datetime(2020, 1, 1, 0), f"Data incorreta: esperava 2020-01-01 00:00, veio {dt}"

    if "diag_conv" in relpath:
        # [3] Estrutura convencional: var → kx → DataFrame
        for var, kx_block in df_dict.items():
            assert isinstance(kx_block, dict), f"Esperado dict para '{var}', veio {type(kx_block)}"
            for kx, df in kx_block.items():
                assert isinstance(df, pd.DataFrame), f"{var}[{kx}] não é DataFrame"
                assert not df.empty, f"{var}[{kx}] está vazio"

    else:
        # [4] Estrutura radiância: sensor/kx/dataframes
        assert "sensor" in df_dict, "'sensor' ausente em dados de radiância"
        assert "kx" in df_dict, "'kx' ausente em dados de radiância"
        assert "dataframes" in df_dict, "'dataframes' ausente em dados de radiância"
        dfs = df_dict["dataframes"]
        assert isinstance(dfs, dict), "'dataframes' deve ser um dicionário"
        assert any(isinstance(df, pd.DataFrame) for df in dfs.values()), "Nenhum DataFrame encontrado"

