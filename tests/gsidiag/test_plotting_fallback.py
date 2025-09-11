# -*- coding: utf-8 -*-
import sys
import types
import importlib

def test_plotting_shim_fallback_when_wrappers_missing(monkeypatch):
    # Cria um módulo core válido para o import obrigatório
    fake_core = types.ModuleType("readDiag.plotting.core")
    class DummyPlotter: pass
    fake_core.diagPlotter = DummyPlotter

    # Injeta um "wrappers" sem os símbolos esperados para disparar ImportError no "from ... import ..."
    fake_wrappers = types.ModuleType("readDiag.plotting.wrappers")
    # (não define plot_kx_count etc.)

    sys.modules["readDiag.plotting.core"] = fake_core
    sys.modules["readDiag.plotting.wrappers"] = fake_wrappers

    # Força recarregar o shim
    sys.modules.pop("gsidiag.plotting", None)
    import gsidiag.plotting as gp
    importlib.reload(gp)

    # No fallback, só diagPlotter é exportado pelo shim
    assert gp.diagPlotter is DummyPlotter
    assert gp.__all__ == ["diagPlotter"]

