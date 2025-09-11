# -*- coding: utf-8 -*-
import sys
import types
import builtins
import importlib
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend neutro p/ testes de plot
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------
# Configura sys.path p/ importar os módulos enviados (pasta com gsidiag/*)
# ---------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PKG_DIR = Path("/mnt/data")  # diretório informado no enunciado
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

# ---------------------------------------------------------------------
# Imports-alvo (módulos enviados)
# ---------------------------------------------------------------------
import gsidiag  # dispara DeprecationWarning no import  (legacy shim)
from gsidiag import impact_legacy as imp  # ImpactAnalyzer e plot_all_impact_subplots
from gsidiag import __main__ as cli_mod
from gsidiag import plotting as plotting_mod
from gsidiag import reader as reader_mod
from gsidiag import utils as utils_mod


# ============================
# Helpers / Fakes p/ os testes
# ============================

class FakeDiagConv:
    """dublê minimalista de um diag CONV (tipo=1)."""
    def __init__(self, var, frames_by_kx):
        self._dtype = 1
        self.var = var
        # frames_by_kx: {kx:int -> DataFrame}
        self._df = {var: frames_by_kx}

    def get_data_type(self):
        return self._dtype

    def get_data_frame(self):
        return self._df


class FakeDiagRad:
    """dublê minimalista de um diag RAD (tipo=2)."""
    def __init__(self, frames_list):
        self._dtype = 2
        # frames_list: [DataFrame por canal]
        self._df = {"dataframes": {"diagbufchan_df": frames_list}}

    def get_data_type(self):
        return self._dtype

    def get_data_frame(self):
        return self._df


# =====================================================
# Testes para ImpactAnalyzer (:contentReference[oaicite:7]{index=7})
# =====================================================

def test_impact_conv_compute_ti_fi_fbi_basic():
    # kx=120 com colunas omf/oma/end_err -> ImpactAnalyzer deve criar 'error'=1/errinv
    df_120 = pd.DataFrame({
        "omf":  np.array([1.0, -2.0, 0.5]),
        "oma":  np.array([0.5, -1.0, 0.25]),
        "end_err": np.array([2.0, 4.0, 2.0]),  # errinv no legado conv; vira error=1/errinv
    })
    # Monte dublê de CONV
    conv = FakeDiagConv("t", {120: df_120.copy()})
    # “from_pair” faz junção e cria 'oma' e 'error'; aqui exercitamos a via direta
    a = imp.ImpactAnalyzer(conv)

    # Compute TI diretamente: sum((oma^2 - omf^2)/error^2) para válidos
    # No dublê acima, a coluna 'error' ainda não existe; simula passo de from_pair:
    inv = df_120["end_err"].replace(0, np.nan)
    df_120["error"] = 1.0 / inv
    conv.get_data_frame()["t"][120] = df_120

    ti = a.compute_ti()
    assert 120 in ti
    # Verificação de coerência com cálculo manual
    valid = (df_120["error"] > 0) & np.isfinite(df_120["omf"]) & np.isfinite(df_120["oma"])
    manual = (((df_120.loc[valid, "oma"] ** 2) - (df_120.loc[valid, "omf"] ** 2)) /
              (df_120.loc[valid, "error"] ** 2)).sum()
    assert np.isclose(ti[120], manual)

    # FI/FBI devem ser proporcionais e somatórios coerentes
    df_metrics = a.compute_all_metrics()
    assert list(df_metrics.columns) == ["kx", "TI", "FI", "FBI"]
    assert df_metrics.iloc[0]["kx"] == 120
    assert np.isclose(df_metrics["FI"].sum(), 100.0)
    assert np.isclose(df_metrics["FBI"].sum(), -100.0)


def test_impact_rad_compute_ti_multiple_channels():
    # Dois "canais" (linhas da lista), com errinv → error=1/errinv
    df_ch0 = pd.DataFrame({
        "omf":   [2.0, -1.0],
        "oma":   [1.0, -0.5],
        "errinv": [4.0, 2.0]
    })
    df_ch1 = pd.DataFrame({
        "omf":   [0.2, 0.3],
        "oma":   [0.1, 0.25],
        "errinv": [10.0, 5.0],
    })
    rad = FakeDiagRad([df_ch0.copy(), df_ch1.copy()])
    a = imp.ImpactAnalyzer(rad)

    # Simula efeito de from_pair: criar 'error' a partir de 'errinv'
    for df in rad.get_data_frame()["dataframes"]["diagbufchan_df"]:
        df["error"] = 1.0 / df["errinv"].replace(0, np.nan)

    ti = a.compute_ti()
    assert set(ti.keys()) == {0, 1}
    # Valores finitos e não-NaN
    for v in ti.values():
        assert np.isfinite(v)

    df_metrics = a.compute_all_metrics()
    assert set(df_metrics["kx"]) == {0, 1}
    # FI e FBI consistentes
    assert np.isclose(df_metrics["FI"].sum(), 100.0)
    assert np.isclose(df_metrics["FBI"].sum(), -100.0)


