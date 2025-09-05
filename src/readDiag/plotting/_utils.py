from __future__ import annotations

"""Plotting helpers for readDiag (NumPy-style docstrings).

This module centralizes small, reusable helpers that are **specific to plotting**.
General-purpose utilities (logging, deprecations, dtype endianness) remain in
:mod:`readDiag.utils`.

Notes
-----
- Designed for Python 3.10+ (uses ``|`` for unions and modern typing).
- Cartopy is optional; GeoPandas is preferred for a fast, offline basemap.
- Docstrings are in **English**; inline comments (PT-BR) explicam o passo a passo.
"""

from pathlib import Path
from typing import Any, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize, to_hex

# Cartopy é opcional
try:  # pragma: no cover
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    _HAS_CARTOPY = True
except Exception:  # pragma: no cover
    _HAS_CARTOPY = False

__all__ = [
    "wrap_lon",
    "cmap_hex",
    "ensure_axes_gpd",
    "ensure_axes_cartopy",
    "make_axes",
    "wrap_label",
]


# ---------------------------------------------------------------------------
# Longitude helpers
# ---------------------------------------------------------------------------

def wrap_lon(arr: np.ndarray, mode: str = "auto") -> np.ndarray:
    """Normalize longitudes to a consistent range.

    Parameters
    ----------
    arr : numpy.ndarray
        Array of longitudes.
    mode : {"auto", "pm180", "360", "none"}, default: "auto"
        * "pm180": force range [-180, 180)
        * "360":   force range [0, 360)
        * "none":  do not change
        * "auto":  if all >= 0 and any > 180, convert to [-180, 180)

    Returns
    -------
    numpy.ndarray
        Normalized longitude array (view if no change is needed).

    Notes
    -----
    Idempotent: applying twice yields the same values.
    """
    # --- decisão pelo modo solicitado (PT-BR)
    if mode == "none":
        return arr
    if mode == "pm180":
        return ((arr + 180.0) % 360.0) - 180.0
    if mode == "360":
        return arr % 360.0

    # --- "auto": detecta 0..360 e converte para [-180, 180) quando necessário (PT-BR)
    finite = np.isfinite(arr)
    if not finite.any():
        return arr
    lo, hi = np.nanmin(arr[finite]), np.nanmax(arr[finite])
    if lo >= 0.0 and hi > 180.0:
        return ((arr + 180.0) % 360.0) - 180.0
    return arr


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def cmap_hex(idx: int, total: int, cmap_name: str = "Paired") -> str:
    """Return a hex color from a discrete position in a colormap.

    Parameters
    ----------
    idx : int
        Zero-based index of the item to color.
    total : int
        Total number of items (used to spread colors evenly).
    cmap_name : str, default: "Paired"
        Matplotlib colormap name.

    Returns
    -------
    str
        Hex color string (e.g., "#aabbcc").
    """
    # --- normaliza a posição na paleta de cores (PT-BR)
    cmap = cm.get_cmap(cmap_name)
    return to_hex(cmap(Normalize(vmin=0, vmax=max(1, total - 1))(idx)))


# ---------------------------------------------------------------------------
# Basemap helpers (GeoPandas rápido; Cartopy opcional)
# ---------------------------------------------------------------------------

def ensure_axes_gpd(
    ax: Optional[plt.Axes],
    area: Optional[list[float]],
    world_path: Optional[str] = None,
) -> plt.Axes:
    """Return a regular Axes with an optional GeoPandas world basemap.

    Parameters
    ----------
    ax : matplotlib.axes.Axes or None
        Existing axes or ``None`` to create a new one.
    area : list of float, optional
        Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.
    world_path : str, optional
        Shapefile/GeoPackage path for world polygons. If not provided or fails,
        draw only a styled background (no polygons).

    Returns
    -------
    matplotlib.axes.Axes
        Axes ready for scatter/plot calls (non-geo).
    """
    # --- tenta carregar GeoPandas (PT-BR)
    try:
        import geopandas as gpd  # noqa: F401
    except Exception:
        # Sem GeoPandas → eixos simples, com grade (PT-BR)
        if ax is None:
            _, ax = plt.subplots(figsize=(12, 6))
        ax.set_facecolor("#f7f7f7")
        ax.grid(True, linestyle=":", alpha=0.35)
        ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
        if area:
            ax.set_xlim(area[0], area[2]); ax.set_ylim(area[1], area[3])
        else:
            ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
        return ax

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))

    gdf = None
    if world_path:
        try:
            import geopandas as gpd
            gdf = gpd.read_file(world_path)
        except Exception:
            gdf = None

    if gdf is not None:
        gdf.plot(ax=ax, facecolor="lightgrey", edgecolor="k", linewidth=0.5)
    else:
        ax.set_facecolor("#f7f7f7")
        ax.grid(True, linestyle=":", alpha=0.35)

    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    if area:
        ax.set_xlim(area[0], area[2]); ax.set_ylim(area[1], area[3])
    else:
        ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
    return ax


