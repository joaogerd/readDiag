# readDiag/adapters.py
from __future__ import annotations

"""
AccessAdapter
=============

Adapter that wraps the legacy/low-level ``diagAccess`` facade and exposes a
stable, typed interface consistent with :class:`readDiag.api.DiagnosticAPI`.

Why this exists
---------------
Historically, ``diagAccess`` returned nested dicts/lists whose *shape and keys*
varied a bit across versions (and even sensors). This adapter **centralizes the
translation** from those fragile structures into a clear, predictable surface.

Key behaviors
-------------
- **Kind inference**: determines ``"conv"`` (conventional) vs ``"rad"`` (radiance)
  from file info; falls back to heuristics when needed.
- **Metadata snapshot**: reads metadata once and stores it in a :class:`Metadata`
  DTO for cheap access.
- **Radiance tables**: exposes named tables via :meth:`table` and per-channel
  frames via :meth:`frame_channel`.
- **Conventional slices**: lists variables/KX and fetches DataFrames by
  (variable, kx) via :meth:`frame_conv`.
- **Legacy shims**: preserves a minimal set of legacy getters so old plotting/test
  code continues to work during the migration.

Notes
-----
- This module is designed to be **import-light** and avoid importing plotting
  libraries. Keep high-level visualization in dedicated modules.
- Channel indices in the public API are **1-based**. Internally, some backends
  keep 0-based lists; we normalize as needed.

Examples
--------
Wrap a ``diagAccess`` backend and query metadata:

>>> # from readDiag.io.reader import diagAccess
>>> # from readDiag.adapters import AccessAdapter
>>> # b = diagAccess("/path/to/diag_amsua_n15_03.2024013018")
>>> # d = AccessAdapter(b)
>>> # m = d.meta()
>>> # (m.kind, m.sensor, m.platform)  # doctest: +SKIP
... # ('rad', 'amsua', 'n15')

Conventional workflow (variables/KX → DataFrame):

>>> # if d.kind() == "conv":
... #     for var in d.variables():
... #         for kx in d.kx_list(var):
... #             df = d.frame_conv(var, kx)   # doctest: +SKIP
... #             assert hasattr(df, "shape")

Radiance workflow (channels → per-channel DataFrame):

>>> # if d.kind() == "rad":
... #     for ch in d.channels():
... #         ch_df = d.frame_channel(ch)      # doctest: +SKIP
... #         assert hasattr(ch_df, "columns")

Accessing named radiance tables:

>>> # if d.kind() == "rad":
... #     chan_tbl = d.table("channel_df")     # doctest: +SKIP
... #     main_tbl = d.table("diagbuf_df")     # doctest: +SKIP
... #     ext_tbl  = d.table("diagbufex_df")   # doctest: +SKIP
... #     ch_map   = d.table("diagbufchan_df") # doctest: +SKIP
... #     # ch_map is {1: DataFrame, 2: DataFrame, ...} (1-based)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

import pandas as pd

from .api import DiagnosticAPI, Metadata, Kind
from ..io.reader import diagAccess  # current backend (facade)
from ..utils import check_kind

__all__ = ["AccessAdapter"]


class AccessAdapter(DiagnosticAPI):
    """Adapt ``diagAccess`` to the high-level :class:`DiagnosticAPI`.

    This adapter removes direct dependence on fragile internal dict/list
    structures returned by ``diagAccess`` and exposes a stable, typed
    interface that matches ``DiagnosticAPI``. It also preserves a set of
    **legacy shims** for older plotting/tests code paths while you migrate.

    Notes
    -----
    - The adapter infers the dataset kind (``"conv"`` or ``"rad"``) from
      the metadata returned by ``diagAccess.get_file_info()``.
    - For radiance files, channel-resolved tables are exposed via
      :meth:`frame_channel` and the multi-table store via :meth:`table`.
    - For conventional files, variables and ``kx`` lists are exposed via
      :meth:`variables` and :meth:`kx_list`, and per-slice frames via
      :meth:`frame_conv`.

    Examples
    --------
    Wrap an existing ``diagAccess`` instance and query metadata:

    >>> # backend = diagAccess("/path/to/diag_amsua_n15_03.2024013018")
    >>> # adapter = AccessAdapter(backend)
    >>> # meta = adapter.meta()
    >>> # meta.kind, meta.sensor, meta.n_channels
    ... # ('rad', 'amsua', 15)

    Iterate conventional variables/kx and fetch a DataFrame:

    >>> # if adapter.kind() == "conv":
    ... #     for var in adapter.variables():
    ... #         for kx in adapter.kx_list(var):
    ... #             df = adapter.frame_conv(var, kx)
    ... #             print(var, kx, len(df))

    List radiance channels and fetch a per-channel DataFrame:

    >>> # if adapter.kind() == "rad":
    ... #     for ch in adapter.channels():
    ... #         ch_df = adapter.frame_channel(ch)
    ... #         assert isinstance(ch_df, pd.DataFrame)

    Access the raw radiance tables (stable names):

    >>> # if adapter.kind() == "rad":
    ... #     chan_tbl = adapter.table("channel_df")
    ... #     main_tbl = adapter.table("diagbuf_df")
    ... #     ext_tbl  = adapter.table("diagbufex_df")
    ... #     ch_dict  = adapter.table("diagbufchan_df")  # {1-based index: DF}
    ... #     assert isinstance(ch_dict[1], pd.DataFrame)
    """

    def __init__(self, backend: diagAccess) -> None:
        """Initialize adapter over a :class:`diagAccess` backend.

        Parameters
        ----------
        backend : diagAccess
            A fully initialized ``diagAccess`` instance (already opened
            and ready to serve data).

        Notes
        -----
        - Reads file-level metadata **once** and materializes a :class:`Metadata`
          DTO for cheap future access.
        - Avoids writing into properties (uses private caches, e.g. ``_file_name``).
        - Uses tolerant heuristics for ``kind`` and ``cycle_dt`` when exact fields
          are absent in ``get_file_info()``.
        """
        # Store the backend reference (private: do not expose its surface)
        self._b = backend

        # --- File info snapshot (one-time) ---------------------------------
        try:
            m = backend.get_file_info()
            if not isinstance(m, dict):
                raise TypeError("diagAccess.get_file_info() must return dict")
        except Exception as e:
            raise RuntimeError("Failed to retrieve file info from diagAccess") from e

        # --- Kind inference (stable first, then heuristics) ----------------
        dt = (m.get("kind") or m.get("data_type") or "").strip().lower()
        if dt in {"rad", "radiance"}:
            kind: Kind = "rad"
        elif dt in {"conv", "conventional"}:
            kind = "conv"
        else:
            # Heuristic: presence of channels or n_channels → radiance
            if m.get("n_channels") or hasattr(backend, "channels") or hasattr(backend, "frame_channel"):
                kind = "rad"
            else:
                kind = "conv"

        # --- Resolve file_name with tolerant fallbacks ---------------------
        file_name = (
            m.get("file_name")
            or getattr(backend, "file_name", None)
            or getattr(backend, "filename", None)
            or str(getattr(backend, "path", ""))  # last resort
            or ""
        )

        # --- Build Metadata DTO -------------------------------------------
        date = m.get("date") or m.get("analysis_time") or m.get("datetime") or m.get("valid_time")
        platform = m.get("platform")
        if platform is not None:
            platform = str(platform)

        self._meta = Metadata(
            file_name=file_name,
            date=date,
            kind=kind,
            sensor=m.get("sensor"),
            platform=platform,
            n_channels=m.get("n_channels"),
            n_obs=m.get("n_obs"),
        )

        # --- Cached convenience fields (do NOT assign properties) ----------
        self._file_name: str = self._meta.file_name or file_name
        # keep original date token (str or datetime); deeper normalization lives in utils
        self.date: Optional[datetime | str] = self._meta.date

        # --- Best-effort canonical cycle datetime --------------------------
        # Only parse when trivially safe; complex cases defer to utils.get_cycle(...)
        self.cycle_dt: Optional[datetime] = None
        raw = date
        try:
            if isinstance(raw, datetime):
                self.cycle_dt = raw
            elif isinstance(raw, str):
                tok = raw.strip()
                # Accept tokens with at least YYYYMMDDHH; ignore extra mm/ss if present
                if tok.isdigit() and len(tok) >= 10:
                    self.cycle_dt = datetime.strptime(tok[:10], "%Y%m%d%H")
        except Exception:
            # Be forgiving: plotting can fall back to filename-based cycle parsing
            pass

    # ---------------------------------------------------------------------
    # Generic API
    # ---------------------------------------------------------------------
    def meta(self) -> Metadata:
        """Return immutable file-level metadata.

        Returns
        -------
        Metadata
            Metadata with file name, date, kind, sensor/platform and counts.
        """
        return self._meta

    def kind(self) -> Kind:
        """Return the dataset kind (``"conv"`` or ``"rad"``).

        Returns
        -------
        {"conv", "rad"}
            The inferred dataset kind.
        """
        return self._meta.kind

    # ---------------------------------------------------------------------
    # Conventional (conv) API
    # ---------------------------------------------------------------------
    @check_kind("conv")
    def variables(self) -> list[str]:
        """List available conventional variables.

        Returns
        -------
        list of str
            Variable names. If the dataset is not conventional, returns an
            empty list.

        Notes
        -----
        This is a thin, safe wrapper around ``diagAccess.get_variables()``.
        """
        if self.kind() != "conv":
            return []
        return list(self._b.get_variables())

    @check_kind("conv")
    def kx_list(self, var: Optional[str] = None) -> Union[List[int], Dict[str, List[int]]]:
        """
        Return the list of WMO/BUFR *KX* codes available in the file.

        Parameters
        ----------
        var : str, optional
            Variable name (e.g., ``"t"``, ``"q"``, ``"uv"``, ``"ps"``, ...).
            If provided, returns the KX list for that variable only.
            If ``None`` (default), returns a dict mapping each variable
            to its sorted list of KX codes.

        Returns
        -------
        list of int or dict of str -> list of int
            - If ``var`` is given: a sorted list of integers (KX codes).
            - Otherwise: a mapping ``{variable: [kx, ...]}`` with lists sorted.

        Notes
        -----
        This is a thin adapter over the backend interface. If the backend
        does not provide an aggregate KX listing, we compute it by
        iterating over :meth:`variables` and calling the per-variable KX
        method.

        Examples
        --------
        >>> # d.kx_list("t")                    # doctest: +SKIP
        ... # [120, 130, 131]
        >>> # d.kx_list()                       # doctest: +SKIP
        ... # {'t': [...], 'q': [...], 'uv': [...], 'ps': [...]}
        """
        # Fast path: specific variable
        if var is not None:
            kxs = self._b.get_kx_list(var)  # backend method
            return sorted(set(kxs))

        # Aggregate across all variables
        result: Dict[str, List[int]] = {}
        for v in self.variables():
            kxs = self._b.get_kx_list(v)
            # normalize to unique + sorted
            result[v] = sorted(set(kxs))
        return result

    @check_kind("conv")
    def frame_conv(self, var: str, kx: int) -> pd.DataFrame:
        """Return a conventional slice as a :class:`pandas.DataFrame`.

        Parameters
        ----------
        var : str
            Conventional variable name.
        kx : int
            WMO platform code for the slice.

        Returns
        -------
        pandas.DataFrame
            The requested (``var``, ``kx``) slice.

        Raises
        ------
        ValueError
            If called on a radiance dataset.
        KeyError
            If ``var`` or ``kx`` are not available in the backend.
        """
        if self.kind() != "conv":
            raise ValueError("frame_conv only valid for conventional data.")
        return self._b.get_dataframe(var, kx)

    # ---------------------------------------------------------------------
    # Radiance (rad) API
    # ---------------------------------------------------------------------
    @check_kind("rad")
    def channels(self) -> list[int]:
        """List 1-based channel indices for radiance datasets.

        Returns
        -------
        list of int
            Available channel indices. Empty list if not a radiance dataset.

        Notes
        -----
        Values are coerced to ``int`` for consistency across backends.
        """
        if self.kind() != "rad":
            return []
        return [int(i) for i in self._b.get_channels()]

    @check_kind("rad")
    def frame_channel(self, ch_index: int) -> pd.DataFrame:
        """Return the per-channel :class:`pandas.DataFrame` for radiances.

        Parameters
        ----------
        ch_index : int
            1-based channel index.

        Returns
        -------
        pandas.DataFrame
            Frame containing channel-resolved diagnostics.

        Raises
        ------
        ValueError
            If called on a conventional dataset.
        KeyError
            If the channel index does not exist.
        """
        if self.kind() != "rad":
            raise ValueError("frame_channel only valid for radiance data.")

        # Backend stores a list of per-channel frames at:
        # get_data_frame()["dataframes"]["diagbufchan_df"]
        store = self._b.get_data_frame()["dataframes"]["diagbufchan_df"]
        # Public API is 1-based; backend list is 0-based
        i0 = ch_index - 1
        return store[i0]

    @check_kind("rad")
    def table(self, name: str) -> Any:
        """Access named radiance tables from the backend store.

        Parameters
        ----------
        name : {"channel_df", "diagbuf_df", "diagbufex_df", "diagbufchan_df"}
            Stable table names:
            - ``"channel_df"``: instrument/channel metadata.
            - ``"diagbuf_df"``: main diagnostic buffer table.
            - ``"diagbufex_df"``: extended diagnostic buffer table.
            - ``"diagbufchan_df"``: **mapping** ``{index: DataFrame}``
              for per-channel frames (1-based indices).

        Returns
        -------
        Any
            A :class:`pandas.DataFrame` for the first three names, or a
            ``dict[int, pandas.DataFrame]`` for ``"diagbufchan_df"``.

        Raises
        ------
        ValueError
            If called on a conventional dataset.
        KeyError
            If the table name is not recognized.
        """
        if self.kind() != "rad":
            raise ValueError("table() only for radiance data.")

        df_store: Dict[str, object] = self._b.get_data_frame()["dataframes"]

        # Direct pass-through for single-DataFrame tables.
        if name == "channel_df":
            return df_store["channel_df"]  # type: ignore[return-value]
        if name == "diagbuf_df":
            return df_store["diagbuf_df"]  # type: ignore[return-value]
        if name == "diagbufex_df":
            return df_store["diagbufex_df"]  # type: ignore[return-value]

        # Convert list of per-channel frames to a 1-based index->DataFrame mapping.
        if name == "diagbufchan_df":
            lst = df_store["diagbufchan_df"]  # list[DataFrame]
            return {i: df for i, df in enumerate(lst, start=1)}

        raise KeyError(f"Unknown table '{name}'")

    def bring(
        self,
        ch: int,
        cols: Union[str, Sequence[str]],
        *,
        on: Optional[Sequence[str]] = None,
        how: str = "inner",
        allow_many_to_one: bool = True,
        suffix_map: Optional[Mapping[str, str]] = None,
    ) -> pd.DataFrame:
        """
        Return the channel DataFrame enriched with additional columns
        automatically located from global radiance tables.

        Parameters
        ----------
        ch : int
            1-based channel index.
        cols : str or list of str
            Column(s) to include. If already present in the channel
            DataFrame, no merge is performed.
        on : sequence of str, optional
            Candidate join keys. Only those present in both DataFrames
            will be used. If none are found, falls back to positional join.
        how : str, default="inner"
            Join method.
        allow_many_to_one : bool, default=True
            Whether many-to-one joins are allowed (unique keys required
            only on the table side).
        suffix_map : mapping, optional
            Optional suffixes for conflicting column names per table.

        Returns
        -------
        pandas.DataFrame
            Combined DataFrame with requested columns.
        """
        wanted = [cols] if isinstance(cols, str) else list(cols)
        out = self.frame_channel(ch).copy()

        # case 1: everything already present
        if all(c in out.columns for c in wanted):
            return out

        # candidate tables in priority order
        candidate_tables = ("diagbuf_df", "diagbufex_df", "channel_df")

        default_keys = ["seqno", "obs_id", "iobs", "obsnum", "scanpos", "row", "index"]
        candidates = list(on) if on is not None else default_keys

        for col in wanted:
            if col in out.columns:
                continue  # already present

            # find which table has the column
            source_table = None
            for t in candidate_tables:
                tbl = self.table(t)
                if isinstance(tbl, pd.DataFrame) and col in tbl.columns:
                    source_table = t
                    break

            if source_table is None:
                raise KeyError(f"Column '{col}' not found in any known table.")

            base = self.table(source_table)[[c for c in [col] + candidates if c in self.table(source_table).columns]]

            # determine join keys
            keys = [k for k in candidates if k in out.columns and k in base.columns]

            if keys:
                if not allow_many_to_one:
                    if base.duplicated(keys).any():
                        raise ValueError(f"Join keys {keys} not unique in {source_table}")
                suf = (suffix_map or {}).get(source_table, f"_{source_table}")
                out = out.merge(base, how=how, on=keys, suffixes=("", suf))
            else:
                # fallback: positional join
                if len(out) != len(base):
                    raise ValueError(
                        f"Cannot align by position: different lengths (channel={len(out)}, {source_table}={len(base)})"
                    )
                left = out.reset_index(drop=False).rename(columns={"index": "_row"})
                right = base.reset_index(drop=False).rename(columns={"index": "_row"})
                suf = (suffix_map or {}).get(source_table, f"_{source_table}")
                out = left.merge(right, how=how, on="_row", suffixes=("", suf)).drop(columns="_row")

        return out

    # ---------------------------------------------------------------------
    # Legacy shims (compatibility with older plotting/tests)
    # ---------------------------------------------------------------------
    # These members forward to the new, safer API. Prefer using the modern
    # methods above and remove these shims over time.
    def get_data_type(self) -> int:
        """Legacy: return 1 for conventional, 2 for radiance.

        Returns
        -------
        int
            ``1`` if ``kind == "conv"``, ``2`` otherwise.
        """
        return 2 if self.kind() == "rad" else 1

    def get_variables(self) -> list[str]:
        """Legacy alias for :meth:`variables`."""
        return self.variables()

    def get_kx_list(self, var: str) -> list[int]:
        """Legacy alias for :meth:`kx_list`."""
        return self.kx_list(var)  # type: ignore[return-value]

    def get_channels(self) -> list[int]:
        """Legacy alias for :meth:`channels`."""
        return self.channels()

    def get_dataframe(self, var: str, kx: int) -> pd.DataFrame:
        """Legacy alias mirroring ``diagAccess.get_dataframe(var, kx)``."""
        return self.frame_conv(var, kx)

    def get_data_frame(self) -> dict[str, Any]:
        """Legacy structure for both conventional and radiance datasets.

        Returns
        -------
        dict
            For conventional:
                ``{var -> {kx -> DataFrame}}``

            For radiance:
                ``{"dataframes": {``

                - ``"channel_df"``: ``DataFrame``
                - ``"diagbuf_df"``: ``DataFrame``
                - ``"diagbufex_df"``: ``DataFrame``
                - ``"diagbufchan_df"``: ``list[DataFrame]``  # per channel (legacy)

                ``}}``

        Notes
        -----
        This method exists solely for backwards compatibility. Prefer
        :meth:`variables`, :meth:`kx_list`, :meth:`frame_conv`,
        :meth:`channels`, :meth:`frame_channel` and :meth:`table`.
        """
        if self.kind() == "conv":
            # Build on demand to avoid leaking backend internal storage.
            out: dict[str, dict[int, pd.DataFrame]] = {}
            for var in self.variables():
                inner: dict[int, pd.DataFrame] = {}
                for kx in self.kx_list(var):  # type: ignore[arg-type]
                    inner[kx] = self.frame_conv(var, kx)
                out[var] = inner
            return out

        # Radiance (kept verbatim to match historic callers/tests)
        chan_ids = self.channels()
        return {
            "dataframes": {
                "channel_df": self.table("channel_df"),
                "diagbuf_df": self.table("diagbuf_df"),
                "diagbufex_df": self.table("diagbufex_df"),
                "diagbufchan_df": [self.frame_channel(i) for i in chan_ids],
            }
        }

    def get_file_info(self) -> dict:
        """Return file info in the legacy format used by ``diagAccess``.

        Returns
        -------
        dict
            Mapping with keys:
            ``file_name``, ``data_type``, ``date``, ``sensor``,
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

    # ---------------------------------------------------------------------
    # Legacy properties (kept for plotting/tests)
    # ---------------------------------------------------------------------
    @property
    def file_name(self) -> str:
        """File name (often a full path). Kept for legacy/plotting expectations.

        Notes
        -----
        Historically this attribute has been used both as basename and as
        full path depending on the backend. We preserve the value as provided
        by the backend/metadata to avoid breaking legacy code. If you need the
        basename, apply ``os.path.basename(adapter.file_name)`` at call site.
        """
        return self._file_name

    @property
    def file_path(self) -> str:
        """Full file path as string (legacy convenience).

        Returns
        -------
        str
            The best-effort full path, preferring backend attributes.
        """
        # Prefer backend attribute if available; fall back to metadata.
        return str(
            getattr(self._b, "file_name", "") or self._meta.file_name or self._file_name
        )

