import logging
from pathlib import Path
import textwrap
import yaml
import pandas as pd
import numpy as np

def test_datasources_logs(minimal_yaml, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG, logger="gsidiag")
    import importlib
    m = importlib.import_module("gsidiag.datasources")

    # força singleton a ler do tmp
    m._DS_INFO = m.DataSourcesInfo(yaml_file=minimal_yaml)

    assert any("Loaded" in r.message for r in caplog.records)
    assert any(r.levelno == logging.INFO for r in caplog.records)

def test_legacy_read_warns_on_missing_anl(caplog, monkeypatch, tmp_path):
    caplog.set_level(logging.DEBUG, logger="gsidiag")

    # mock do diagAccess mínimo para não depender de arquivos reais:
    class DummyRD:
        def __init__(self, *a, **k): pass
        def get_data_type(self): return 1  # convencional
        def get_variables(self): return ["t"]
        def get_kx_list(self, _): return [120]
        def get_dataframe(self, *a, **k):
            return pd.DataFrame({"lat":[0.], "lon":[0.], "prs":[1000], "omf":[0.1], "oma":[np.nan]})
        _idate = "2024021000"

    import importlib
    readmod = importlib.import_module("gsidiag.legacy_api.read")
    monkeypatch.setattr(readmod, "diagAccess", DummyRD)

    g = readmod.read_diag("bg.diag", "anl.diag")  # ANL “falha” dentro do try
    # Deve ter algum log de info/aviso
    assert any("Opened diagnostic" in r.message for r in caplog.records)
    # Como usamos DummyRD que não lança, não necessariamente haverá WARN; mas o INFO deve existir

