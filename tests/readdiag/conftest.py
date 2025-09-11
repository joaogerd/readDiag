# conftest.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import pytest

# =========================
# FAKE backends (RAD / CONV)
# =========================
class _RadBackendTables:
    """
    Fake backend p/ **radiance** com superfície igual ao reader público:
    - get_file_info()
    - get_channels()
    - get_data_frame()
    - get_table(name)

    dataframes = {
      "channel_df":      (n_channels, ...),
      "diagbuf_df":      (n_obs, ...),
      "diagbufchan_df":  list de len n_channels, cada DF (n_obs, ...),
      "diagbufex_df":    (n_obs, ...)
    }
    """
    def __init__(
        self,
        path: str = "diag_amsua_n15_03.2025010106",
        *,
        sensor: str = "amsua",
        platform: str = "n15",
        n_channels: int = 3,
        n_obs: int = 8,
        npred: int = 2,
        date: Optional[datetime] = None,
        **_: Any,
    ) -> None:
        self._path = path
        self._date = date or datetime(2025, 1, 1, 6)

        # --- channel_df -------------------------------------------------------
        ich = np.arange(1, n_channels + 1, dtype=int)
        channel_df = pd.DataFrame(
            {
                "freq":   np.linspace(23.8, 57.6, n_channels, dtype=float),
                "pol":    np.zeros(n_channels, dtype=float),
                "wave":   np.linspace(1.0, 3.0, n_channels, dtype=float),
                "varch":  np.linspace(0.1, 0.3, n_channels, dtype=float),
                "tlap":   np.linspace(0.0, 1.0, n_channels, dtype=float),
                "iuse":   np.ones(n_channels, dtype=int),
                "nuchan": ich,
                "ich":    ich,
            }
        )

        # --- diagbuf_df (header / por-observação, sem canal) -----------------
        header_cols = [
            "lat","lon","elev","time","iscanp","zasat","ilazi","pangs","isazi","sgagl",
            "sfcwc","sfclc","sfcic","sfcsc","sfcwt","sfclt","sfcit","sfcst","sfcstp",
            "sfcsmc","sfcltp","sfcvf","sfcsd","sfcws","clsORclw","cldpORtpwc",
        ]
        diagbuf_df = pd.DataFrame(
            np.zeros((n_obs, len(header_cols)), dtype=float),
            columns=header_cols,
        )
        diagbuf_df["lat"]  = np.linspace(-30.0, 30.0, n_obs, dtype=float)
        diagbuf_df["lon"]  = np.linspace(-60.0, -40.0, n_obs, dtype=float)
        diagbuf_df["time"] = np.linspace(0.0, 1.0,   n_obs, dtype=float)

        # --- diagbufchan_df (por canal) --------------------------------------
        ch_head   = ["tb_obs","omf","omf_nbc","errinv","idqc","emiss","tlach","ts"]
        pred_cols = [f"pred{i}" for i in range(1, npred + 3)]  # +2 p/ simular reader
        cols      = ["ch"] + ch_head + pred_cols + ["spread", "end_err", "oma"]

        diagbufchan_df: List[pd.DataFrame] = []
        for ch in range(1, n_channels + 1):
            dfc = pd.DataFrame(index=range(n_obs), columns=cols, dtype=float)
            dfc["ch"]      = float(ch)
            dfc["tb_obs"]  = 200.0 + ch + np.linspace(-2.0, 2.0, n_obs, dtype=float)
            dfc["omf"]     = np.linspace(-1.0, 1.0, n_obs, dtype=float)
            dfc["omf_nbc"] = dfc["omf"] * 0.8
            dfc["errinv"]  = 0.5 + 0.01 * ch       # > 0 para evitar div/0
            dfc["idqc"]    = 0.0
            dfc["emiss"]   = 0.9
            dfc["tlach"]   = 0.0
            dfc["ts"]      = 290.0
            for c in pred_cols:
                dfc[c] = 0.0
            dfc["spread"]  = 0.1
            # evitar divisão por zero com replace(0, NaN) (aqui errinv > 0)
            inv = dfc["errinv"].replace(0.0, np.nan)
            dfc["end_err"] = 1.0 / inv
            dfc["oma"]     = np.nan
            # garantir dtypes float
            for c in dfc.columns:
                dfc[c] = dfc[c].astype(float)
            diagbufchan_df.append(dfc)

        # --- diagbufex_df (qualquer tabela extra por-obs) --------------------
        diagbufex_df = pd.DataFrame({"extra1": np.zeros(n_obs, dtype=float)})

        # --- store e meta -----------------------------------------------------
        self._store: Dict[str, Any] = {
            "sensor": sensor,
            "platform": platform,
            "dataframes": {
                "channel_df":     channel_df,
                "diagbuf_df":     diagbuf_df,
                "diagbufchan_df": diagbufchan_df,
                "diagbufex_df":   diagbufex_df,
            },
        }
        self._meta: Dict[str, Any] = {
            "file_name":   self._path,
            "data_type":   "rad",
            "date":        self._date,
            "sensor":      sensor,
            "platform":    platform,
            "n_channels":  int(channel_df.shape[0]),
            "n_obs":       int(diagbuf_df.shape[0]),
        }
        self._channels: List[int] = list(ich.tolist())

    # ------- API pública simulada --------------------------------------------
    def get_file_info(self) -> Dict[str, Any]:
        return dict(self._meta)

    def get_channels(self) -> List[int]:
        return list(self._channels)

    def get_dataframe(self) -> Dict[str, Any]:
        """Retorna o 'store' com as tabelas."""
        return self._store

    def get_table(self, name: str) -> Any:
        """Acessa uma das tabelas por nome."""
        dfs = self._store["dataframes"]
        if name == "diagbufchan_df":
            return dfs["diagbufchan_df"]  # lista de DFs (len = n_channels)
        if name in dfs:
            return dfs[name]
        raise KeyError(f"Tabela desconhecida: {name!r}")


