# src/readDiag/__init__.py
# =============================================================================
# readDiag public API (clean, no legacy glued inside this package)
#
# This module exposes a *stable* and minimal public surface for end users.
# It defers to internal subpackages (surface/, io/, plotting/) while keeping
# imports robust even when optional pieces are missing during development.
#
# Design goals
# ------------
# - Keep imports cheap and resilient (fail "late" on missing optional parts).
# - Provide a single canonical entry-point for opening diagnostics:
#       readDiag.open_diagnostic(path)  # -> DiagnosticAPI
# - Offer friendly plotting wrappers when available, but don't hard-require them.
# - Preserve a thin legacy export `diagAccess` for old scripts/tests.
# =============================================================================
from __future__ import annotations

from typing import Optional, Any

# -- Surface contract/adapter --------------------------------------------------
try:
    # Preferred adapter that normalizes backends to the high-level API.
    from .surface.access_adapter import AccessAdapter  # type: ignore[attr-defined]
except Exception as _e:  # noqa: N816  (keep external name)
    # Keep the module importable; raise at call sites if used.
    AccessAdapter = None  # type: ignore[assignment]

try:
    # Interface that concrete adapters must implement.
    from .surface.api import DiagnosticAPI  # type: ignore[attr-defined]
except Exception:
    # Fallback stub to keep type-checkers happy during partial trees.
    class DiagnosticAPI:  # type: ignore[no-redef]
        """Stub interface for development-time imports only."""
        ...

# -- Low-level opener (fallbacks) ---------------------------------------------
_open_impl: Optional[Any] = None
try:
    # Preferred: factory function
    from .io.reader import open_diagnostic as _open_impl  # type: ignore[attr-defined]
except Exception:
    pass

if _open_impl is None:
    try:
        # Alternate historical name
        from .io.reader import read_diag as _open_impl  # type: ignore[attr-defined]
    except Exception:
        pass

if _open_impl is None:
    try:
        # Last resort: wrap a diagAccess class into a callable
        from .io.reader import diagAccess  # type: ignore[attr-defined]

        def _open_impl(path: str):
            return diagAccess(path)
    except Exception:
        # If *nothing* can open a file, defer error to call time for clearer msg.
        def _open_impl(path: str):
            raise RuntimeError(
                "No opener found in readDiag.io.reader; expected one of: "
                "open_diagnostic(), read_diag(), or diagAccess"
            )

def open_diagnostic(path: str) -> "DiagnosticAPI":
    """Open a diagnostic file and return a high-level `DiagnosticAPI` handle.

    This function discovers an appropriate low-level backend using the most
    specific factory available (`io.reader.open_diagnostic`, then
    `io.reader.read_diag`, and finally a `diagAccess` class as a last resort),
    and then wraps the backend with :class:`AccessAdapter` to expose a consistent
    high-level surface.

    Parameters
    ----------
    path : str
        Path to a single diagnostic file. The concrete backend decides what
        formats are supported (e.g., GSI conventional, radiance, etc.).

    Returns
    -------
    DiagnosticAPI
        An object implementing the high-level diagnostic contract (e.g.,
        `.kind()`, `.variables()`, `.kx_list(var)`, `.frame_*()` methods, etc.).

    Raises
    ------
    RuntimeError
        If :class:`AccessAdapter` is not importable or no low-level opener can
        be found in :mod:`readDiag.io.reader`.

    Notes
    -----
    - Import errors for optional modules are *deferred* to this call to keep
      `import readDiag` lightweight and robust in partially-built trees.
    - The exact backend chosen is an implementation detail; rely on the
      `DiagnosticAPI` contract for stability.

    Examples
    --------
    Basic usage:

    >>> import readDiag as rd
    >>> h = rd.open_diagnostic("data/diag_conv_01.2024013018")   # doctest: +SKIP
    >>> h.kind()                                                 # doctest: +SKIP
    'conv'
    >>> vars = h.variables()                                     # doctest: +SKIP
    >>> 't' in vars                                              # doctest: +SKIP
    True

    Plotting with wrapper helpers (if installed):

    >>> from readDiag import plot_kx_count                       # doctest: +SKIP
    >>> plot_kx_count(h, var="t")                                # doctest: +SKIP
    """
    if AccessAdapter is None:
        raise RuntimeError(
            "AccessAdapter not available (readDiag.surface.access_adapter missing)"
        )
    backend = _open_impl(path)
    return AccessAdapter(backend)

# Friendly alias (kept for discoverability / historical usage).
read_diag = open_diagnostic

# -- Plotting (optional) -------------------------------------------------------
try:
    # Lower-level plotting helper, can be used directly when advanced control is needed.
    from .plotting.core import diagPlotter  # type: ignore[attr-defined]
except Exception:
    class diagPlotter:  # type: ignore[no-redef]
        """Stub plotting class placeholder."""
        ...

# Optional convenience wrappers (no legacy; just thin, user-friendly helpers).
try:
    from .plotting.wrappers import (  # type: ignore[attr-defined]
        plot_kx_count,
        plot_omf_map,
        plot_oma_map,
        plot_histogram_omf,
        plot_histogram_oma,
        plot_scatter,
    )
except Exception:
    # Keep the package importable even if wrappers are not present.
    def _missing(*args, **kwargs):
        """Raise a clear error when optional plotting wrappers are unavailable."""
        raise RuntimeError("Plot wrappers not available (readDiag.plotting.wrappers)")

    plot_kx_count = plot_omf_map = plot_oma_map = \
        plot_histogram_omf = plot_histogram_oma = plot_scatter = _missing  # type: ignore[misc]

__all__ = [
    "DiagnosticAPI",
    "open_diagnostic",
    "read_diag",
    "AccessAdapter",
    "diagPlotter",
    "plot_kx_count",
    "plot_omf_map",
    "plot_oma_map",
    "plot_histogram_omf",
    "plot_histogram_oma",
    "plot_scatter",
]

# -- Legacy export (deprecated): diagAccess for old tests/scripts --------------
# Rationale: some historical scripts (e.g., `import gsidiag as gd; gd.diagAccess`)
# still reach for this symbol. We re-export it to ease migrations while encouraging
# the modern `open_diagnostic()` path above.
try:
    from .io.reader import diagAccess as diagAccess  # type: ignore[attr-defined]
except Exception:
    pass
if "__all__" in globals() and "diagAccess" not in __all__:
    __all__.append("diagAccess")

# --- Version & environment diagnostics ---------------------------------------
try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError as _PkgNF

    try:
        __version__ = _pkg_version("readDiag")
    except _PkgNF:
        # In editable/dev installs without a proper package name.
        __version__ = "0.0.0.dev0"
except Exception:
    __version__ = "0.0.0.dev0"


def show_versions() -> None:
    """Print package and environment version information.

    This is a lightweight helper primarily for issue templates and user support.
    The output is intentionally short and single-line per field to simplify copy/paste.

    Examples
    --------
    >>> import readDiag as rd
    >>> rd.show_versions()  # doctest: +SKIP
    readDiag : 2.0.0rc3
    Python   : 3.11.9
    Platform : Linux-6.8.0-...-x86_64-with-glibc2.37
    """
    import sys
    import platform

    print(f"readDiag : {__version__}")
    print(f"Python   : {sys.version.split()[0]}")
    print(f"Platform : {platform.platform()}")

