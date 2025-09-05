# --- readDiag.utils ---------------------------------------------------------
from __future__ import annotations

"""Utility helpers for logging, timing, endianness, parsing, and GSI usage.

This module centralizes small, reusable utilities used across *readDiag*.
Docstrings adopt the **NumPy** style and include clear contracts (types,
preconditions), behavior notes, and examples whenever relevant.

Contents
--------
- **Logging / timing / deprecation**: :data:`logger`, :func:`log_time`,
  :func:`deprecated` and the custom warning :class:`ReadDiagDeprecationWarning`.
- **Endianness**: :func:`needs_swap_dtype`, :func:`fix_endian` to normalize
  NumPy dtypes and arrays to native byte order.
- **Parsing & labels**: :func:`extract_int`, :func:`mask_to_query`,
  :func:`nice_label`, :func:`guess_cycle_token`, :func:`replace_sentinels`.
- **Plotting contracts**: :func:`check_kind` decorator used by plotting
  classes to guard methods by diagnostic kind.
- **Radiance extraction**: :func:`get_rad_data_by_channel` to obtain
  per-channel DataFrames from :class:`~readDiag.reader.diagAccess`.
- **GSI usage helpers**: :class:`IuseDecoded`, :func:`decode_iuse`,
  :func:`attach_iuse_decoded`, :func:`apply_usage_filter`.

Notes
-----
- Python **3.10+** is required; the module uses modern typing (``|`` union).
- Inline comments in PT-BR explain implementation steps quickly.
"""

from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
import functools
import logging
import os
import re
import sys
import time
import warnings
from typing import Any, Iterable, Literal, Optional, Tuple, Dict
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    # Logging / timing / deprecation
    "logger",
    "log_time",
    "deprecated",
    "ReadDiagDeprecationWarning",
    # Endianness
    "needs_swap_dtype",
    "fix_endian",
    # Small helpers
    "check_kind",
    "extract_int",
    "mask_to_query",
    "nice_label",
    "guess_cycle_token",
    "get_rad_data_by_channel",
    "replace_sentinels",
    # GSI usage helpers
    "IuseDecoded",
    "decode_iuse",
    "attach_iuse_decoded",
    "apply_usage_filter",
]

# ============================================================================
# Logger factory and module-level logger
# ============================================================================


def _build_logger() -> logging.Logger:
    """Create (or return) the package logger with console + rotating file.

    The function is **idempotent**: if a ``readDiag`` logger already has
    handlers attached, it is returned unchanged.

    Environment
    -----------
    DIAGACCESS_LOG_LEVEL : {"DEBUG", "INFO", "WARNING", "ERROR"}
        Controls the logger's base level. Defaults to ``"INFO"`` when unset
        or invalid.

    Returns
    -------
    logging.Logger
        A configured logger named ``"readDiag"`` with a console handler and a
        rotating file handler (``diagAccess.log``, 10MB, 5 backups).
    """
    lg = logging.getLogger("readDiag")
    if lg.hasHandlers():
        return lg

    # --- formatação comum dos handlers (PT-BR)
    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    lg.addHandler(console)

    # File logging is opt-in: set READDIAG_LOG_FILE to a truthy value or a path
    file_cfg = os.getenv("READDIAG_LOG_FILE", "").strip()
    if file_cfg:
        log_path = file_cfg if any(ch in file_cfg for ch in ("/", "\\")) else "diagAccess.log"
        file_handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(fmt)
        lg.addHandler(file_handler)

    level = os.getenv("DIAGACCESS_LOG_LEVEL", "INFO").upper()
    lg.setLevel(getattr(logging, level, logging.INFO))
    return lg


#: Public module-level logger to be reused by submodules.
logger = _build_logger()

# ============================================================================
# Deprecation helper
# ============================================================================


class ReadDiagDeprecationWarning(DeprecationWarning):
    """Custom deprecation category for ``readDiag``.

    Use this category via :func:`deprecated` to make deprecation warnings more
    visible and easier to grep in logs.
    """


# Make our custom deprecations visible by default
warnings.simplefilter("default", ReadDiagDeprecationWarning)


