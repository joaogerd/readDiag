from __future__ import annotations

"""
Plotting helpers for readDiag
============================

Small, reusable helpers **specific to plotting**. General-purpose utilities
(logging, deprecations, dtype endianness) live in :mod:`readDiag.utils`.

Highlights
----------
- Python 3.10+ (uses ``|`` for unions and ``list[T]`` notation).
- Cartopy is optional; GeoPandas is preferred for a fast, offline basemap.
- Docstrings are in English; inline comments (PT-BR) explicam o raciocínio.

Examples
--------
Create a quick global basemap (Cartopy if available, fallback otherwise):

>>> import matplotlib.pyplot as plt
>>> from readDiag.plotting import make_axes
>>> ax, crs = make_axes(basemap=True)  # crs is None if not geo
>>> ax.set_title("Global view")
>>> plt.show()

Plot points over South America using GeoPandas fallback:

>>> from readDiag.plotting import ensure_axes_gpd
>>> ax = ensure_axes_gpd(ax=None, area=[-90, -60, -30, 15])
>>> ax.scatter([-60, -54], [-3, -23], s=10)
>>> ax.set_title("Two sample sites"); plt.show()

Color items consistently with a colormap:

>>> from readDiag.plotting import cmap_hex
>>> colors = [cmap_hex(i, total=5, cmap_name="Paired") for i in range(5)]
>>> len(set(colors)) == 5
True
"""

from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize, to_hex

# Cartopy é opcional (evita import pesado e dependências na instalação mínima)
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
        Array of longitudes (in degrees). The function is vectorized and
        accepts any numeric dtype; NaNs are preserved.
    mode : {"auto", "pm180", "360", "none"}, default: "auto"
        - ``"pm180"``: force range ``[-180, 180)``.
        - ``"360"``:   force range ``[0, 360)``.
        - ``"none"``:  return the input unchanged.
        - ``"auto"``:  if all finite values are ``>= 0`` and any ``> 180``,
          convert to ``[-180, 180)``; otherwise leave as-is.

    Returns
    -------
    numpy.ndarray
        Normalized longitude array. If no change is needed, this is a view
        of ``arr``; otherwise, a new array is returned.

    Notes
    -----
    - Idempotent: applying it twice yields the same values.
    - Works on masked arrays (mask preserved by NumPy operations).

    Examples
    --------
    >>> wrap_lon(np.array([0, 90, 270]), mode="pm180")
    array([  0.,  90., -90.])
    >>> wrap_lon(np.array([350, 10]), mode="auto")
    array([-10.,  10.])
    """
    # --- decisão pelo modo solicitado (PT-BR)
    if mode == "none":
        return arr
    if mode == "pm180":
        return ((arr + 180.0) % 360.0) - 180.0
    if mode == "360":
        return arr % 360.0
    if mode != "auto":
        raise ValueError(f"Unknown mode '{mode}'. Use 'auto', 'pm180', '360', or 'none'.")

    # --- "auto": detecta 0..360 e converte para [-180, 180) quando necessário (PT-BR)
    finite = np.isfinite(arr)
    if not finite.any():
        return arr
    lo = float(np.nanmin(arr[finite]))
    hi = float(np.nanmax(arr[finite]))
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
        Zero-based index of the item to color. If ``idx`` is out of range,
        it is clamped to ``[0, total-1]``.
    total : int
        Total number of items. Must be >= 1. Values are spread evenly across
        the colormap domain via linear normalization.
    cmap_name : str, default: "Paired"
        Matplotlib colormap name (e.g., ``"viridis"``, ``"tab10"``, ``"Paired"``).

    Returns
    -------
    str
        Hex color string (e.g., ``"#aabbcc"``).

    Raises
    ------
    ValueError
        If ``total < 1``.

    Examples
    --------
    >>> cmap_hex(2, total=5, cmap_name="tab10").startswith("#")
    True
    """
    # --- validação simples (PT-BR)
    if total < 1:
        raise ValueError("total must be >= 1")
    # Clampa índice para evitar exceções/cores fora do espectro (PT-BR)
    i = max(0, min(idx, total - 1))
    # Normaliza posição na paleta [0, 1] (PT-BR)
    norm = Normalize(vmin=0, vmax=max(1, total - 1))
    cmap = cm.get_cmap(cmap_name)
    return to_hex(cmap(norm(i)))


