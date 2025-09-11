# -*- coding: utf-8 -*-
"""
Testes extras para o legado: ImpactAnalyzer.from_pair (conv/rad),
CLI com múltiplos arquivos e checagem de mensagem deprecada exata.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest


# -----------------------------------------------------------------------------
# ImpactAnalyzer.from_pair (conv e rad)  :contentReference[oaicite:0]{index=0}
# -----------------------------------------------------------------------------
def test_from_pair_conv_merges_oma_and_error(monkeypatch):
    import gsidiag.impact_legacy as imp

    class FakeConv:
        def __init__(self, var="t"):
            self._dtype = 1
            self.var = var
            # kx=120: omf + end_err
            self._data_frame = {
                var: {
                    120: pd.DataFrame(
                        {"omf": [1.0, -2.0, 0.5], "end_err": [2.0, 4.0, 2.0]}
                    )
                }
            }

        # API usada pelo ImpactAnalyzer
        def get_data_type(self):
            return self._dtype

        def get_data_frame(self):
            return self._data_frame

    # diagAccess “falso”: primeiro arquivo = OmF, segundo = OmA
    calls = dict(n=0)

    def fake_diag_access(_path, var=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeConv(var=var or "t")  # OmF
        return FakeConv(var=var or "t")      # OmA (com mesma estrutura; usaremos 'omf' como 'oma')

    monkeypatch.setattr(imp, "diagAccess", fake_diag_access)

    a = imp.ImpactAnalyzer.from_pair("omf.diag", "oma.diag", var="t")
    assert a.diag.get_data_type() == 1

    df = a.diag.get_data_frame()["t"][120]
    # deve ter colunas criadas
    assert "oma" in df.columns and "error" in df.columns
    # error = 1/end_err
    np.testing.assert_allclose(df["error"].to_numpy(), 1.0 / np.array([2.0, 4.0, 2.0]))


def test_from_pair_rad_merges_channels_and_error(monkeypatch):
    import gsidiag.impact_legacy as imp

    class FakeRad:
        def __init__(self):
            self._dtype = 2
            # Lista de canais, cada df com omf + errinv
            self._data_frame = {
                "dataframes": {
                    "diagbufchan_df": [
                        pd.DataFrame({"omf": [2.0, -1.0], "errinv": [4.0, 2.0]}),
                        pd.DataFrame({"omf": [0.2, 0.3], "errinv": [10.0, 5.0]}),
                    ]
                }
            }

        def get_data_type(self):
            return self._dtype

        def get_data_frame(self):
            return self._data_frame

    # O primeiro retorno do diagAccess será a lista OmF, o segundo a lista OmA
    rad_objs = [FakeRad(), FakeRad()]
    def fake_diag_access(_path, var=None):
        return rad_objs.pop(0)

    monkeypatch.setattr(imp, "diagAccess", fake_diag_access)

    a = imp.ImpactAnalyzer.from_pair("omf.rad", "oma.rad")
    frames = a.diag.get_data_frame()["dataframes"]["diagbufchan_df"]
    # Para cada canal, 'oma' e 'error' devem existir
    for df in frames:
        assert {"oma", "error"} <= set(df.columns)
        # error == 1/errinv (não-NaN)
        assert np.isfinite(df["error"]).all()


# -----------------------------------------------------------------------------
# CLI: múltiplos arquivos, sem --var (apenas pfileinfo)  :contentReference[oaicite:1]{index=1}
# -----------------------------------------------------------------------------
def test_cli_multiple_files_no_var(monkeypatch, capsys):
    import gsidiag.__main__ as cli_mod

    class FakeLegacyObj:
        def pfileinfo(self):
            print("Variable Name : t")
            print("              └── kx => 120 130")
        def summarize(self, *a, **k):
            # não será chamado, pois não passamos --var
            raise AssertionError("summarize() não deveria ser chamado sem --var")

    # CLI usa read_diag do próprio módulo
    monkeypatch.setattr(cli_mod, "read_diag", lambda files: FakeLegacyObj())
    monkeypatch.setattr(sys, "argv", ["gsidiag", "f1.diag", "f2.diag"])

    rc = cli_mod.cli()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Variable Name : t" in out
    assert "kx => 120 130" in out


# -----------------------------------------------------------------------------
# Deprecation exato no import de gsidiag  :contentReference[oaicite:2]{index=2}
# -----------------------------------------------------------------------------
def test_deprecation_message_exact_text(monkeypatch):
    # Garante recarregar o pacote para capturar o warn
    sys.modules.pop("gsidiag", None)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        import gsidiag  # noqa: F401
        msgs = [str(r.message) for r in rec]
        assert any(
            "You are importing the legacy package 'gsidiag'." in m for m in msgs
        ), f"Mensagem não encontrada nas warnings: {msgs}"

