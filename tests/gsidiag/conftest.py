# tests/gsidiag/conftest.py
from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import textwrap
import numpy as np
import pandas as pd
import pytest

# =============================================================================
# 0) Dependências opcionais: stubs só se o pacote real não existe
# =============================================================================
def _install_readDiag_stubs() -> None:
    readDiag = types.ModuleType("readDiag")
    reader = types.ModuleType("readDiag.reader")
    schema = types.ModuleType("readDiag.schema")
    naming = types.ModuleType("readDiag.schema.naming")

    def _fake_diagAccess(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        # objeto mínimo só para smoke-tests do legado
        return {"dummy": True}

    def _fake_resolve_col_in_df(df: pd.DataFrame, *aliases: str, default: Optional[str] = None) -> Optional[str]:
        for k in aliases:
            if k in df.columns:
                return k
        return default

    reader.diagAccess = _fake_diagAccess
    naming.resolve_col_in_df = _fake_resolve_col_in_df
    schema.naming = naming
    readDiag.reader = reader
    readDiag.schema = schema

    sys.modules.setdefault("readDiag", readDiag)
    sys.modules.setdefault("readDiag.reader", reader)
    sys.modules.setdefault("readDiag.schema", schema)
    sys.modules.setdefault("readDiag.schema.naming", naming)

if importlib.util.find_spec("readDiag") is None:
    _install_readDiag_stubs()

# geopandas é opcional: stub se ausente
if importlib.util.find_spec("geopandas") is None:  # pragma: no cover
    gpd = types.ModuleType("geopandas")
    class GeoDataFrame(pd.DataFrame):  # stand-in mínimo
        __module__ = "geopandas"
    gpd.GeoDataFrame = GeoDataFrame
    sys.modules.setdefault("geopandas", gpd)

# Matplotlib em modo não interativo
import matplotlib
matplotlib.use("Agg", force=True)

# =============================================================================
# 1) FAKE backends (RAD / CONV) com estrutura rica
# =============================================================================
class _RadBackendTables:
    """
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

        # --- diagbuf_df (por observação, sem canal) --------------------------
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
        pred_cols = [f"pred{i}" for i in range(1, npred + 3)]  # +2 simulando reader
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
            inv = dfc["errinv"].replace(0.0, np.nan)
            dfc["end_err"] = 1.0 / inv
            dfc["oma"]     = np.nan
            # garantir dtypes float
            for c in dfc.columns:
                dfc[c] = dfc[c].astype(float)
            diagbufchan_df.append(dfc)

        # --- diagbufex_df (tabela extra) -------------------------------------
        diagbufex_df = pd.DataFrame({"extra1": np.zeros(n_obs, dtype=float)})

        # --- meta e store -----------------------------------------------------
        self._meta: Dict[str, Any] = {
            "file_name": self._path,
            "data_type": "rad",
            "date": self._date,
            "sensor": sensor,
            "platform": platform,
            "n_channels": n_channels,
            "n_obs": n_obs,
        }
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

    @property
    def meta(self) -> Dict[str, Any]:
        return self._meta

    @property
    def dataframes(self) -> Dict[str, Any]:
        return self._store["dataframes"]


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
                    arr[:, 19] = 0.1 if v != "wst" else 1.0  # spread/factw

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

    @property
    def meta(self) -> Dict[str, Any]:
        return self._meta

    @property
    def split_map(self) -> Dict[str, Dict[int, pd.DataFrame]]:
        """Retorna {var -> {kx -> DataFrame}}."""
        return self._data


# =============================================================================
# 2) Fixtures de alto nível p/ usar nos testes do legado
# =============================================================================
@pytest.fixture(scope="session")
def rad_backend() -> _RadBackendTables:
    return _RadBackendTables()

@pytest.fixture(scope="session")
def conv_backend() -> _ConvBackendTables:
    return _ConvBackendTables()

# atalhos convenientes (muito usados em smoke-tests)
@pytest.fixture(scope="session")
def rad_dataframes(rad_backend) -> Dict[str, Any]:
    return rad_backend.dataframes

@pytest.fixture(scope="session")
def conv_data_map(conv_backend) -> Dict[str, Dict[int, pd.DataFrame]]:
    return conv_backend.split_map
@pytest.fixture()
def minimal_yaml(tmp_path: Path) -> Path:
    """Create a minimal table.yml with one conventional and one satellite entry."""
    yaml_text = textwrap.dedent(
        """
        observations:
          - kx: "120"
            details:
              - var: ps
                abbreviation: ADPUPA
                instrument: Radiosonde
                color: "#1f77b4"
                symbol: s
                iuse: "1"
              - var: t
                abbreviation: ADPUPA
                instrument: Radiosonde
                color: "#B25809"
                symbol: "*"
                iuse: "1"

          - kx: n19
            details:
              - var: amsua
                abbreviation: AMSU-A NOAA-19
                instrument: ""     # empty to force fallback for instrument
                color: "#ff0000"
                symbol: x
                iuse: "1"
        """
    ).strip()
    p = tmp_path / "table.yml"
    p.write_text(yaml_text, encoding="utf-8")
    return p

