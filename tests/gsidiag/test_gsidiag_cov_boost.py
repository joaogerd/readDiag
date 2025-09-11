# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import sys
from types import ModuleType
import warnings

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest


# ======================================================================
# ImpactAnalyzer — validações, erros e caminhos “sem dados”
# Fonte: impact_legacy.py
# ======================================================================

def test_impact_validate_requires_var_for_conv():
    import gsidiag.impact_legacy as imp

    class DummyConv:
        def __init__(self):
            self.var = None
        def get_data_type(self):
            return 1  # conv
    with pytest.raises(ValueError):
        imp.ImpactAnalyzer(DummyConv())


def test_impact_from_pair_type_mismatch(monkeypatch, tmp_path):
    import gsidiag.impact_legacy as imp

    class FakeA:
        def __init__(self, dtype):
            self._dtype = dtype
            self.var = "t"
            self._data_frame = {"t": {120: pd.DataFrame({"omf":[1.0], "end_err":[2.0]})}}
        def get_data_type(self): return self._dtype
        def get_data_frame(self): return self._data_frame

    # Força diagAccess a alternar tipos
    seq = [FakeA(1), FakeA(2)]
    monkeypatch.setattr(imp, "diagAccess", lambda *a, **k: seq.pop(0))

    with pytest.raises(ValueError):
        imp.ImpactAnalyzer.from_pair("omf.diag", "oma.diag", var="t")


def test_impact_plot_impact_bar_empty_raises(monkeypatch):
    import gsidiag.impact_legacy as imp

    class DummyRad:
        def get_data_type(self): return 2  # rad
        def get_data_frame(self):
            # ausência de 'oma'/'error' → compute_all_metrics() vazio
            return {"dataframes": {"diagbufchan_df": [pd.DataFrame({"omf":[1.0]})]}}

    a = imp.ImpactAnalyzer.__new__(imp.ImpactAnalyzer)
    a.diag = DummyRad()
    # compute_all_metrics vazio → plot_impact_bar deve levantar ValueError
    with pytest.raises(ValueError):
        a.plot_impact_bar("TI")


def test_impact_plot_all_impact_subplots_no_data(monkeypatch):
    import gsidiag.impact_legacy as imp

    class A:
        def compute_all_metrics(self): return pd.DataFrame()

    with pytest.raises(RuntimeError):
        imp.plot_all_impact_subplots([A(), A()], labels=["x","y"])


# ======================================================================
# legacy_api.read_diag — ramos de construção/erros e helpers
# Fonte: legacy_api.py
# ======================================================================

def _install_fake_engine(monkeypatch, *, file_type=1):
    """Cria *fakes* para diagAccess/AccessAdapter/DiagnosticAPI."""
    import gsidiag.legacy_api as leg

    class FakeRaw:
        def __init__(self):
            self._dtype = file_type
        def get_data_type(self): return self._dtype
        def get_date(self): return "2024-01-30 18:00:00"

    class FakeAPI:
        # CONV
        def variables(self): return ["t", "q"]
        def kx_list(self, v): return [120, 130] if v == "t" else [130]
        def frame_conv(self, v, kx):
            return pd.DataFrame({"lat":[-10,0,10],
                                 "lon":[-45,-46,-47],
                                 "omf":[0.1, -0.2, 0.05]})
        # RAD
        def channels(self): return [0,1,2]
        def frame_channel(self, ch):
            return pd.DataFrame({"lat":[0,1], "lon":[0,1], "omf":[0.2, 0.3]})

    # diagAccess → apenas retorna FakeRaw
    monkeypatch.setattr(leg, "diagAccess", lambda *a, **k: FakeRaw())
    # AccessAdapter → ignora e devolve FakeAPI
    monkeypatch.setattr(leg, "AccessAdapter", lambda _raw: FakeAPI())
    # DiagnosticAPI nome apenas para coerência (não é usado)
    monkeypatch.setattr(leg, "DiagnosticAPI", object)