def deprecated(msg: str, *, stacklevel: int = 3) -> None:
    """Issue a standardized **deprecation** warning.

    The message is prefixed with ``"[DEPRECATED]"`` for easy grepping.

    Parameters
    ----------
    msg : str
        Explanation of what is deprecated and how to migrate.
    stacklevel : int, default: 3
        Frame depth at which the warning should be reported. Increase this
        value when :func:`deprecated` is called by wrappers.

    Raises
    ------
    TypeError
        If ``msg`` is not a string.
    """
    if not isinstance(msg, str):
        raise TypeError(f"Expected 'msg' to be str, got {type(msg).__name__}")
    warnings.warn(
        f"[DEPRECATED] {msg}",
        category=ReadDiagDeprecationWarning,
        stacklevel=stacklevel,
    )

# ============================================================================
# Timing decorator
# ============================================================================


def log_time(func):
    """Decorator to log a function's execution time at **INFO** level.

    The decorated function's name and elapsed time (in seconds) are emitted via
    the module logger.

    Examples
    --------
    >>> @log_time
    ... def slow():
    ...     import time; time.sleep(0.001)
    ...
    >>> slow()  # doctest: +ELLIPSIS

    Returns
    -------
    collections.abc.Callable
        A wrapper that preserves the original function's signature
        (via :func:`functools.wraps`).
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        logger.info("%s completed in %.3fs", func.__name__, duration)
        return result

    return wrapper


# ============================================================================
# NumPy dtype / array endianness helpers
# ============================================================================


def needs_swap_dtype(dt: np.dtype) -> bool:
    """Return ``True`` if any field of a dtype is **non-native** endian.

    Works for both simple and structured dtypes. Fields with byteorder ``'|'``
    (not applicable) and ``'='`` (native) are ignored.

    Parameters
    ----------
    dt : numpy.dtype
        The dtype to test.

    Returns
    -------
    bool
        ``True`` if the dtype contains non-native-endian components.
    """
    native = "<" if sys.byteorder == "little" else ">"

    # Plain dtype: check directly
    if dt.fields is None:
        return dt.byteorder not in ("=", "|", native)

    # Structured dtype: check each field
    for _name, (subdt, _off) in dt.fields.items():
        bo = subdt.byteorder
        if bo in ("|", "="):
            continue
        if bo != native:
            return True
    return False


def fix_endian(arr: np.ndarray) -> np.ndarray:
    """Convert arrays (plain or structured) to **native endianness**.

    The function is **idempotent**: an array already in native byte order is
    returned unchanged (view or shallow copy as per NumPy semantics).

    Parameters
    ----------
    arr : numpy.ndarray
        Array to normalize.

    Returns
    -------
    numpy.ndarray
        View/copy with native endianness. Copies only when needed.
    """
    dt = arr.dtype
    if not needs_swap_dtype(dt):
        return arr

    swapped = arr.byteswap(inplace=False)
    try:
        return swapped.view(dt.newbyteorder("="))
    except Exception:  # pragma: no cover – legacy NumPy fallback
        return swapped.newbyteorder("=")


# ============================================================================
# Small parsing / labeling helpers
# ============================================================================

# Precompiled pieces used by mask_to_query
_AND_OR_MAP = {"&": " and ", "|": " or "}


def _compile_drop_pattern(drop_token: str) -> re.Pattern[str]:
    """Compile a pattern to remove ``(drop_token == N)`` clauses.

    Parameters
    ----------
    drop_token : str
        Token to match (e.g., ``"nchan"`` or ``"kx"``). The token is escaped
        to be used safely in a regex.

    Returns
    -------
    re.Pattern
        Compiled pattern that matches the shortest ``(...)`` group containing
        the equality ``drop_token == <integer>``.
    """
    return re.compile(rf"\(.*?{re.escape(drop_token)}\s*==\s*\d+\)")


def extract_int(expr: str | None, pattern: str, default: int | None) -> int | None:
    """Extract an integer from a regex match, or return a default.

    Parameters
    ----------
    expr : str or None
        Input string to search. If ``None`` or empty, ``default`` is returned.
    pattern : str
        Regular expression with **one capturing group** for the integer
        (e.g., ``r"nchan\\s*==\\s*(\\d+)"``).
    default : int or None
        Value returned when no match is found.

    Returns
    -------
    int or None
        Parsed integer on success; otherwise ``default``.

    Notes
    -----
    The function does not validate group counts; it simply attempts to read
    the first group and cast it to ``int`` if a match exists.
    """
    if not expr:
        return default
    m = re.search(pattern, expr)
    return int(m.group(1)) if m else default


def mask_to_query(mask: str, drop_token: str) -> str:
    """Convert a legacy boolean mask into a ``DataFrame.query`` expression.

    Replaces any clause of the form ``(drop_token==N)`` by ``True`` and
    transforms ``&``/``|`` into ``and``/``or`` as required by
    :meth:`pandas.DataFrame.query`.

    Parameters
    ----------
    mask : str
        Legacy boolean expression, e.g. ``"(nchan==15) & (omf<2) | (kx==3)"``.
    drop_token : str
        Token to drop entirely (e.g., ``"nchan"`` or ``"kx"``).

    Returns
    -------
    str
        Sanitized expression suitable for ``DataFrame.query``.
    """
    q = _compile_drop_pattern(drop_token).sub("True", mask)
    return q.replace("&", _AND_OR_MAP["&"]).replace("|", _AND_OR_MAP["|"])


def nice_label(col: str) -> str:
    """Return a human-friendly label for common diagnostic columns.

    Parameters
    ----------
    col : str
        Raw column name (e.g., ``"omf"``, ``"tb_obs"``).

    Returns
    -------
    str
        Prettier label; if unknown, the input is returned unchanged.
    """
    return {
        "tb_obs": "Brightness Temperature [K]",
        "omf": "O–F",
        "oma": "O–A",
    }.get(col, col)


def guess_cycle_token(path: str) -> str:
    """Guess a cycle timestamp token (``YYYYMMDDHH``) from a filepath suffix.

    Parameters
    ----------
    path : str
        A filename or path possibly ending with ``.YYYYMMDDHH``.

    Returns
    -------
    str
        Human-friendly timestamp like ``'17Aug2025 - 1200 GMT'`` if parsing
        succeeds; otherwise the original trailing token (or empty string).
    """
    token = path.split(".")[-1] if "." in path else ""
    try:
        return datetime.strptime(token, "%Y%m%d%H").strftime("%d%b%Y - %H00 GMT")
    except Exception:
        return token


def replace_sentinels(df: pd.DataFrame, threshold: float = 1e10) -> pd.DataFrame:
    """Replace sentinel magnitudes by ``NaN`` in numeric columns.

    This is useful to sanitize data at read time so downstream code does not
    mistake large sentinel values (e.g., ``1.0e+11``) for valid measurements.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame.
    threshold : float, default: 1e10
        Any absolute value ``>= threshold`` is replaced by ``NaN``.

    Returns
    -------
    pandas.DataFrame
        A new DataFrame with sentinel values replaced.
    """
    out = df.copy()
    num_cols = out.select_dtypes(include=[np.number]).columns
    out[num_cols] = out[num_cols].where(out[num_cols].abs() < threshold, np.nan)
    return out


def check_kind(kind: str):
    def decorator(func):
        import functools
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            actual = getattr(self, "kind", None)
            actual = actual() if callable(actual) else actual
            if actual is None:
                d = getattr(self, "diag", None)
                if d is not None:
                    _k = getattr(d, "kind", None)
                    actual = _k() if callable(_k) else _k
                    if actual is None:
                        _m = getattr(d, "meta", None)
                        if callable(_m):
                            try:
                                actual = getattr(_m(), "kind", None)
                            except Exception:
                                actual = None
            if actual != kind:
                raise ValueError(f"{func.__name__} only valid for {kind} diagnostics")
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
    return decorator

    return decorator


# ============================================================================
# Radiance extraction helper
# ============================================================================


def get_rad_data_by_channel(
    diag,
    varName: str,
    q: Optional[str],
    *,
    strict: bool = False,
    verbose: bool = True,
) -> Dict[int, pd.DataFrame]:
    """Extract radiance diagnostic data by channel.

    Iterates over all channels available for a given radiance variable and
    collects their DataFrames. Optionally applies a filtering expression
    (``pandas.DataFrame.query``).

    Parameters
    ----------
    diag : object
        Diagnostic object (usually :class:`~readDiag.reader.diagAccess`). Must
        implement:

        - ``get_channel_list(varName)`` → list of available channels.
        - ``get_dataframe(varName, channel)`` → DataFrame for the channel.
    varName : str
        Radiance variable name, e.g. ``'amsua_n15'``.
    q : str or None
        Optional query expression passed to :meth:`pandas.DataFrame.query` for
        row filtering. If invalid for a given DataFrame, it is ignored.
    strict : bool, default: False
        - ``True`` → raise ``ValueError`` if no non-empty channel data is
          extracted.
        - ``False`` → return empty dict in that case.
    verbose : bool, default: True
        If ``True``, print messages when a channel cannot be loaded or is
        empty after filtering.

    Returns
    -------
    dict of int → pandas.DataFrame
        Mapping from channel number to its DataFrame. Each DataFrame contains
        at least ``'lon'`` and ``'lat'`` columns, plus other diagnostic fields
        (e.g., ``'omf'``, ``'oma'``, ``'tb_obs'``).

    Raises
    ------
    ValueError
        If ``strict=True`` and no data is extracted for ``varName``.

    Notes
    -----
    - Channels that raise errors in ``get_dataframe`` are skipped.
    - Empty DataFrames (after filtering) are skipped unless ``strict=True``.
    - Useful as a building block for plotting functions that need per-channel
      scatter plots.

    Examples
    --------
    >>> data = get_rad_data_by_channel(diag, "amsua_n15", q="omf < 2")
    >>> sorted(data.keys())
    [1, 2, 3, 4, 5]

    Iterate channels and inspect sizes:

    >>> for ch, df in data.items():
    ...     print(f"Channel {ch}: {len(df)} rows")
    Channel 1: 1240 rows
    Channel 2: 1198 rows
    """
    data: Dict[int, pd.DataFrame] = {}
    if not hasattr(diag, "get_channel_list"):
        return data

    for ch in diag.get_channel_list(varName):
        try:
            df = diag.get_dataframe(varName, ch)
        except Exception:
            continue

        if q:
            try:
                df = df.query(q)
            except Exception:
                pass

        if df is None or df.empty:
            if verbose:
                print(f"[get_rad_data_by_channel] empty for ch={ch}")
            continue

        data[int(ch)] = df

    if strict and not data:
        raise ValueError(f"No data extracted for var={varName}")

    return data


# ============================================================================
# GSI usage / QC helpers (iuse/iusev)
# ============================================================================

# Reference notes (adapted from read_prepbufr.f90 in your version)
# 0      -> initialized usable (usage=0)
# 1..99  -> hold-out/cross-validation groups
# 100..  -> various not-used reasons (QM, PQM, aux fields, sanity checks)
IuseCategory = Literal[
    "pre:used",        # iuse == 0
    "pre:not-used",    # iuse in {100, 101, 102, 103, 115, 116, 117, 118, ...}
    "pre:holdout",     # 1..99
    "pre:unknown",
]


@dataclass(frozen=True)
class IuseDecoded:
    """Decoded representation of a GSI ``iuse`` code.

    Parameters
    ----------
    code : int
        Raw value from the ``iuse`` column.
    label : str
        Human-readable description of the code.
    category : {"pre:used", "pre:not-used", "pre:holdout", "pre:unknown"}
        Coarse-grained category useful for filtering/plotting.
    """

    code: int
    label: str
    category: IuseCategory


def decode_iuse(code: int) -> IuseDecoded:
    """Decode GSI ``iuse`` to a human label and category.

    Parameters
    ----------
    code : int
        Raw integer from the ``iuse`` column.

    Returns
    -------
    IuseDecoded
        Structured representation with fields ``code``, ``label`` and
        ``category``.
    """
    try:
        v = int(code)
    except Exception:
        return IuseDecoded(code=-9999, label="invalid", category="pre:unknown")

    if v == 0:
        return IuseDecoded(v, "usable (prep)", "pre:used")
    if 1 <= v <= 99:
        return IuseDecoded(v, f"hold-out / cross-validation group {v}", "pre:holdout")

    mapping = {
        100: "not-used: config/QM(9/12/15)/special KX",
        101: "not-used: element QM >= lim_qm",
        102: "not-used: program PQM >= lim_qm",
        103: "not-used: auxiliary field (gust/vis/td/pm/maxT/minT/wave/ceil)",
        115: "not-used: calm wind",
        116: "not-used: Td unrealistically low",
        117: "not-used: dewpoint depression > 70°C",
        118: "not-used: Td unrealistically high",
    }
    if v in mapping:
        return IuseDecoded(v, mapping[v], "pre:not-used")
    return IuseDecoded(v, f"code {v}", "pre:unknown")


def attach_iuse_decoded(
    df: pd.DataFrame, iuse_col: str = "iuse", *, drop_existing: bool = False
) -> pd.DataFrame:
    """Attach ``iuse_label`` and ``iuse_category`` derived from :func:`decode_iuse`.

    Keeps the raw ``iuse`` intact. If the column is absent, returns the input
    unchanged.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame.
    iuse_col : str, default: "iuse"
        Column name with ``iuse`` codes.
    drop_existing : bool, default: False
        If ``True``, drop existing decoded columns before attaching.

    Returns
    -------
    pandas.DataFrame
        A copy of the DataFrame with two extra columns: ``iuse_label`` and
        ``iuse_category``.
    """
    if iuse_col not in df.columns:
        return df
    out = df.copy()
    if drop_existing:
        out = out.drop(columns=[c for c in ("iuse_label", "iuse_category") if c in out.columns])
    dec = [decode_iuse(v) for v in out[iuse_col].tolist()]
    out["iuse_label"] = [d.label for d in dec]
    out["iuse_category"] = [d.category for d in dec]
    return out


UsageMode = Literal["all", "pre:used", "pre:monitored", "post:assimilated", "post:monitored"]
UsageStage = Literal["auto", "pre", "post"]
UsageField = Literal["auto", "iuse", "use", "iusev", "analysis_use"]


def _choose_usage_column(
    df: pd.DataFrame, *, stage: UsageStage = "auto", field: UsageField = "auto"
) -> str | None:
    """Select a column to use for usage filtering.

    Stage logic
    -----------
    - ``'pre'``  → prefer ``'iuse'``, fallback ``'use'``
    - ``'post'`` → prefer ``'iusev'``, fallback ``'analysis_use'``
    - ``'auto'`` → try *post* first, then *pre*

    If ``field`` is not ``'auto'``, its value is honored when present.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame to inspect.
    stage : {"auto", "pre", "post"}, default: "auto"
        Stage preference when detecting a suitable column.
    field : {"auto", "iuse", "use", "iusev", "analysis_use"}, default: "auto"
        Explicit column preference.

    Returns
    -------
    str or None
        The chosen column name, or ``None`` if none matches.
    """
    if field != "auto":
        return field if field in df.columns else None

    def _pre() -> str | None:
        return "iuse" if "iuse" in df.columns else ("use" if "use" in df.columns else None)

    def _post() -> str | None:
        return "iusev" if "iusev" in df.columns else ("analysis_use" if "analysis_use" in df.columns else None)

    if stage == "pre":
        return _pre()
    if stage == "post":
        return _post()
    return _post() or _pre()


def apply_usage_filter(
    df: pd.DataFrame,
    *,
    mode: UsageMode = "all",
    stage: UsageStage = "auto",
    field: UsageField = "auto",
) -> Tuple[pd.DataFrame, str | None]:
    """Apply canonical usage filters to a diagnostic DataFrame.

    Modes
    -----
    - **all**: no filter
    - **pre:used**: ``iuse == 0`` (or ``use == 0``)
    - **pre:monitored**: ``iuse != 0`` (or ``use != 0``)
    - **post:assimilated**: ``iusev == +1`` (or ``analysis_use == +1``)
    - **post:monitored**: ``iusev == -1`` (or ``analysis_use == -1``)

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame.
    mode : {"all", "pre:used", "pre:monitored", "post:assimilated", "post:monitored"}, default: "all"
        Requested usage filter.
    stage : {"auto", "pre", "post"}, default: "auto"
        Stage preference used internally by :func:`_choose_usage_column`.
    field : {"auto", "iuse", "use", "iusev", "analysis_use"}, default: "auto"
        Explicit column preference.

    Returns
    -------
    (pandas.DataFrame, str or None)
        Tuple of *(filtered_df, column_used)*. If no suitable column exists,
        returns an **empty** slice and ``None``.
    """
    if mode == "all":
        col = _choose_usage_column(df, stage=stage, field=field)
        return df, col

    if mode.startswith("pre:"):
        col = _choose_usage_column(df, stage="pre", field=field)
        if not col:
            return df.iloc[0:0], None
        s = df[col]
        return (df[s == 0], col) if mode == "pre:used" else (df[s != 0], col)

    col = _choose_usage_column(df, stage="post", field=field)
    if not col:
        return df.iloc[0:0], None
    s = df[col]
    if mode == "post:assimilated":
        return df[s == 1], col
    if mode == "post:monitored":
        return df[s == -1], col
    return df, col


# ---------------------------------------------------------------------
# Cycle resolution utilities
# ---------------------------------------------------------------------

_CYCLE_PAT = re.compile(r"(\d{10})")  # ex: 2024013018

def _as_dt(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        s = str(int(val))
        if len(s) in (10, 12, 14):
            fmt = {10: "%Y%m%d%H", 12: "%Y%m%d%H%M", 14: "%Y%m%d%H%M%S"}[len(s)]
            return datetime.strptime(s, fmt)
    if isinstance(val, str):
        s = val.strip().replace("-", "").replace(":", "").replace(" ", "")
        for L, fmt in [(14, "%Y%m%d%H%M%S"), (12, "%Y%m%d%H%M"), (10, "%Y%m%d%H")]:
            if len(s) == L and s.isdigit():
                return datetime.strptime(s, fmt)
    return None


def _token_from_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H")


def _try_metadata(diag: Any) -> Tuple[Optional[datetime], Optional[str]]:
    # procura em atributos comuns
    candidates = []
    for attr in ("cycle_dt", "datetime", "analysis_time", "valid_time", "time"):
        candidates.append(getattr(diag, attr, None))

    # procura em dicionários comuns
    for dict_attr in ("meta", "metadata", "header", "info"):
        d = getattr(diag, dict_attr, None)
        if isinstance(d, dict):
            for key in ("cycle_dt", "datetime", "analysis_time", "valid_time", "time", "date", "cycle"):
                candidates.append(d.get(key))

    for c in candidates:
        dt = _as_dt(c)
        if dt:
            return dt, _token_from_dt(dt)
        if isinstance(c, str):
            m = _CYCLE_PAT.search(c)
            if m:
                token = m.group(1)
                try:
                    return datetime.strptime(token, "%Y%m%d%H"), token
                except Exception:
                    pass
    return None, None


def _try_filename(diag: Any) -> Tuple[Optional[datetime], Optional[str]]:
    name = getattr(diag, "file_name", None)
    if not name:
        p = getattr(diag, "path", None) or getattr(diag, "filepath", None)
        if p:
            try:
                name = Path(p).name
            except Exception:
                name = str(p)
    if not name:
        return None, None
    m = _CYCLE_PAT.search(str(name))
    if not m:
        return None, None
    token = m.group(1)
    try:
        return datetime.strptime(token, "%Y%m%d%H"), token
    except Exception:
        return None, None


def get_cycle(diag: Any) -> Tuple[Optional[datetime], Optional[str]]:
    """Retorna (cycle_dt, cycle_token) na ordem:
    1. metadados do arquivo
    2. nome do arquivo
    3. None, None
    """
    dt, tok = _try_metadata(diag)
    if dt:
        return dt, tok
    return _try_filename(diag)