class _ConvBackendTables:
    """
    Fake backend p/ **convencional** no formato split:
    {var -> {kx -> DataFrame}} com colunas base-20 (e variações de 'uv' e 'wst').
    """
    def __init__(
        self,
        path: str = "diag_conv_01.2025010106",
        *,
        vars: Sequence[str] = ("t", "q", "ps", "uv", "wst"),
        kx_list: Sequence[int] = (120, 130, 131),
        n_obs_per_kx: int = 6,
        add_qc_flag_alias: bool = True,
        date: Optional[datetime] = None,
        **_: Any,
    ) -> None:
        self._path = path
        self._date = date or datetime(2025, 1, 1, 6)
        self._vars = list(vars)
        self._kx = list(kx_list)
        self._n = int(n_obs_per_kx)

        base20 = [
            "kx","ksub","lat","lon","elev","prs","hgt","time","iqc",
            "qc_setup","iuse","analysis_use","rwgt",
            "errinv_inp","errinv_adj","errinv_fin",
            "obs","omf","omf_wob","spread",
        ]

        def make_cols(var: str) -> List[str]:
            if var == "uv":
                tail = ["obs_u","omf_u","omf_wob_u","obs_v","omf_v","omf_wob_v"]
                return base20[:16] + tail
            if var == "wst":
                cols = base20.copy()
                cols[-1] = "factw"
                return cols
            return base20

        self._data: Dict[str, Dict[int, pd.DataFrame]] = {}
        rng = np.random.default_rng(42)
        for v in self._vars:
            cols = make_cols(v)
            v_map: Dict[int, pd.DataFrame] = {}
            for kx in self._kx:
                m = self._n
                arr = np.zeros((m, len(cols)), dtype=float)
                arr[:, 0] = kx         # kx
                arr[:, 1] = 1          # ksub
                arr[:, 2] = np.linspace(-20, 20, m)
                arr[:, 3] = np.linspace(-60, -50, m)
                arr[:, 4] = 500.0
                arr[:, 5] = rng.normal(700.0, 50.0, m)  # prs
                arr[:, 6] = rng.normal(100.0, 10.0, m)  # hgt
                arr[:, 7] = np.linspace(0, 1, m)        # time
                arr[:, 8] = 0.0                         # iqc
                arr[:, 9]  = 0.0                        # qc_setup
                arr[:, 10] = 1.0                        # iuse
                arr[:, 11] = 1.0                        # analysis_use
                arr[:, 12] = 1.0                        # rwgt
                # errinv*
                arr[:, 13] = 0.02
                arr[:, 14] = 0.03
                arr[:, 15] = 0.04

                if v != "uv":
                    arr[:, 16] = rng.normal(0.0, 1.0, m)   # obs
                    arr[:, 17] = rng.normal(0.0, 0.5, m)   # omf
                    arr[:, 18] = arr[:, 17] * 0.9          # omf_wob
                    # spread/factw:
                    arr[:, 19] = 0.1 if v != "wst" else 1.0

                df = pd.DataFrame(arr, columns=cols)
                if add_qc_flag_alias and "iqc" in df.columns and "qc_flag" not in df.columns:
                    df["qc_flag"] = df["iqc"]

                v_map[int(kx)] = df.reset_index(drop=True)
            self._data[v] = v_map

        self._meta: Dict[str, Any] = {
            "file_name": self._path,
            "data_type": "conv",
            "date": self._date,
            "n_vars": len(self._vars),
            "vars": tuple(self._vars),
            "kx_all": tuple(self._kx),
            "n_obs_total": len(self._vars) * len(self._kx) * self._n,
        }

    def get_file_info(self) -> Dict[str, Any]:
        return dict(self._meta)

    def get_variables(self) -> List[str]:
        return list(self._vars)

    def get_kx_list(self, var: str) -> List[int]:
        if var not in self._data:
            raise ValueError(f"Variable '{var}' not found.")
        return sorted(self._data[var].keys())

    def get_dataframe(self, var: str, kx: int) -> Dict[str, Dict[int, pd.DataFrame]]:
        return self._data[var][kx]

    def get_table(self, var: str, kx: int) -> pd.DataFrame:
        if var not in self._data or kx not in self._data[var]:
            raise KeyError(f"Table for var={var!r} kx={kx!r} not found")
        return self._data[var][kx]


