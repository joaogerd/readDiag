# readDiag public API (clean, no legacy inside this package)

# -- Surface contract/adapter --
try:
    from .surface.access_adapter import AccessAdapter  # type: ignore
except Exception as _e:
    AccessAdapter = None  # type: ignore

try:
    from .surface.api import DiagnosticAPI  # type: ignore
except Exception:
    class DiagnosticAPI: ...  # type: ignore

# -- Low-level opener (fallbacks) --
_open_impl = None
try:
    # Preferred: a factory in io/reader.py
    from .io.reader import open_diagnostic as _open_impl  # type: ignore
except Exception:
    pass

if _open_impl is None:
    try:
        # Alt name some trees use
        from .io.reader import read_diag as _open_impl  # type: ignore
    except Exception:
        pass

if _open_impl is None:
    try:
        # Last-resort: build from diagAccess class
        from .io.reader import diagAccess  # type: ignore
        def _open_impl(path: str):
            return diagAccess(path)
    except Exception:
        # If nothing is available, make it explicit at call time
        def _open_impl(path: str):
            raise RuntimeError("No opener found in readDiag.io.reader; expected open_diagnostic/read_diag/diagAccess")

def open_diagnostic(path: str) -> "DiagnosticAPI":
    if AccessAdapter is None:
        raise RuntimeError("AccessAdapter not available (readDiag.surface.access_adapter missing)")
    backend = _open_impl(path)
    return AccessAdapter(backend)

# Friendly alias
read_diag = open_diagnostic

# -- Plotting --
try:
    from .plotting.core import diagPlotter  # type: ignore
except Exception:
    class diagPlotter: ...  # type: ignore

# Optional convenience wrappers (no legacy; just thin helpers)
try:
    from .plotting.wrappers import (
        plot_kx_count, plot_omf_map, plot_oma_map,
        plot_histogram_omf, plot_histogram_oma, plot_scatter,
    )  # type: ignore
except Exception:
    # Keep package importable even if wrappers are not present
    def _missing(*args, **kwargs):
        raise RuntimeError("Plot wrappers not available")
    plot_kx_count = plot_omf_map = plot_oma_map = \
    plot_histogram_omf = plot_histogram_oma = plot_scatter = _missing

__all__ = [
    "DiagnosticAPI","open_diagnostic","read_diag",
    "AccessAdapter","diagPlotter",
    "plot_kx_count","plot_omf_map","plot_oma_map",
    "plot_histogram_omf","plot_histogram_oma","plot_scatter",
]

# -- Legacy export (deprecated): diagAccess for old tests/scripts --
try:
    from .io.reader import diagAccess as diagAccess  # type: ignore
except Exception:
    pass
if "__all__" in globals():
    if "diagAccess" not in __all__:
        __all__.append("diagAccess")



# --- version & diagnostics ---
try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError as _PkgNF
    try:
        __version__ = _pkg_version("readDiag")
    except _PkgNF:
        __version__ = "0.0.0.dev0"
except Exception:
    __version__ = "0.0.0.dev0"

def show_versions():
    import sys, platform
    print(f"readDiag : {__version__}")
    print(f"Python   : {sys.version.split()[0]}")
    print(f"Platform : {platform.platform()}")
