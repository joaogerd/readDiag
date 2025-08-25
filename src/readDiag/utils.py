# --- readDiag.utils ---------------------------------------------------------
from __future__ import annotations

"""
Utilities for logging, timing decorators, and NumPy endianness helpers.

This module centralizes small, reusable utilities used across *readDiag*:

- A preconfigured module-level :data:`logger` (console + rotating file).
- :func:`log_time` decorator for simple runtime measurements.
- :func:`deprecated` to emit standardized deprecation warnings.
- :func:`needs_swap_dtype` and :func:`fix_endian` to normalize NumPy dtypes
  and arrays to native byte order (idempotent, supports NumPy < 2.0 and >= 2.0).

Examples
--------
>>> from readDiag.utils import logger, log_time, deprecated, fix_endian
>>> @log_time
... def work(x):
...     return x * 2
...
>>> _ = work(21)  # doctest: +ELLIPSIS
>>> deprecated("use new_api() instead")
>>> import numpy as np
>>> arr = np.array([1, 2, 3], dtype=">i4")
>>> native = fix_endian(arr)
>>> native.dtype.byteorder in ("=", "|")
True
"""

import functools
import logging
import os
import sys
import time
import warnings
from logging.handlers import RotatingFileHandler
from typing import Any

import numpy as np

__all__ = [
    "logger",
    "log_time",
    "deprecated",
    "needs_swap_dtype",
    "fix_endian",
]


# ---------------------------------------------------------------------------
# Deprecation helper
# ---------------------------------------------------------------------------

def deprecated(msg: str, *, stacklevel: int = 3) -> None:
    """Issue a standardized deprecation warning.

    The message is prefixed with ``"[DEPRECATED]"`` to make grepping logs and
    warnings output easier across the codebase.

    Parameters
    ----------
    msg : str
        Explanation of what is deprecated and how to migrate.
    stacklevel : int, default: 3
        Stack level at which the warning should be reported. Increase this
        value if the helper is wrapped by additional layers.

    Raises
    ------
    TypeError
        If ``msg`` is not a string.
    """
    if not isinstance(msg, str):
        raise TypeError(f"Expected 'msg' to be str, got {type(msg).__name__}")
    warnings.warn(f"[DEPRECATED] {msg}", DeprecationWarning, stacklevel=stacklevel)


# ---------------------------------------------------------------------------
# Logger factory and module-level logger
# ---------------------------------------------------------------------------

def _build_logger() -> logging.Logger:
    """Create (or return) the package logger with console + rotating file.

    Environment
    -----------
    DIAGACCESS_LOG_LEVEL : {"DEBUG", "INFO", "WARNING", "ERROR"}
        Controls the root level for this logger. Defaults to ``"INFO"``.

    Notes
    -----
    - If handlers already exist on the logger, it is returned unchanged to
      avoid duplicate messages when the module is imported multiple times.
    - The rotating file handler writes to ``diagAccess.log`` with 10 MB per
      file and up to 5 backups.
    """
    lg = logging.getLogger("readDiag")
    if lg.hasHandlers():
        return lg

    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    lg.addHandler(console)

    file_handler = RotatingFileHandler(
        "diagAccess.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    lg.addHandler(file_handler)

    level = os.getenv("DIAGACCESS_LOG_LEVEL", "INFO").upper()
    lg.setLevel(getattr(logging, level, logging.INFO))
    return lg


# Public module-level logger for all submodules to reuse
logger = _build_logger()


# ---------------------------------------------------------------------------
# Timing decorator
# ---------------------------------------------------------------------------

def log_time(func):
    """Decorator to log execution time of a function.

    The elapsed time is reported via :data:`logger` at ``INFO`` level.

    Parameters
    ----------
    func : callable
        Target function.

    Returns
    -------
    callable
        Wrapped function that logs runtime and returns the original result.

    Examples
    --------
    >>> @log_time
    ... def slow():
    ...     import time; time.sleep(0.01)
    ...
    ...
    >>> slow()  # doctest: +ELLIPSIS
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        logger.info(f"{func.__name__} completed in {duration:.3f}s")
        return result

    return wrapper


# ---------------------------------------------------------------------------
# NumPy dtype / array endianness helpers
# ---------------------------------------------------------------------------

def needs_swap_dtype(dt: np.dtype) -> bool:
    """Return ``True`` if any field of a dtype is non-native-endian.

    Works for both simple and structured dtypes. Fields with byteorder ``'|'``
    (not applicable) and ``'='`` (native) are ignored.

    Parameters
    ----------
    dt : numpy.dtype
        The dtype to test.

    Returns
    -------
    bool
        ``True`` if the dtype contains non-native-endian components, otherwise
        ``False``.
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

    The function is **idempotent**: passing an array already in native byte
    order returns either the same view or a shallow copy as permitted by NumPy.

    Parameters
    ----------
    arr : numpy.ndarray
        Array to normalize.

    Returns
    -------
    numpy.ndarray
        View with native endianness. Copies only when needed.

    Notes
    -----
    Compatible with NumPy < 2.0 and >= 2.0. Internally, the function relies on
    :func:`needs_swap_dtype` and safe ``byteswap`` usage.
    """
    dt = arr.dtype
    if not needs_swap_dtype(dt):
        return arr

    # Create a swapped copy (``inplace=False`` ensures original is preserved)
    swapped = arr.byteswap(inplace=False)

    # Try the modern API first; fall back to legacy behavior if necessary
    try:
        return swapped.view(dt.newbyteorder("="))
    except Exception:  # pragma: no cover - legacy NumPy fallback
        return swapped.newbyteorder("=")