def test_legacy_read_diag_builds_obsinfo_and_lists(monkeypatch):
    import gsidiag.legacy_api as leg
    _install_fake_engine(monkeypatch, file_type=1)

    obj = leg.read_diag(["f1.diag", "f2.diag"])
    # Deve materializar MultiIndex idate/var/kx e listar variáveis/KX
    assert set(obj.varNames) == {"t","q"}
    assert 120 in obj._variablesList["t"]
    assert set(obj.get_unique_vars()) == {"t","q"}
    assert set(obj.get_unique_kx()) >= {120, 130}
    assert obj.get_unique_dates() == ["2024-01-30 18:00:00"]


def test_legacy_read_diag_index_filter_and_errors(monkeypatch):
    import gsidiag.legacy_api as leg
    _install_fake_engine(monkeypatch, file_type=1)

    obj = leg.read_diag("f1.diag")
    # summarize com var inexistente → KeyError
    with pytest.raises(KeyError):
        obj.summarize(varName="zz")
    # tmsummarize sem args obrigatórios → KeyError
    with pytest.raises(KeyError):
        obj.tmsummarize(varName=None, kx=120)
    with pytest.raises(KeyError):
        obj.tmsummarize(varName="t", kx=None)
    # filter_multiindex: nível ausente → KeyError
    with pytest.raises(KeyError):
        obj.filter_multiindex(obj.obsInfo, [("NOPE", 1)])


def test_legacy_pvmap_requires_args(monkeypatch):
    import gsidiag.legacy_api as leg
    _install_fake_engine(monkeypatch, file_type=1)
    # Evita depender de wrappers reais: substitui por stubs
    monkeypatch.setattr(leg, "_plot_oma_map", lambda *a, **k: "OMA_OK")

    obj = leg.read_diag("f1.diag")
    with pytest.raises(ValueError):
        obj.pvmap()  # precisa de var e kx
    # Nota: a implementação atual duplica 'kx' ao repassar para _plot_oma_map,
    # gerando TypeError quando passamos kx em kwargs. Mantemos como xfail.
    # Quando corrigido no código-fonte, o assert abaixo deve passar:
    assert obj.pvmap(varName="t", kx=120) == "OMA_OK"


def test_legacy_plot_dispatch_omf_oma(monkeypatch):
    import gsidiag.legacy_api as leg
    _install_fake_engine(monkeypatch, file_type=1)

    monkeypatch.setattr(leg, "_plot_omf_map", lambda *a, **k: "OMF_OK")
    monkeypatch.setattr(leg, "_plot_oma_map", lambda *a, **k: "OMA_OK")

    obj = leg.read_diag("f1.diag")
    assert obj.plot("t", 120, param="omf") == "OMF_OK"
    assert obj.plot("t", 120, param="oma") == "OMA_OK"
    with pytest.raises(NotImplementedError):
        obj.plot("t", 120, param="unknown")


def test_legacy_constructor_lists_length_mismatch(monkeypatch):
    import gsidiag.legacy_api as leg
    _install_fake_engine(monkeypatch, file_type=1)
    with pytest.raises(ValueError):
        leg.read_diag(["a.diag", "b.diag"], diag_file_anl=["only_one.anl"])


def test_legacy_radiance_materialization(monkeypatch):
    import gsidiag.legacy_api as leg
    _install_fake_engine(monkeypatch, file_type=2)
    obj = leg.read_diag("rad.diag")
    # Em rad, varNames vira ['radiance'] e obsInfo é flat com coluna channel
    assert obj.varNames == ["radiance"]
    assert "channel" in obj.obsInfo.columns


# ======================================================================
# gsidiag.utils — branch com import “real” de readDiag._utils
# Fonte: utils.py
# ======================================================================

def test_utils_imports_from_real_readDiag_utils(monkeypatch):
    # injeta um módulo sintético readDiag._utils com as funções
    fake = ModuleType("readDiag._utils")
    def _deprecated(msg): warnings.warn(f"[REAL] {msg}", DeprecationWarning)
    def _check_kind(*a, **k): return True
    fake.deprecated = _deprecated
    fake.check_kind = _check_kind
    sys.modules["readDiag._utils"] = fake

    # força recarregar gsidiag.utils para pegar o caminho “try:” (import real)
    if "gsidiag.utils" in sys.modules:
        del sys.modules["gsidiag.utils"]
    u = importlib.import_module("gsidiag.utils")
    assert u.deprecated is fake.deprecated
    assert u.check_kind is fake.check_kind
