# readDiag/adapters.py
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .api import DiagnosticAPI, Metadata, Kind
from ..io.reader import diagAccess  # current backend (facade)
from ..utils import check_kind


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
    ... #     ch_dict  = adapter.table("diagbufchan_df")  # {index: DataFrame}
    ... #     assert isinstance(ch_dict[1], pd.DataFrame)
    """

    def __init__(self, backend: diagAccess) -> None:
        """Initialize adapter over a diagAccess backend.
    
        Parameters
        ----------
        backend
            A fully initialized ``diagAccess`` instance (already opened
            and ready to serve data).

        Notes
        -----
        - Reads file-level metadata **once** and materializes a `Metadata` DTO
          for cheap future access.
        - Avoids writing into properties (uses private caches, e.g. `_file_name`).
        - Uses tolerant heuristics for `kind` and `cycle_dt` when exact fields
          are absent in `get_file_info()`.
        """
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
        """Return the dataset kind (``\"conv\"`` or ``\"rad\"``).

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
        >>> d.kx_list("t")
        [120, 130, 131]
        >>> d.kx_list()  # doctest: +ELLIPSIS
        {'t': [...], 'q': [...], 'uv': [...], 'ps': [...]}
        """
        # Caminho rápido: var especificado
        if var is not None:
            kxs = self._b.get_kx_list(var)  # assume backend já possui este método
            return sorted(set(kxs))

        # Agregado para todas as variáveis
        result: Dict[str, List[int]] = {}
        for v in self.variables():
            kxs = self._b.get_kx_list(v)
            # normaliza: únicos + ordenado
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

        # The backend returns a structured store with a list of per-channel
        # frames under ["dataframes"]["diagbufchan_df"]. We centralize access
        # here to avoid leaking structure to callers.
        store = self._b.get_data_frame()["dataframes"]["diagbufchan_df"]
        # nossa API é 1-based; a lista do backend é 0-based
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
            - ``"diagbufchan_df"``: *mapping* ``{index: DataFrame}``
              for per-channel frames.

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

        # Convert list of per-channel frames to an index->DataFrame mapping.
        if name == "diagbufchan_df":
            lst = df_store["diagbufchan_df"]  # list[DataFrame]
            return {i: df for i, df in enumerate(lst)}

        raise KeyError(f"Unknown table '{name}'")

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
        return self.kx_list(var)

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
                - ``"diagbufchan_df"``: ``list[DataFrame]``  # per channel

                ``}}``

        Notes
        -----
        This method exists solely for backwards compatibility. Prefer
        :meth:`variables`, :meth:`kx_list`, :meth:`frame_conv`,
        :meth:`channels`, :meth:`frame_channel` and :meth:`table`.
        """
        if self.kind() == "conv":
            # Build the legacy nested mapping on demand to avoid exposing
            # internal storage formats externally.
            out: dict[str, dict[int, pd.DataFrame]] = {}
            for var in self.variables():
                inner: dict[int, pd.DataFrame] = {}
                for kx in self.kx_list(var):
                    inner[kx] = self.frame_conv(var, kx)
                out[var] = inner
            return out

        # Radiance (kept verbatim, including list-of-frames for channels)
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
       """Full file path as string (legacy convenience)."""
       # Prefer backend attribute if available; fall back to metadata.
       return str(
           getattr(self._b, "file_name", "") or self._meta.file_name or self._file_name
       )