def ensure_axes_cartopy(
    ax: Optional[plt.Axes],
    area: Optional[list[float]],
) -> tuple[plt.Axes, Any]:
    """Return a Cartopy GeoAxes in PlateCarree with basic features.

    Parameters
    ----------
    ax : matplotlib.axes.Axes or None
        Existing axes (replaced if non-geo) or ``None``.
    area : list of float, optional
        Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.

    Returns
    -------
    (matplotlib.axes.Axes, cartopy.crs._CylindricalProjection)
        GeoAxes and the data CRS (PlateCarree).
    """
    # --- configura eixos do Cartopy com recursos básicos (PT-BR)
    import cartopy.crs as ccrs, cartopy.feature as cfeature  # type: ignore
    if ax is None or not hasattr(ax, "projection"):
        fig = plt.figure(figsize=(12, 6)) if ax is None else ax.get_figure()
        if ax is not None:
            fig.delaxes(ax)
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.coastlines(resolution="110m", linewidth=0.5)
    ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.3)
    ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor="lightgrey", alpha=0.6)
    ax.gridlines(draw_labels=False, linestyle=":", alpha=0.4)
    if area:
        ax.set_extent([area[0], area[2], area[1], area[3]], crs=ccrs.PlateCarree())
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    return ax, ccrs.PlateCarree()


def make_axes(basemap: bool = True, resolution: str = "110m"):
    """Create axes for geographic scatter plots.

    Parameters
    ----------
    basemap : bool, default: True
        If ``True`` and Cartopy is available, create a GeoAxes with basemap.
    resolution : {"110m", "50m", "10m"}, default: "110m"
        NaturalEarth scale for borders/land if Cartopy is used.

    Returns
    -------
    (matplotlib.axes.Axes, cartopy.crs._CylindricalProjection | None)
        Axes and CRS (``None`` if non-geo).
    """
    # --- tenta Cartopy se disponível e solicitado (PT-BR)
    if basemap and _HAS_CARTOPY:
        ax = plt.axes(projection=ccrs.PlateCarree())  # type: ignore
        ax.set_global()
        ax.gridlines(draw_labels=False, linestyle=":", alpha=0.4)
        ax.coastlines(resolution=resolution, linewidth=0.5)  # type: ignore
        ax.add_feature(cfeature.BORDERS.with_scale(resolution), linewidth=0.3)  # type: ignore
        ax.add_feature(cfeature.LAND.with_scale(resolution), facecolor="lightgray", alpha=0.6)  # type: ignore
        return ax, ccrs.PlateCarree()  # type: ignore
    ax = plt.gca()
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    return ax, None


def wrap_label(text: str, width: int = 30) -> str:
    """Wrap a string into fixed-length lines.

    Parameters
    ----------
    text : str
        Input label.
    width : int, default: 30
        Maximum number of characters per line.

    Returns
    -------
    str
        Wrapped label with ``'\\n'`` separators.
    """
    # --- quebra rótulos longos para caber na legenda (PT-BR)
    from textwrap import wrap
    return "\n".join(wrap(text, width))


# ---------------------------------------------------------------------------
# Backward-compatibility (deprecated) -----------------------------------------
# ---------------------------------------------------------------------------

def _deprecated_alias(new_name: str):
    import warnings

    def _warn():
        warnings.warn(
            f"'{new_name}' should be used instead of deprecated helper; "
            "this alias will be removed in a future release.",
            DeprecationWarning,
            stacklevel=3,
        )
    return _warn


def _make_axes(basemap: bool, resolution: str):
    """Deprecated alias for :func:`make_axes`."""
    _deprecated_alias("make_axes")()
    return make_axes(basemap=basemap, resolution=resolution)


def _get_cmap_color(idx: int, total: int, cmap_name: str = "Paired"):
    """Deprecated alias for :func:`cmap_hex`."""
    _deprecated_alias("cmap_hex")()
    return cmap_hex(idx, total, cmap_name)


def _wrap_label(text: str, width: int = 30) -> str:
    """Deprecated alias for :func:`wrap_label`."""
    _deprecated_alias("wrap_label")()
    return wrap_label(text, width)


def _draw_basemap(
    ax: Optional[plt.Axes] = None,
    area: Optional[list[float]] = None,
    backend: str = "gpd",
) -> plt.Axes:
    """Deprecated convenience wrapper around Geo/Cartopy axes helpers.

    Parameters
    ----------
    ax : matplotlib.axes.Axes, optional
        Existing axes or ``None`` for a new one.
    area : list of float, optional
        Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.
    backend : {"gpd", "cartopy", "auto"}, default: "gpd"
        Prefer GeoPandas ("gpd") for speed/offline; "cartopy" for GeoAxes.
        "auto" tries Cartopy and falls back to GeoPandas.

    Returns
    -------
    matplotlib.axes.Axes
        Prepared axes (GeoAxes for Cartopy; regular Axes for GeoPandas).
    """
    _deprecated_alias("ensure_axes_gpd / ensure_axes_cartopy")()

    # --- seleciona backend (PT-BR)
    use = backend
    if use == "auto":
        use = "cartopy" if _HAS_CARTOPY else "gpd"

    if use == "cartopy" and _HAS_CARTOPY:
        ax, _ = ensure_axes_cartopy(ax, area)
        return ax

    # fallback: GeoPandas
    return ensure_axes_gpd(ax, area, world_path=None)

