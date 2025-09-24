
import types
import pandas as pd
import numpy as np
import importlib
import sys

def _make_conv_stub():
    class RD:
        def __init__(self):
            self._type = 1
        def get_data_type(self):
            return 1  # conventional
        def get_variables(self):
            return ["ps"]
        def get_kx_list(self, obsName):
            assert obsName == "ps"
            return [120]
        def get_dataframe(self, obsName, kx):
            assert obsName == "ps" and kx == 120
            # Minimal realistic columns used downstream
            n = 5
            df = pd.DataFrame({
                "lat": np.linspace(-10, 10, n),
                "lon": np.linspace( -5,  5, n),
                "idqc": [0]*n,
                "iuse": [1]*n,
                "obs": np.linspace(1000, 1005, n),
                "omf": np.linspace(0.1, 0.5, n),
                "oma": np.zeros(n),
                "kx": [120]*n,
                "var": ["ps"]*n,
                "time": np.arange(n),
            })
            return df
    return RD()

def test_read_conv_builds_obsinfo(monkeypatch):
    # Inject stub into readDiag.reader.diagAccess
    import types, gsidiag
    import gsidiag.legacy_api.read as legacy_read
    def fake_diag_access(*a, **k):
        return _make_conv_stub()
    sys.modules["readDiag.reader"].diagAccess = fake_diag_access

    g = legacy_read.read_diag("bg_conv.diag", None)
    assert isinstance(g.varNames, list) and "ps" in g.varNames
    assert "ps" in g.obsInfo and not g.obsInfo["ps"].empty

    # close should return 0 and keep object usable (legacy behavior)
    assert g.close() == 0
