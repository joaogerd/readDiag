# readDiag/adapters.py
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from ..surface import DiagnosticAPI, Metadata, Kind
from ..reader import diagAccess  # current backend (facade)
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
        """Initialize the adapter.

        Parameters
        ----------
        backend
            A fully initialized ``diagAccess`` instance (already opened
            and ready to serve data).

        Notes
        -----
        The constructor reads once the file-level metadata from the
        backend and materializes a :class:`Metadata` instance for fast,
        cheap future access.
        """
        self._b = backend

        # --- Extract and normalize backend metadata once -----------------
        # We rely only on stable keys returned by diagAccess.get_file_info().
        # If a key is optional (sensor/platform), we guard accesses.
        m = backend.get_file_info()
        kind: Kind = "rad" if m.get("data_type") == "rad" else "conv"

        self._meta = Metadata(
            file_name=m["file_name"],
            date=m["date"],
            kind=kind,
            sensor=m.get("sensor"),
            platform=str(m.get("platform")) if m.get("platform") is not None else None,
            n_channels=m.get("n_channels"),
            n_obs=m.get("n_obs"),
        )

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
    def kx_list(self, var: str) -> list[int]:
        """List available WMO platform codes (``kx``) for a variable.

        Parameters
        ----------
        var : str
            A conventional variable name returned by :meth:`variables`.

        Returns
        -------
        list of int
            Integer ``kx`` codes for the given variable. Empty list if not
            a conventional dataset.

        Notes
        -----
        Values are coerced to ``int`` for consistency, even if the backend
        returns ``numpy.int64`` or strings.
        """
        if self.kind() != "conv":
            return []
        return [int(k) for k in self._b.get_kx_list(var)]

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