# ---------------------------------------------------------------------------
# Basemap helpers (GeoPandas rápido; Cartopy opcional)
# ---------------------------------------------------------------------------

def ensure_axes_gpd(
    ax: Optional[plt.Axes],
    area: Optional[Sequence[float]],
    world_path: Optional[str] = None,
) -> plt.Axes:
    """Return a regular ``Axes`` with an optional GeoPandas world basemap.

    Parameters
    ----------
    ax : matplotlib.axes.Axes or None
        Existing axes or ``None`` to create a new one.
    area : sequence of float, optional
        Bounding box ``[lon_min, lat_min, lon_max, lat_max]``. If omitted,
        defaults to global ``[-180, -90, 180, 90]``.
    world_path : str, optional
        Shapefile/GeoPackage path for world polygons. If not provided or
        loading fails, draw only a styled background (no polygons).

    Returns
    -------
    matplotlib.axes.Axes
        Axes ready for scatter/plot calls (non-geo).

    Notes
    -----
    - This is a **non-geo** axes: data are plotted in lon/lat directly.
    - Prefer this path when Cartopy is not installed or offline rendering
      is desired (no NaturalEarth downloads).

    Examples
    --------
    >>> ax = ensure_axes_gpd(None, [-90, -60, -30, 15])  # doctest: +SKIP
    >>> ax.scatter([-60], [-3])  # doctest: +SKIP
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

    # Com GeoPandas disponível (PT-BR)
    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))

    gdf = None
    if world_path:
        try:
            import geopandas as gpd
            # Leitura preguiçosa; GeoPackage e Shapefile são suportados (PT-BR)
            gdf = gpd.read_file(world_path)
        except Exception:
            gdf = None  # fallback abaixo

    if gdf is not None:
        # Polígonos rápidos sem projeção (lon/lat) (PT-BR)
        gdf.plot(ax=ax, facecolor="lightgrey", edgecolor="k", linewidth=0.5)
    else:
        # Fundo neutro com grade leve (PT-BR)
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
    area: Optional[Sequence[float]],
) -> tuple[plt.Axes, Any]:
    """Return a Cartopy GeoAxes in PlateCarree with basic features.

    Parameters
    ----------
    ax : matplotlib.axes.Axes or None
        Existing axes (replaced if non-geo) or ``None`` to create a new figure.
    area : sequence of float, optional
        Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.

    Returns
    -------
    (matplotlib.axes.Axes, cartopy.crs._CylindricalProjection)
        GeoAxes and the data CRS (PlateCarree).

    Raises
    ------
    RuntimeError
        If Cartopy is not available.

    Examples
    --------
    >>> # doctest: +SKIP
    >>> ax, crs = ensure_axes_cartopy(None, [-85, -60, -30, 15])
    >>> ax.scatter([-60], [-3], transform=crs)
    """
    # --- exige Cartopy para configurar GeoAxes (PT-BR)
    if not _HAS_CARTOPY:
        raise RuntimeError("Cartopy is not available. Install 'cartopy' to use this helper.")
    import cartopy.crs as ccrs, cartopy.feature as cfeature  # type: ignore

    if ax is None or not hasattr(ax, "projection"):
        fig = plt.figure(figsize=(12, 6)) if ax is None else ax.get_figure()
        if ax is not None:
            fig.delaxes(ax)  # remove axes não-geo (PT-BR)
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # Recursos básicos (PT-BR)
    ax.coastlines(resolution="110m", linewidth=0.5)
    ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.3)
    ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor="lightgrey", alpha=0.6)
    ax.gridlines(draw_labels=False, linestyle=":", alpha=0.4)

    if area:
        ax.set_extent([area[0], area[2], area[1], area[3]], crs=ccrs.PlateCarree())
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    return ax, ccrs.PlateCarree()


def make_axes(basemap: bool = True, resolution: str = "110m"):
    """Create axes for geographic scatter plots with a light basemap.

    Parameters
    ----------
    basemap : bool, default: True
        If ``True`` **and** Cartopy is available, create a GeoAxes with basemap.
        Otherwise, return the current pyplot axes (non-geo).
    resolution : {"110m", "50m", "10m"}, default: "110m"
        NaturalEarth scale for borders/land **if** Cartopy is used.

    Returns
    -------
    (matplotlib.axes.Axes, cartopy.crs._CylindricalProjection | None)
        Axes and CRS (``None`` if non-geo).

    Notes
    -----
    - Use the returned ``crs`` when plotting in GeoAxes:
      ``ax.scatter(lon, lat, transform=crs)``.
    - In non-geo mode, data are assumed to be lon/lat in axes units.

    Examples
    --------
    >>> ax, crs = make_axes(basemap=True)  # crs is None if Cartopy unavailable
    >>> hasattr(ax, "projection") or crs is None
    True
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

    # Fallback não-geo (PT-BR)
    ax = plt.gca()
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    return ax, None


