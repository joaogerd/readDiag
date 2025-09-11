# tests/readdiag/surface/test_access_adapter_conv.py
import pandas as pd
from datetime import datetime
from readDiag.surface import AccessAdapter
import pytest

from readDiag.surface.access_adapter import AccessAdapter
from readDiag.schema.naming import resolve_col_in_df

class FakeConvBackend:
    """
    Backend mínimo para 'conv' que expõe exatamente o que o AccessAdapter usa.
    """

    def __init__(self):
        # vars e KX disponíveis
        self._vars = {"t": [120, 121], "q": [120]}

        # DataFrames por (var, kx).
        # Notar: usamos 'idqc' (legado) de propósito para cobrir a
        # resolução de alias ('qc_flag' -> 'idqc').
        self._dfs = {
            ("t", 120): pd.DataFrame(
                {
                    "lat": [0.0, 1.0],
                    "lon": [10.0, 11.0],
                    "omf": [0.1, -0.2],
                    "idqc": [1, 0],
                    "kx": [120, 120],
                }
            ),
            ("t", 121): pd.DataFrame(
                {
                    "lat": [2.0],
                    "lon": [12.0],
                    "omf": [0.05],
                    "idqc": [1],
                    "kx": [121],
                }
            ),
            ("q", 120): pd.DataFrame(
                {
                    "lat": [3.0],
                    "lon": [13.0],
                    "omf": [-0.1],
                    "idqc": [0],
                    "kx": [120],
                }
            ),
        }

        # metadado opcional usado por AccessAdapter.file_path (não é obrigatório,
        # mas não atrapalha e ajuda a cobrir fallback)
        self.file_name = "/tmp/fake_conv_diag.bufr"

    # Interface esperada pelo AccessAdapter (ramo conv)
    def kind(self):
        return "conv"

    def get_variables(self):
        return list(self._vars.keys())

    def get_kx_list(self, var):
        return list(self._vars[var])

    def get_dataframe(self, var, kx):
        return self._dfs[(var, kx)].copy()

    def bring(self, var, kx, cols):
        """
        Algumas rotas do AccessAdapter chamam o backend.bring; para garantir
        que o teste não quebre, resolvemos alias aqui também.
        """
        df = self.get_dataframe(var, kx)
        cols_resolvidos = [resolve_col_in_df(df.columns, c, "conv") for c in cols]
        return df[cols_resolvidos].copy()

    def get_file_info(self):
        return {
            "kind": "conv",
            "file_name": getattr(self, "file_name", "/tmp/fake_conv_diag.bufr"),
            "cycle_dt": None,
        }
        
class _OnlyRadBackend:
    def kind(self):
        return "rad"

    def channels(self):
        return [1]

    def frame_channel(self, ch):
        import pandas as pd
        return pd.DataFrame({"lat":[0.0], "lon":[0.0], "qc_flag":[1]})

    # NEW: exigido pelo AccessAdapter.__init__
    def get_file_info(self):
        return {
            "kind": "rad",
            "file_name": "/tmp/fake_rad_diag.h5",
            "cycle_dt": None,
        }

def test_conv_methods_guard_on_rad_dataset():
    a = AccessAdapter(_OnlyRadBackend())
    # variables() deve retornar [] em dataset rad (guard interno)
    with pytest.raises(ValueError):
        a.variables()
    # chamar frame_conv em rad deve levantar ValueError
    with pytest.raises(ValueError):
        a.frame_conv("t", 120)

def test_access_adapter_conv_table_guard_and_legacy_shape():
    a = AccessAdapter(FakeConvBackend())
    assert a.kind() == "conv"

    # table() não é suportado para conv → ValueError
    with pytest.raises(ValueError):
        a.table("channel_df")

    # get_data_frame monta {var: {kx: df}}
    g = a.get_data_frame()
    assert isinstance(g, dict) and "t" in g and 120 in g["t"]
    df = g["t"][120]
    assert {"lat", "lon", "omf"} <= set(df.columns)


def test_get_data_frame_nested_shape_and_keys():
    a = AccessAdapter(FakeConvBackend())
    g = a.get_data_frame()  # deve montar {var: {kx: df}}
    assert set(g.keys()) == {"t", "q"}
    assert set(g["t"].keys()) == {120, 121}
    assert 120 in g["q"]
    # todos valores devem ser DataFrames
    assert all(all(hasattr(df, "columns") for df in inner.values()) for inner in g.values())

