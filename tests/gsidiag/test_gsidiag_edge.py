# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import sys
import types
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest


# ---------- ImpactAnalyzer: top_k, metric inválido, labels ----------

def _fake_conv_analyzer():
    import gsidiag.impact_legacy as imp

    class FakeConv:
        def __init__(self):
            self._dtype = 1
            self.var = "t"
            self._df = {
                "t": {
                    120: pd.DataFrame({"omf":[1.0, 0.5], "oma":[0.2, 0.1], "end_err":[2.0, 2.0]}),
                    130: pd.DataFrame({"omf":[3.0, 1.0], "oma":[0.5, 0.2], "end_err":[5.0, 5.0]}),
                }
            }

        def get_data_type(self): return self._dtype
        def get_data_frame(self): return self._df

    conv = FakeConv()
    # cria 'error' = 1/end_err
    for df in conv.get_data_frame()["t"].values():
        df["error"] = 1.0 / df["end_err"]
    return imp.ImpactAnalyzer(conv)


def test_plot_impact_bar_top_k_and_invalid_metric():
    a = _fake_conv_analyzer()
    ax = a.plot_impact_bar("TI", top_k=1)  # cobre branch do parâmetro legado top_k
    assert isinstance(ax, plt.Axes)

    # métrica inválida → implementação atual levanta KeyError (aceitamos ambos)
    with pytest.raises((KeyError, ValueError)):
        a.plot_impact_bar("NOPE")


def test_plot_all_impact_subplots_labels_autofill():
    # A função não levanta erro quando labels tem tamanho diferente; apenas usa o que tem.
    a1 = _fake_conv_analyzer()
    a2 = _fake_conv_analyzer()
    import gsidiag.impact_legacy as imp

    fig_before = plt.gcf()
    imp.plot_all_impact_subplots([a1, a2], labels=["apenas_um"], metric="TI")
    fig = plt.gcf()
    try:
        assert len(fig.axes) == 2  # deve criar 2 subplots
    finally:
        plt.close(fig)
        plt.close(fig_before)


def test_plot_all_impact_subplots_show_is_called(monkeypatch):
    a1 = _fake_conv_analyzer()
    a2 = _fake_conv_analyzer()
    import gsidiag.impact_legacy as imp

    called = {"n": 0}
    def _fake_show():
        called["n"] += 1
    monkeypatch.setattr(plt, "show", _fake_show)

    fig_before = plt.gcf()
    imp.plot_all_impact_subplots([a1, a2], labels=["A1", "A2"], metric="TI")
    try:
        assert called["n"] == 1  # show foi chamado uma vez
    finally:
        plt.close(plt.gcf())
        plt.close(fig_before)


# ------------------------ gsidiag.plotting: caminho “core” ------------------------

def test_plotting_shim_prefers_readDiag_plotting_core(monkeypatch):
    # cria módulos sintéticos para o caminho que o shim usa: readDiag.plotting.core
    class DummyPlotter: pass

    fake_core = types.ModuleType("readDiag.plotting.core")
    fake_core.diagPlotter = DummyPlotter

    fake_pkg = types.ModuleType("readDiag.plotting")
    fake_pkg.core = fake_core  # expõe submódulo como atributo

    sys.modules["readDiag.plotting.core"] = fake_core
    sys.modules["readDiag.plotting"] = fake_pkg

    # Recarrega o shim para pegar os fakes
    sys.modules.pop("gsidiag.plotting", None)
    import gsidiag.plotting as gp
    importlib.reload(gp)

    assert hasattr(gp, "diagPlotter")
    assert gp.diagPlotter is DummyPlotter


# ------------------------ gsidiag.utils: caminho fallback puro ------------------------

def test_utils_fallback_only_path(monkeypatch):
    # remove o módulo real para forçar o 'except:' do shim
    sys.modules.pop("readDiag._utils", None)
    sys.modules.pop("gsidiag.utils", None)

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        u = importlib.import_module("gsidiag.utils")
        # fallback expõe 'deprecated' que só emite Warning e 'check_kind' que é Truthy / decorador
        u.deprecated("edge")
        assert any("edge" in str(w.message) for w in rec)

        ck = u.check_kind(1)
        # aceita True (fallback) ou decorador (variante de ambiente)
        assert (ck is True) or callable(ck)
