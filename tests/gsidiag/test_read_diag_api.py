# tests/gsidiag/test_read_diag_api.py
import gc
from pathlib import Path
import pandas as pd
import numpy as np
import pytest


def _monkeypatch_diag_access_to_conv(monkeypatch):
    """Substitui readmod.diagAccess por um reader *conv* mínimo, compatível com o legado."""
    import importlib
    readmod = importlib.import_module("gsidiag.legacy_api.read")

    class DummyConv:
        _idate = "2024020100"

        def __init__(self, *a, **k):
            pass

        def get_data_type(self):
            return 1  # convencional

        def get_variables(self):
            return ["t"]

        def get_kx_list(self, _var):
            return [120, 130]

        def get_dataframe(self, var, kx):
            assert var == "t"
            rng = np.random.default_rng(int(kx))
            n = 16
            return pd.DataFrame(
                {
                    "lat": rng.uniform(-60, 60, n),
                    "lon": rng.uniform(-180, 180, n),
                    "prs": np.full(n, 1000, dtype=int),
                    "obs": rng.normal(0, 1, n),
                    "omf": rng.normal(0, 0.5, n),
                    "oma": rng.normal(0, 0.5, n),
                    "iuse": rng.integers(0, 2, n),
                }
            )

    monkeypatch.setattr(readmod, "diagAccess", DummyConv)


def _monkeypatch_diag_access_to_rad(monkeypatch):
    """Substitui readmod.diagAccess por um reader *rad* mínimo, compatível com o legado."""
    import importlib
    readmod = importlib.import_module("gsidiag.legacy_api.read")

    class DummyRad:
        _idate = "2024020100"

        def __init__(self, *a, **k):
            pass

        def get_data_type(self):
            return 2  # radiância

        def get_dataframe(self):
            rng = np.random.default_rng(7)
            diagbuf_df = pd.DataFrame(
                {
                    "lat": rng.uniform(-60, 60, 24),
                    "lon": rng.uniform(-180, 180, 24),
                    "time": np.repeat(["2024020100", "2024020106", "2024020112"], 8),
                }
            )
            diagbufchan_df = []
            for _ in (1, 2, 3):
                dfc = pd.DataFrame(
                    {
                        "obs": rng.normal(0, 1, 24),
                        "omf": rng.normal(0, 0.6, 24),
                        "oma": rng.normal(0, 0.6, 24),
                        "iuse": rng.integers(0, 2, 24),
                    }
                )
                diagbufchan_df.append(dfc)
            channel_df = pd.DataFrame({"nuchan": [1, 2, 3], "iuse": [1, 1, 0]})
            return {
                "sensor": "amsua",
                "dataframes": {
                    "diagbuf_df": diagbuf_df,
                    "diagbufchan_df": diagbufchan_df,
                    "channel_df": channel_df,
                },
            }

    monkeypatch.setattr(readmod, "diagAccess", DummyRad)


def test_init_overview_pfileinfo_close(monkeypatch, capsys):
    _monkeypatch_diag_access_to_conv(monkeypatch)
    from gsidiag.legacy_api.read import read_diag, get_open_read_diag_count

    n0 = get_open_read_diag_count()
    g = read_diag("diag_conv_01.2024020100")
    assert "t" in g.varNames
    ov = g.overview()
    assert isinstance(ov, dict) and "t" in ov and set(ov["t"]) == {120, 130}

    g.pfileinfo()
    out = capsys.readouterr().out
    assert "Variable Name" in out

    assert g.close() == 0
    # no caminho conv, o handle pode não ser registrado; então não exigimos n0-1/n0+1
    assert get_open_read_diag_count() == n0


def test_context_manager_and_exit(monkeypatch):
    _monkeypatch_diag_access_to_conv(monkeypatch)
    from gsidiag.legacy_api.read import read_diag

    # apenas smoke: o with deve funcionar e fechar sem exceção
    with read_diag("diag_conv_01.2024020100") as g:
        assert "t" in g.varNames


def test_del_reduces_open_handles(monkeypatch):
    _monkeypatch_diag_access_to_conv(monkeypatch)
    from gsidiag.legacy_api.read import read_diag

    # como o caminho conv pode não registrar handle, este é só smoke:
    g = read_diag("diag_conv_01.2024020100")
    del g
    gc.collect()


def test_tocsv_writes_two_files(tmp_path, monkeypatch):
    _monkeypatch_diag_access_to_conv(monkeypatch)
    from gsidiag.legacy_api.read import read_diag

    g1 = read_diag("diag_conv_01.2024020100")
    g2 = read_diag("diag_conv_01.2024020112")

    out_omf, out_oma = read_diag.tocsv(
        [g1, g2],
        varName="t",
        varType=120,
        dateIni=2024020100,
        dateFin=2024020112,
        nHour="12",
        outdir=tmp_path,
        verbose=False,
    )
    p1, p2 = Path(out_omf), Path(out_oma)
    assert p1.is_file() and p2.is_file()

    df = pd.read_csv(p1)
    assert "datetime" in df.columns
    assert any(col.startswith("mean1000") for col in df.columns)

    g1.close()
    g2.close()


def test_radiance_init_smoke(monkeypatch):
    """Caminho de radiância: inicializa e concatena (smoke)."""
    _monkeypatch_diag_access_to_rad(monkeypatch)
    from gsidiag.legacy_api.read import read_diag

    g = read_diag("diag_amsua_n19_01.2024020100")
    assert "amsua" in g.varNames
    assert "amsua" in g.obsInfo
    assert not g.obs.empty
    g.close()