def wrap_label(text: str, width: int = 30) -> str:
    """Wrap a string into fixed-length lines.

    Parameters
    ----------
    text : str
        Input label. ``None`` or empty string returns ``""``.
    width : int, default: 30
        Maximum number of characters per line; must be >= 1.

    Returns
    -------
    str
        Wrapped label with ``'\\n'`` separators.

    Raises
    ------
    ValueError
        If ``width < 1``.

    Examples
    --------
    >>> wrap_label("ABCDEFGHIJ", width=4)
    'ABCD\\nEFGH\\nIJ'
    """
    if not text:
        return ""
    if width < 1:
        raise ValueError("width must be >= 1")
    # --- quebra rótulos longos para caber na legenda (PT-BR)
    from textwrap import wrap as _wrap
    return "\n".join(_wrap(text, width))


# ---------------------------------------------------------------------------
# Backward-compatibility (deprecated) -----------------------------------------
# ---------------------------------------------------------------------------

def _deprecated_alias(new_name: str):
    """Return a callable that emits a DeprecationWarning.

    Notes
    -----
    Internal helper used to implement legacy function names during
    deprecation windows. Keep warnings short and explicit.
    """
    import warnings

    def _warn():
        warnings.warn(
            f"Use '{new_name}' instead of this deprecated helper; "
            "the alias will be removed in a future release.",
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
    area: Optional[Sequence[float]] = None,
    backend: str = "gpd",
) -> plt.Axes:
    """Deprecated convenience wrapper around Geo/Cartopy axes helpers.

    Parameters
    ----------
    ax : matplotlib.axes.Axes, optional
        Existing axes or ``None`` for a new one.
    area : sequence of float, optional
        Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.
    backend : {"gpd", "cartopy", "auto"}, default: "gpd"
        Prefer GeoPandas ("gpd") for speed/offline; "cartopy" for GeoAxes.
        "auto" tries Cartopy and falls back to GeoPandas.

    Returns
    -------
    matplotlib.axes.Axes
        Prepared axes (GeoAxes for Cartopy; regular Axes for GeoPandas).

    Notes
    -----
    This function is retained for compatibility and will be removed in a
    future major release. Prefer :func:`ensure_axes_gpd` or
    :func:`ensure_axes_cartopy`.

    Examples
    --------
    >>> # doctest: +SKIP
    >>> _draw_basemap(area=[-90, -60, -30, 15], backend="auto")
    """
    _deprecated_alias("ensure_axes_gpd / ensure_axes_cartopy")()

    # --- seleciona backend (PT-BR)
    use = backend
    if use == "auto":
        use = "cartopy" if _HAS_CARTOPY else "gpd"

    if use == "cartopy" and _HAS_CARTOPY:
        ax, _ = ensure_axes_cartopy(ax, area)
        return ax

    # fallback: GeoPandas/non-geo (PT-BR)
    return ensure_axes_gpd(ax, area, world_path=None)