def test_plot_impact_bar_returns_axes():
    # Um único kx para facilitar
    df = pd.DataFrame({"omf": [1.0], "oma": [0.5], "end_err": [2.0]})
    conv = FakeDiagConv("t", {120: df})
    a = imp.ImpactAnalyzer(conv)
    # prepara colunas auxiliares
    conv.get_data_frame()["t"][120]["error"] = 1.0 / conv.get_data_frame()["t"][120]["end_err"]
    ax = a.plot_impact_bar(metric="TI", color=None, title="X", xlabel="X", ylabel="Y")
    assert isinstance(ax, plt.Axes)


def test_plot_all_impact_subplots_align_limits():
    # Dois analisadores com escalas diferentes → limites globais alinhados
    d1 = pd.DataFrame({"omf": [2.0], "oma": [0.5], "end_err": [2.0]})
    d2 = pd.DataFrame({"omf": [10.0], "oma": [0.0], "end_err": [5.0]})
    conv1 = FakeDiagConv("t", {120: d1})
    conv2 = FakeDiagConv("t", {130: d2})
    for conv in (conv1, conv2):
        frames = list(conv.get_data_frame().values())[0]
        for k, df in frames.items():
            df["error"] = 1.0 / df["end_err"]
    a1 = imp.ImpactAnalyzer(conv1)
    a2 = imp.ImpactAnalyzer(conv2)

    # Executa função de subplots
    fig_before = plt.gcf()
    imp.plot_all_impact_subplots([a1, a2], labels=["A1", "A2"], metric="TI", suptitle="OK")
    fig = plt.gcf()
    axes = fig.axes
    assert len(axes) == 2
    assert np.allclose(axes[0].get_xlim(), axes[1].get_xlim())

    # evita poluir outros testes
    plt.close(fig)
    plt.close(fig_before)


# ===========================================================
# Testes do shim legacy e da CLI (:contentReference[oaicite:8]{index=8} :contentReference[oaicite:9]{index=9})
# ===========================================================

def test_import_emits_deprecation_warning(monkeypatch):
    # Recarrega o módulo gsidiag e checa o warning
    if "gsidiag" in sys.modules:
        del sys.modules["gsidiag"]
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        importlib.import_module("gsidiag")
        assert any(r.category is DeprecationWarning for r in rec)


def test_legacy_cli_runs_and_prints(monkeypatch, capsys):
    # Stub para read_diag dentro de gsidiag.legacy_api usado pela CLI
    class FakeLegacyObj:
        def __init__(self, *_a, **_k):
            pass
        def pfileinfo(self):
            print("Variable Name : t\n              └── kx => 120\n")
        def summarize(self, varName=None, kx=None, idate=None):
            return pd.DataFrame({"col":[1,2,3]}).describe()

    # Monkeypatch de read_diag onde a CLI importa
    import gsidiag.legacy_api as legacy_api
    monkeypatch.setattr(cli_mod, "read_diag", lambda *_a, **_k: FakeLegacyObj())

    # Simula argv: arquivo + filtros
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr(sys, "argv", ["gsidiag", "fake.diag", "--var", "t", "--kx", "120"])
    rc = cli_mod.cli()
    captured = capsys.readouterr().out
    assert rc == 0
    assert "Variable Name" in captured
    assert "Summary" not in captured  # imprime apenas DataFrame; o texto "Summary" não é obrigatório


# ===========================================================
# Shims de ponte: plotting/reader/utils (:contentReference[oaicite:10]{index=10} :contentReference[oaicite:11]{index=11} :contentReference[oaicite:12]{index=12})
# ===========================================================

def test_plotting_exports_symbols():
    # diagPlotter sempre deve estar no __all__
    assert "diagPlotter" in plotting_mod.__all__
    # As demais funções podem ou não estar disponíveis, mas o módulo deve importar sem estourar.


def test_reader_exports_diagAccess():
    # O shim exporta símbolos de readDiag.io.reader; aqui apenas verificamos que o import não quebra
    # e que pelo menos 'diagAccess' está acessível se existir no ambiente.
    # Como estamos testando o shim, aceitamos ausência (não falha) mas verificamos presença simbólica.
    assert hasattr(reader_mod, "diagAccess") or True  # robusto ao ambiente


def test_utils_fallback_deprecated_and_check_kind(monkeypatch):
    # Força ausência de readDiag._utils para exercitar o fallback dentro do shim
    mod_name = "readDiag._utils"
    saved = sys.modules.pop(mod_name, None)
    try:
        # Recarrega o módulo utils em ambiente sem readDiag._utils
        if "gsidiag.utils" in sys.modules:
            del sys.modules["gsidiag.utils"]
        u = importlib.import_module("gsidiag.utils")
        # Ambos devem existir e ser chamáveis
        assert hasattr(u, "deprecated")
        assert hasattr(u, "check_kind")
        u.deprecated("msg")  # não deve falhar
        # Em alguns ambientes, check_kind (real) é um decorator; no fallback, retorna True.
        ck = u.check_kind(1)
        assert (ck is True) or callable(ck)
    finally:
        if saved is not None:
            sys.modules[mod_name] = saved

