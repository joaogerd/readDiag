# --- readDiag/surface.py ----------------------------------------------------
from __future__ import annotations

"""
Stable surface (protocol) for readDiag diagnostic backends
=========================================================

This module defines the **minimal, reader-agnostic interface** (protocol) that
plotting, analytics, and higher-level tools depend on. Concrete backends
(e.g., adapters wrapping legacy readers or newer implementations) must
implement this surface without leaking internal or unstable structures.

Design goals
------------
- **Stability**: expose a thin, durable interface that survives backend changes.
- **Simplicity**: rely on plain Python and pandas types; avoid backend-specific dicts.
- **Separation of concerns**: parsing/IO is handled in backends, orchestration
  happens in higher layers; this surface acts as the *contract* between them.

Examples
--------
Wrap an existing backend and consume this surface:

>>> from readDiag.reader import diagAccess
>>> from readDiag.adapters import AccessAdapter
>>> b = diagAccess("data/diag_amsua_n15_03.2024013018")
>>> api = AccessAdapter(b)   # api : DiagnosticAPI
>>> m = api.meta()
>>> m.kind
'rad'
>>> if m.kind == "rad":
...     ch = api.channels()
...     df = api.frame_channel(ch[0])
...     assert isinstance(df, pd.DataFrame)

Implementing a custom backend (sketch):

>>> from dataclasses import dataclass
>>> import pandas as pd
>>> @dataclass(frozen=True)
... class MyAdapter(DiagnosticAPI):
...     _b: object  # concrete backend
...     def meta(self) -> Metadata: ...
...     def kind(self) -> Kind: ...
...     def variables(self) -> list[str]: ...
...     def kx_list(self, var: str) -> list[int]: ...
...     def frame_conv(self, var: str, kx: int) -> pd.DataFrame: ...
...     def channels(self) -> list[int]: ...
...     def frame_channel(self, ch_index: int) -> pd.DataFrame: ...
...     def table(self, name: str) -> pd.DataFrame | dict[int, pd.DataFrame]: ...
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, TypeAlias, Optional

import pandas as pd

__all__ = ["Kind", "Metadata", "DiagnosticAPI"]

# ---------------------------------------------------------------------------
# Public, stable aliases/types
# ---------------------------------------------------------------------------
Kind: TypeAlias = Literal["conv", "rad"]  # dataset category alias


# ---------------------------------------------------------------------------
# File-level metadata
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Metadata:
    """
    Minimal, format-stable metadata returned by any diagnostic backend.

    This dataclass encapsulates only the most essential attributes that higher-level
    layers (e.g., plotting, analytics) consistently need, regardless of backend
    implementation. It is intentionally compact and avoids backend-specific details.

    Parameters
    ----------
    file_name : str
        Original path to the diagnostic file (absolute or relative).
    date : datetime
        Analysis cycle timestamp parsed from the file header.
    kind : {"conv", "rad"}
        High-level category of the dataset. Either conventional (`"conv"`) or radiance (`"rad"`).
    sensor : str, optional
        Sensor/instrument ID when available (commonly provided for radiance diagnostics).
    platform : str, optional
        Platform or satellite identifier, when available (commonly for radiance diagnostics).
    n_channels : int, optional
        Number of channels (radiance only), if known.
    n_obs : int, optional
        Total number of observations (radiance or conventional), if known.

    Attributes
    ----------
    file_name : str
        Path to the diagnostic file.
    date : datetime
        Timestamp of the diagnostic cycle.
    kind : str
        Dataset category (`"conv"` or `"rad"`).
    sensor : str or None
        Sensor identifier.
    platform : str or None
        Platform/satellite identifier.
    n_channels : int or None
        Number of channels.
    n_obs : int or None
        Number of observations.

    Notes
    -----
    - The dataclass is **frozen**, meaning instances are immutable and hashable.
    - Missing or unknown fields should be represented by ``None``.
    - Intended for use in logging, summaries, and lightweight metadata checks.

    Examples
    --------
    Create a metadata object for a conventional diagnostics file:

    >>> from datetime import datetime
    >>> meta = Metadata(
    ...     file_name="diag_conv_t.2024010100",
    ...     date=datetime(2024, 1, 1, 0),
    ...     kind="conv",
    ...     n_obs=123456
    ... )
    >>> meta.kind
    'conv'
    >>> meta.n_obs > 0
    True

    Create a metadata object for a radiance diagnostics file:

    >>> meta = Metadata(
    ...     file_name="diag_amsua_n15_03.2024010100",
    ...     date=datetime(2024, 1, 1, 0),
    ...     kind="rad",
    ...     sensor="amsua",
    ...     platform="n15",
    ...     n_channels=15,
    ...     n_obs=654321
    ... )
    >>> print(meta.pretty())
    Arquivo : diag_amsua_n15_03.2024010100
    Data    : 2024-01-01 00:00 UTC
    Tipo    : rad
    Sensor  : amsua
    Plataf. : n15
    Canais  : 15
    Obs     : 654321
    """

    file_name: str
    date: datetime
    kind: str  # "conv" | "rad"
    sensor: Optional[str] = None
    platform: Optional[str] = None
    n_channels: Optional[int] = None
    n_obs: Optional[int] = None

    def pretty(self) -> str:
        """
        Return a human-friendly, formatted string of the metadata.

        Returns
        -------
        str
            Multiline string with aligned key-value pairs.

        Examples
        --------
        >>> from datetime import datetime
        >>> meta = Metadata(
        ...     file_name="diag_conv_t.2024010100",
        ...     date=datetime(2024, 1, 1, 0),
        ...     kind="conv",
        ...     n_obs=100
        ... )
        >>> print(meta.pretty())
        Arquivo : diag_conv_t.2024010100
        Data    : 2024-01-01 00:00 UTC
        Tipo    : conv
        Sensor  : -
        Plataf. : -
        Canais  : -
        Obs     : 100
        """
        return (
            f"Arquivo : {self.file_name}\n"
            f"Data    : {self.date:%Y-%m-%d %H:%M UTC}\n"
            f"Tipo    : {self.kind}\n"
            f"Sensor  : {self.sensor or '-'}\n"
            f"Plataf. : {self.platform or '-'}\n"
            f"Canais  : {self.n_channels or '-'}\n"
            f"Obs     : {self.n_obs or '-'}"
        )
# ---------------------------------------------------------------------------
# Stable protocol for diagnostic access
# ---------------------------------------------------------------------------
class DiagnosticAPI(Protocol):
    """Stable, reader-agnostic surface for readDiag tools.

    Implementations should be **thin adapters** around concrete readers and must
    not leak backend-specific data structures (nested dicts/lists with implicit
    invariants). Prefer returning :class:`pandas.DataFrame` and plain Python types.

    Contract
    --------
    - **Generic**: :meth:`meta` returns immutable :class:`Metadata`; :meth:`kind`
      returns the dataset category.
    - **Conventional**: enumerate variables and their WMO platform codes (``kx``),
      request slices as DataFrames.
    - **Radiance**: enumerate channel indices, request per-channel DataFrames,
      and access common radiance tables by stable names.

    Error semantics
    ---------------
    - Invalid calls (e.g., calling :meth:`frame_channel` on a conventional file)
      **must** raise ``ValueError``.
    - Unknown/out-of-range keys (variable, kx, channel, table) **should** raise
      ``KeyError``.

    Performance
    -----------
    - Implementations may lazily read or cache data.
    - The protocol enforces *shape* and type of responses, not loading strategy.

    Examples
    --------
    For a conventional file:

    >>> api: DiagnosticAPI = ...
    >>> if api.kind() == "conv":
    ...     for var in api.variables():
    ...         for kx in api.kx_list(var):
    ...             df = api.frame_conv(var, kx)
    ...             assert isinstance(df, pd.DataFrame)

    For a radiance file:

    >>> api: DiagnosticAPI = ...
    >>> if api.kind() == "rad":
    ...     ch = api.channels()
    ...     ch_df = api.frame_channel(ch[0])
    ...     meta_tbl = api.table("channel_df")
    ...     assert isinstance(meta_tbl, pd.DataFrame)
    """

    # ---- generic ----
    def meta(self) -> Metadata:
        """Return immutable file-level metadata.

        Returns
        -------
        Metadata
            File name, timestamp, kind and optional instrument/platform/counts.
        """
        ...

    def kind(self) -> Kind:
        """Return the dataset kind.

        Returns
        -------
        {"conv", "rad"}
            String literal indicating whether the dataset is conventional
            or radiance.
        """
        ...

    # ---- conv only ----
    def variables(self) -> list[str]:
        """List available conventional variables.

        Returns
        -------
        list of str
            Variable names. Should be ``[]`` when ``kind != "conv"``.

        Notes
        -----
        Implementations **may** choose to return ``[]`` instead of raising if
        called on radiance datasets, but higher-level code should prefer
        feature-test via :meth:`kind`.
        """
        ...

    def kx_list(self, var: str) -> list[int]:
        """List WMO platform codes (``kx``) for a given variable.

        Parameters
        ----------
        var : str
            A conventional variable name returned by :meth:`variables`.

        Returns
        -------
        list of int
            Integer ``kx`` codes for the given variable.

        Raises
        ------
        ValueError
            If called for non-conventional datasets.
        KeyError
            If ``var`` is unknown.
        """
        ...

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
            The requested slice.

        Raises
        ------
        ValueError
            If called for non-conventional datasets.
        KeyError
            If ``var`` or ``kx`` are unknown.
        """
        ...

    # ---- rad only ----
    def channels(self) -> list[int]:
        """List available 1-based radiance channel indices.

        Returns
        -------
        list of int
            Channel indices. Should be ``[]`` when ``kind != "rad"``.

        Notes
        -----
        Implementations **should** coerce values to ``int`` for consistency.
        """
        ...

    def frame_channel(self, ch_index: int) -> pd.DataFrame:
        """Return the per-channel DataFrame for a radiance dataset.

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
            If called for non-radiance datasets.
        KeyError
            If ``ch_index`` is unknown/out of range.
        """
        ...

    def table(self, name: str) -> pd.DataFrame | dict[int, pd.DataFrame]:
        """Access named radiance tables via stable identifiers.

        Parameters
        ----------
        name : {"channel_df", "diagbuf_df", "diagbufex_df", "diagbufchan_df"}
            - ``"channel_df"``: instrument/channel metadata (DataFrame).
            - ``"diagbuf_df"``: main diagnostic buffer (DataFrame).
            - ``"diagbufex_df"``: extended diagnostic buffer (DataFrame).
            - ``"diagbufchan_df"``: mapping ``{index: DataFrame}`` for
              per-channel frames.

        Returns
        -------
        pandas.DataFrame or dict of (int -> pandas.DataFrame)
            A single DataFrame for the first three names, or a dictionary
            of per-channel DataFrames for ``"diagbufchan_df"``.

        Raises
        ------
        ValueError
            If called for non-radiance datasets.
        KeyError
            If the table name is unknown.
        """
        ...