# =========================
# FIXTURES
# =========================

@pytest.fixture
def rad_backend_fake() -> _RadBackendTables:
    """Instância pronta do backend de radiância fake."""
    return _RadBackendTables()

@pytest.fixture
def conv_backend_fake() -> _ConvBackendTables:
    """Instância pronta do backend convencional fake (split por kx)."""
    return _ConvBackendTables()

@pytest.fixture
def patch_readers(monkeypatch, rad_backend_fake, conv_backend_fake):
    """
    Monkeys que substituem os readers reais por versões em memória.

    - readDiag.rad_reader.read_radiance(path, use_memmap=True)
      deve retornar (idate, data_frame) como no facade.  # reader usa isso
    - readDiag.conv_reader.read_conv_file(file, ..., set_date_cb=cb)
      deve retornar {var -> {kx -> DF}} e invocar set_date_cb(date).  # idem
    """
    # patch radiance
    def _fake_read_radiance(path: str | bytes, use_memmap: bool = True):
        b = rad_backend_fake
        return (b.get_file_info()["date"], b.get_dataframe())

    monkeypatch.setattr("readDiag.rad_reader.read_radiance", _fake_read_radiance, raising=True)

    # patch conventional
    def _fake_read_conv_file(
        file_name: str,
        *,
        var: Optional[str] = None,
        fast: bool = True,
        base20_only: bool = True,
        read_sids: bool = False,
        compat_legacy: bool = True,
        raw_numpy: bool = False,
        compact: bool = False,
        set_date_cb = None,
    ):
        b = conv_backend_fake
        if set_date_cb is not None:
            try:
                set_date_cb(b.get_file_info()["date"])
            except Exception:
                pass
        data = b.get_dataframe()
        if var is not None:
            data = {var: data[var]}
        # ignoramos flags (fast/base20_only/compact/raw_numpy) no fake
        return data

    monkeypatch.setattr("readDiag.conv_reader.read_conv_file", _fake_read_conv_file, raising=True)

    return {"rad": rad_backend_fake, "conv": conv_backend_fake}


# Helpers convenientes para testes de alto nível com o facade
@pytest.fixture
def diagAccess_patched(patch_readers):
    """
    Factory que retorna uma função para construir diagAccess já com
    os readers fakes ativos.
    """
    from readDiag.reader import diagAccess  # importa após patch
    def _factory(path: str, **kwargs):
        return diagAccess(path, **kwargs)
    return _factory

