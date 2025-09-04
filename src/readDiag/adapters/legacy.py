"""Compatibility layer for legacy GSI diagnostic readers.

This module provides :class:`LegacyCompatAdapter`, an adapter that wraps
older/irregular backends and exposes the modern :class:`~surface.DiagnosticAPI`
interface expected by *readDiag*.

Design goals
------------
- **Best-effort tolerance** to partially implemented legacy methods.
- **Stable surface**: keep public methods aligned with ``DiagnosticAPI``.
- **Zero-copy mindset**: avoid unnecessary DataFrame copies.
- **Kind-guarding**: use :func:`~utils.check_kind` to enforce API contracts.

Examples
--------
Minimal *conventional* backend:

>>> class LegacyConv:
...     file_name = "diag_conv_01.2020010100"
...     def get_variables(self): return ["t", "q"]
...     def get_kx_list(self, var): return [120, 130] if var in ("t", "q") else []
...     def get_dataframe(self, var, kx):
...         import pandas as pd
...         return pd.DataFrame({"var":[var], "kx":[kx]})
...
>>> # api = LegacyCompatAdapter(LegacyConv())
>>> # api.kind(), api.variables()
... # ('conv', ['t', 'q'])

Minimal *radiance* backend:

>>> class LegacyRad:
...     file_name = "diag_amsua_n15_03.2024013018"
...     sensor = "amsua"; platform = "n15"
...     def get_channels(self): return [1, 2, 3]
...     from datetime import datetime
...     def get_date(self): return datetime(2024, 1, 30, 18)
...     def get_data_frame(self):
...         import pandas as pd
...         return {"dataframes": {
...             "channel_df":   pd.DataFrame({"ch":[1,2,3]}),
...             "diagbuf_df":   pd.DataFrame({"x":[1,2,3]}),
...             "diagbufex_df": pd.DataFrame({"y":[4,5,6]}),
...             "diagbufchan_df": [pd.DataFrame({"v":[1]}),
...                               pd.DataFrame({"v":[2]}),
...                               pd.DataFrame({"v":[3]})],
...         }}
...
>>> # api = LegacyCompatAdapter(LegacyRad())
>>> # api.kind(), api.channels()
... # ('rad', [1, 2, 3])
>>> # ch1 = api.frame_channel(1)
>>> # isinstance(ch1, pd.DataFrame)
... # True
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import pandas as pd

from ..surface import DiagnosticAPI, Metadata, Kind
from ..utils import check_kind, guess_cycle_token

__all__ = ["LegacyCompatAdapter"]


class LegacyCompatAdapter(DiagnosticAPI):
    """Adapt legacy-like backends (incl. test fakes) to :class:`DiagnosticAPI`.

    The adapter is **best-effort**: it interprets a variety of legacy reader
    shapes without assuming strict availability of modern methods or metadata.
    It preserves *some* legacy shims while exposing the new stable surface.

    Key behaviors
    -------------
    - Does **not** assume presence of ``file_name`` or ``get_file_info()``.
    - Infers ``kind`` from ``get_data_type()`` (``1=conv``, ``2=rad``) when
      available, or from existence of ``get_channels`` as a fallback.
    - Builds :class:`Metadata` using available hints (sensor/platform, etc.).
    - For radiance, attempts to infer ``n_channels`` and ``n_obs`` from tables.
    - Normalizes ``"diagbufchan_df"`` to a mapping ``{index: DataFrame}``
      when returned via :meth:`table`, to comply with :class:`DiagnosticAPI`.

    Notes
    -----
    The goal is to *consume* older backends during a transition period. Prefer
    the modern :class:`AccessAdapter` whenever possible.

    Error semantics mirror the modern surface where possible
    (``ValueError`` for kind-mismatched calls, ``KeyError`` for unknown keys).
    """

    def __init__(self, backend: Any) -> None:
        """Initialize the adapter from a legacy-like backend.

        Parameters
        ----------
        backend : Any
            Object exposing some combination of legacy methods such as
            ``get_data_type()``, ``get_variables()``, ``get_kx_list()``,
            ``get_dataframe()``, ``get_channels()``, or a legacy
            ``get_data_frame()`` structure.

        Notes
        -----
        - ``kind`` is inferred from ``get_data_type()`` when present; otherwise
          from the existence of ``get_channels``.
        - ``date`` falls back to :func:`datetime.now` if no accessor exists.
        - ``n_channels`` and ``n_obs`` are inferred where possible (radiance).
        """
        self._b = backend

        # --- 1) Infer kind (conv|rad) -----------------------------------
        if hasattr(backend, "get_data_type"):
            dt = backend.get_data_type()
            kind: Kind = "rad" if dt == 2 else "conv"
        else:
            kind = "rad" if hasattr(backend, "get_channels") else "conv"

        # --- 2) Ensure _data_type on backend (used by some legacy code) ---
        if not hasattr(backend, "_data_type"):
            try:
                setattr(backend, "_data_type", 2 if kind == "rad" else 1)
            except Exception:
                # Backend may be a simple proxy or frozen object; ignore.
                pass

        # --- 3) Best-effort metadata ------------------------------------
        file_name = getattr(backend, "file_name", "unknown")
        if callable(getattr(backend, "get_date", None)):
            try:
                date = backend.get_date()
            except Exception:
                date = guess_cycle_token(file_name) or datetime.now()
        else:
            date = guess_cycle_token(file_name) or datetime.now()

        sensor = getattr(backend, "sensor", None)
        platform = getattr(backend, "platform", None)

        # --- 4) Radiance counts without adapter methods ------------------
        n_channels = None
        n_obs = None
        if kind == "rad":
            # Try direct backend accessor
            if callable(getattr(backend, "get_channels", None)):
                try:
                    n_channels = len(list(backend.get_channels()))
                except Exception:
                    pass
            # Try legacy store shape {"dataframes": {...}}
            if callable(getattr(backend, "get_data_frame", None)):
                try:
                    store = backend.get_data_frame()
                    if isinstance(store, dict) and "dataframes" in store:
                        dfs = store["dataframes"]
                        if isinstance(dfs, dict):
                            if "diagbuf_df" in dfs:
                                try:
                                    n_obs = len(dfs["diagbuf_df"])
                                except Exception:
                                    n_obs = None
                            elif "diagbufchan_df" in dfs:
                                seq = dfs["diagbufchan_df"]
                                try:
                                    n_obs = sum(len(df) for df in seq if df is not None)
                                except Exception:
                                    n_obs = None
                except Exception:
                    pass

        self._meta = Metadata(
            file_name=str(file_name),
            date=date,
            kind=kind,
            sensor=str(sensor) if sensor is not None else None,
            platform=str(platform) if platform is not None else None,
            n_channels=n_channels,
            n_obs=n_obs,
        )

    # ------------------------------------------------------------------
    # New stable surface
    # ------------------------------------------------------------------
    def meta(self) -> Metadata:
        """Return immutable file-level metadata.

        Returns
        -------
        Metadata
            File name, timestamp, kind and optional instrument/platform/counts.
        """
        return self._meta

    def kind(self) -> Kind:
        """Return the dataset kind.

        Returns
        -------
        {"conv", "rad"}
            Dataset category inferred at construction time.
        """
        return self._meta.kind

    # ---- Conventional API ---------------------------------------------
    @check_kind("conv")
    def variables(self) -> list[str]:
        """List available conventional variables.

        Returns
        -------
        list of str
            Variable names if discoverable; otherwise ``[]``.

        Notes
        -----
        - If the backend exposes ``get_variables()``, it is used directly.
        - Otherwise, the method derives variable names from the legacy
          mapping returned by :meth:`get_data_frame` when *not* a radiance
          structure (i.e., there is no top-level ``"dataframes"`` key).
        """
        # Preferred path: modern/legacy accessor
        if hasattr(self._b, "get_variables"):
            try:
                return list(self._b.get_variables())
            except Exception:
                pass
        # Robust fallback: infer from backend legacy mapping
        if hasattr(self._b, "get_data_frame"):
            try:
                data = self._b.get_data_frame()
                if isinstance(data, dict) and "dataframes" not in data:
                    return list(data.keys())
            except Exception:
                pass
        return []

    @check_kind("conv")
    def kx_list(self, var: str) -> list[int]:
        """List WMO platform codes (``kx``) for a given variable.

        Parameters
        ----------
        var : str
            Conventional variable name.

        Returns
        -------
        list of int
            Integer kx codes if discoverable; otherwise ``[]``.

        Notes
        -----
        Prefers backend's ``get_kx_list`` when available, falling back to keys
        of the inner legacy mapping ``{var: {kx: DataFrame}}``.
        """
        if hasattr(self._b, "get_kx_list"):
            try:
                return [int(k) for k in self._b.get_kx_list(var)]
            except Exception:
                pass
        if hasattr(self._b, "get_data_frame"):
            try:
                data = self._b.get_data_frame()
                inner = data.get(var, {}) if isinstance(data, dict) else {}
                return [int(k) for k in getattr(inner, "keys", lambda: [])()]
            except Exception:
                pass
        return []

    @check_kind("conv")
    def frame_conv(self, var: str, kx: int) -> pd.DataFrame:
        """Return a conventional (var, kx) slice as a DataFrame.

        Parameters
        ----------
        var : str
            Conventional variable name.
        kx : int
            WMO platform code.

        Returns
        -------
        pandas.DataFrame
            Slice DataFrame from the legacy backend.

        Raises
        ------
        KeyError
            If the legacy backend does not expose an appropriate accessor
            or if the pair ``(var, kx)`` is not present in the legacy map.
        """
        # 1) Preferred path: direct accessor on backend
        if hasattr(self._b, "get_dataframe"):
            try:
                return self._b.get_dataframe(var, kx)
            except Exception:
                pass

        # 2) Fallback: legacy dictionary ``{var: {kx: DataFrame}}``
        if hasattr(self._b, "get_data_frame"):
            try:
                data = self._b.get_data_frame()
                if isinstance(data, dict) and "dataframes" not in data:
                    return data[var][kx]
            except Exception:
                pass

        raise KeyError(f"frame_conv: invalid pair var={var!r}, kx={kx!r}")

    # ---- Radiance API --------------------------------------------------
    @check_kind("rad")
    def channels(self) -> list[int]:
        """List available **1-based** radiance channel indices.

        Returns
        -------
        list of int
            Channel indices if discoverable; otherwise inferred from the
            length of the legacy per-channel list.

        Notes
        -----
        Values are coerced to ``int`` for consistency.
        """
        if hasattr(self._b, "get_channels"):
            return [int(i) for i in self._b.get_channels()]
        if hasattr(self._b, "get_data_frame"):
            data = self._b.get_data_frame()
            store = data.get("dataframes", {}).get("diagbufchan_df", [])
            # Legacy list is typically 0-based; external contract is 1-based.
            return list(range(1, len(store) + 1))
        return []

    @check_kind("rad")
    def frame_channel(self, ch_index: int) -> pd.DataFrame:
        """Return the per-channel DataFrame for a radiance dataset.

        Parameters
        ----------
        ch_index : int
            **1-based** channel index.

        Returns
        -------
        pandas.DataFrame
            Per-channel frame from the legacy structure.

        Raises
        ------
        KeyError
            If the channel index is unknown/out of range or the backend lacks
            the expected legacy structure.
        """
        if hasattr(self._b, "get_data_frame"):
            data = self._b.get_data_frame()
            store = data.get("dataframes", {}).get("diagbufchan_df", [])
            i0 = ch_index - 1  # 1-based -> 0-based
            if not (0 <= i0 < len(store)):
                raise KeyError(f"Unknown channel index: {ch_index}")
            return store[i0]
        raise KeyError("diagbufchan_df not available in legacy backend.")

    @check_kind("rad")
    def table(self, name: str) -> pd.DataFrame | dict[int, pd.DataFrame]:
        """Access named radiance tables via stable identifiers.

        Parameters
        ----------
        name : {"channel_df", "diagbuf_df", "diagbufex_df", "diagbufchan_df"}
            Target table name.

        Returns
        -------
        pandas.DataFrame or dict of (int -> pandas.DataFrame)
            A single DataFrame for the first three names, or a dictionary
            of per-channel DataFrames for ``"diagbufchan_df"`` (1-based keys).

        Raises
        ------
        KeyError
            If the name is unknown or the legacy structure is missing.
        """
        if hasattr(self._b, "get_data_frame"):
            data = self._b.get_data_frame()
            dfs = data.get("dataframes", {})
            if name not in dfs:
                raise KeyError(f"Unknown table '{name}'")

            if name == "diagbufchan_df":
                # Legacy is a list[DataFrame]; normalize to {1-based index: DF}
                lst = dfs[name]
                return {i + 1: df for i, df in enumerate(lst)}

            # Pass-through for DataFrame tables
            return dfs[name]
        raise KeyError(f"Unknown table '{name}'")

    # ------------------------------------------------------------------
    # Legacy shims (transition)
    # ------------------------------------------------------------------
    def get_data_type(self) -> int:
        """Legacy: return ``1`` for conventional, ``2`` for radiance.

        Returns
        -------
        int
            ``1`` for ``"conv"`` and ``2`` for ``"rad"``.
        """
        return 2 if self.kind() == "rad" else 1

    def get_variables(self) -> list[str]:
        """Legacy alias for :meth:`variables`."""
        return self.variables()

    def get_kx_list(self, var: str) -> list[int]:
        """Legacy alias for :meth:`kx_list`."""
        return self.kx_list(var)

    def get_channels(self) -> list[int]:
        """Legacy alias for :meth:`channels`."""
        return self.channels()

    def get_dataframe(self, var: str, kx: int) -> pd.DataFrame:
        """Legacy alias mirroring ``get_dataframe(var, kx)``."""
        return self.frame_conv(var, kx)

    def get_data_frame(self) -> dict[str, Any]:
        """Recreate the **legacy** structure used by older callers.

        For conventional
        ~~~~~~~~~~~~~~~~
        ``{var -> {kx -> DataFrame}}``

        For radiance
        ~~~~~~~~~~~~
        ``{"dataframes": {``

        - ``"channel_df"``: ``DataFrame`` *(if available)*
        - ``"diagbuf_df"``: ``DataFrame`` *(if available)*
        - ``"diagbufex_df"``: ``DataFrame`` *(if available)*
        - ``"diagbufchan_df"``: ``list[DataFrame]``  # per channel

        ``}}``

        Returns
        -------
        dict
            Mapping compatible with legacy expectations.

        Notes
        -----
        Exists solely for backwards compatibility. Prefer the new API.
        """
        if self.kind() == "conv":
            out: Dict[str, Dict[int, pd.DataFrame]] = {}
            for var in self.variables():
                inner: Dict[int, pd.DataFrame] = {}
                for kx in self.kx_list(var):
                    inner[kx] = self.frame_conv(var, kx)
                out[var] = inner
            return out

        # Radiance legacy: preserve list-of-frames for channels
        # Avoid recursion—do not call adapter methods here.
        if callable(getattr(self._b, "get_data_frame", None)):
            try:
                store = self._b.get_data_frame()
            except Exception:
                store = {"dataframes": {}}
            dfs = dict(store.get("dataframes", {}))
            ch = dfs.get("diagbufchan_df")
            # Ensure diagbufchan_df is a list (legacy expects list)
            if isinstance(ch, dict):
                # Order by numeric key whenever possible
                try:
                    keys = sorted(ch.keys())
                except Exception:
                    keys = list(ch.keys())
                dfs["diagbufchan_df"] = [ch[k] for k in keys]
            elif ch is None:
                dfs["diagbufchan_df"] = []
            return {"dataframes": dfs}

        # Absolute fallback (rare): shape-minimal store
        return {"dataframes": {"diagbufchan_df": []}}

    def get_file_info(self) -> dict:
        """Legacy file info mapping compatible with older code.

        Returns
        -------
        dict
            Keys: ``file_name``, ``data_type``, ``date``, ``sensor``,
            ``platform``, ``n_channels``, ``n_obs``.
        """
        m = self._meta
        return {
            "file_name": m.file_name,
            "data_type": "rad" if m.kind == "rad" else "conv",
            "date": m.date,
            "sensor": m.sensor,
            "platform": m.platform,
            "n_channels": m.n_channels,
            "n_obs": m.n_obs,
        }

