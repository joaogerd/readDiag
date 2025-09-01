# readDiag/surface.py
from __future__ import annotations

"""Stable surface (protocol) for readDiag diagnostic backends.

This module defines the minimal, reader-agnostic interface that plotting,
analytics and higher-level tools will depend on. Concrete backends (e.g.,
adapters over legacy readers or newer implementations) must implement this
surface without leaking internal or unstable structures.

Design goals
------------
- **Stability**: expose a thin, durable interface that survives backend changes.
- **Simplicity**: use plain Python and pandas types; avoid backend-specific dicts.
- **Separation of concerns**: parsing/IO stays in backends; orchestration lives
  at higher levels; this surface is the contract between them.

Quick example
-------------
Wrap an existing backend and consume this surface:

>>> # from readDiag.reader import diagAccess
>>> # from readDiag.adapters import AccessAdapter
>>> # b = diagAccess("/path/to/diag_amsua_n15_03.2024013018")
>>> # api = AccessAdapter(b)     # api : DiagnosticAPI
>>> # m = api.meta()
>>> # m.kind
... # 'rad'
>>> # if m.kind == "rad":
... #     ch = api.channels()
... #     df = api.frame_channel(ch[0])

Implementing a custom backend (sketch):

>>> # from dataclasses import dataclass
>>> # import pandas as pd
>>> # class MyBackend:
... #     ...
>>> # @dataclass(frozen=True)
... # class MyAdapter(DiagnosticAPI):
... #     _b: MyBackend
... #     def meta(self) -> Metadata: ...
... #     def kind(self) -> Kind: ...
... #     def variables(self) -> list[str]: ...
... #     def kx_list(self, var: str) -> list[int]: ...
... #     def frame_conv(self, var: str, kx: int) -> pd.DataFrame: ...
... #     def channels(self) -> list[int]: ...
... #     def frame_channel(self, ch_index: int) -> pd.DataFrame: ...
... #     def table(self, name: str) -> pd.DataFrame | dict[int, pd.DataFrame]: ...
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, TypeAlias

import pandas as pd

__all__ = ["Kind", "Metadata", "DiagnosticAPI"]

# ---------------------------------------------------------------------------
# Public, stable aliases/types
# ---------------------------------------------------------------------------
Kind: TypeAlias = Literal["conv", "rad"]


# ---------------------------------------------------------------------------
# File-level metadata
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Metadata:
    """Minimal, format-stable metadata returned by any diagnostic backend.

    This structure is intentionally compact and avoids backend-specific keys.
    It captures only the information that higher layers consistently need.

    Parameters
    ----------
    file_name : str
        Original path to the diagnostic file (may be absolute or relative).
    date : datetime
        Analysis cycle timestamp parsed from the file header.
    kind : {"conv", "rad"}
        High-level data category used by plotting and higher-level tools.
    sensor : str, optional
        Sensor/instrument ID, when available (commonly for radiance).
    platform : str, optional
        Platform/satellite identifier, when available (commonly for radiance).
    n_channels : int, optional
        Number of channels (radiance), if known.
    n_obs : int, optional
        Total number of observations (radiance or conventional), if known.

    Attributes
    ----------
    file_name : str
    date : datetime
    kind : {"conv", "rad"}
    sensor : str or None
    platform : str or None
    n_channels : int or None
    n_obs : int or None

    Notes
    -----
    - The dataclass is **frozen** to allow safe sharing and hashing where useful.
    - Backends should populate missing/unknown fields with ``None`` rather than
      inventing placeholder values.
    """

    file_name: str
    date: datetime
    kind: Kind
    sensor: str | None = None
    platform: str | None = None
    n_channels: int | None = None
    n_obs: int | None = None


# ---------------------------------------------------------------------------
# Stable protocol for diagnostic access
# ---------------------------------------------------------------------------
class DiagnosticAPI(Protocol):
    """Stable, reader-agnostic surface for readDiag tools.

    Implementations should be thin adapters around concrete readers and must
    not leak backend-specific data structures (e.g., nested dicts/lists with
    implicit invariants). Prefer returning :class:`pandas.DataFrame` and plain
    Python types only.

    Contract
    --------
    - **Generic**: :meth:`meta` returns immutable :class:`Metadata`; :meth:`kind`
      returns the dataset category.
    - **Conventional**: callers can enumerate variables and their WMO platform
      codes (``kx``) and request a slice as a DataFrame.
    - **Radiance**: callers can enumerate channel indices and request a
      per-channel DataFrame; common radiance tables are exposed by a small
      set of stable names via :meth:`table`.

    Error semantics
    ---------------
    - Methods that are not meaningful for the current ``kind`` **must** raise
      ``ValueError`` (e.g., calling :meth:`frame_channel` on a conventional file).
    - Out-of-range or unknown keys (variable, kx, channel, table name) **should**
      raise ``KeyError`` where appropriate.

    Performance
    -----------
    Implementations may lazily read data or cache frames. The protocol does not
    mandate eager loading; it mandates only the *shape* of the responses.

    Examples
    --------
    >>> # Assume `api` is a DiagnosticAPI for a conventional file:
    ... # for var in api.variables():
    ... #     for kx in api.kx_list(var):
    ... #         df = api.frame_conv(var, kx)
    ... #         assert isinstance(df, pd.DataFrame)

    >>> # For radiance:
    ... # ch = api.channels()
    ... # ch_df = api.frame_channel(ch[0])
    ... # main = api.table("diagbuf_df")
    ... # assert isinstance(main, pd.DataFrame)
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


