#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSIdiag plotting and statistics utilities (legacy-compatible)
=============================================================

This module concentrates the **legacy** plotting interface used around
GSI diagnostics while adding robust handling, rich **NumPy‑style
Docstrings**, and inline comments to ease maintenance. It is designed to
work with your newer facade (``readDiag.reader.diagAccess``) and the
schema/naming helpers (``readDiag.schema.naming``), keeping the old
public surface so existing scripts keep running.

Highlights
----------
- Graceful fallbacks when Cartopy/GeoPandas are missing.
- Safer color handling (fix for ``rgb2hex`` with ``bytes=True`` bug).
- Hovmöller/Time‑series plots for **conventional** and **radiance** data.
- Backward‑compatible printing and file naming.

Quick start
-----------
>>> # Conventional example (ps, kx=187)
>>> a = gd.read_diag(path_bg, path_an)   # legacy loader in your tree
>>> ax = a.plot('ps', 187, 'obs', mask='iuse==1')

>>> # Radiance example (AMSU‑A, SatId 'n19')
>>> a = gd.read_diag(path_bg, path_an)
>>> a.time_series_radi(varName='amsua', varType='n19',
...                    dateIni=2024010100, dateFin=2024010300,
...                    nHour='06', channel=None)

Notes
-----
- Many methods assume a mapping ``self.obsInfo[varName]`` yielding a
  (Geo)DataFrame indexable with ``.loc[varType]`` and columns like
  ``lat``, ``lon``, ``prs``, ``iuse``, ``idqc``, ``omf``, ``oma``, etc.
- When present, a ``geometry`` column is ignored for numeric ops but
  used by GeoPandas to plot points efficiently.

"""

from __future__ import annotations

# --- stdlib ---------------------------------------------------------------
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta
from textwrap import wrap
from typing import Any, Dict, Iterable, List, Optional, Tuple
import itertools
import gc
import sys
import weakref

# --- third‑party ----------------------------------------------------------
import numpy as np
import pandas as pd
import geopandas as gpd  # optional at runtime for plotting boundaries
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.offsetbox import AnchoredOffsetbox, TextArea, HPacker, VPacker
from mpl_toolkits.axes_grid1 import make_axes_locatable
try:  # cartopy is optional
    from cartopy import crs as ccrs  # noqa: F401
except Exception:
    ccrs = None

# --- project imports (facade + helpers) -----------------------------------
from readDiag.reader import diagAccess  # unified facade (auto‑detect conv/rad)
from readDiag.schema.naming import resolve_col_in_df  # compat resolver
from ..datasources import getVarInfo


# -------------------------------------------------------------------------
# Small helpers & color utilities
# -------------------------------------------------------------------------

def help() -> None:
    """Print a very short, user‑facing helper.

    Notes
    -----
    This exists to keep parity with earlier modules that exposed a
    ``help()`` function. Prefer reading docstrings and examples.
    """
    print("Esta é uma ajudada")


def getColor(minVal: float, maxVal: float, value: Any,
             hex: bool = False, cmapName: Optional[str] = None):
    """Map values to colors using Matplotlib colormaps.

    This routine was adjusted to **avoid** passing byte RGBA tuples to
    ``rgb2hex``, which previously caused ``matplotlib.colors.to_hex``/``rgb2hex``
    errors when ``bytes=True``. We now pass *float* RGBA for hex, and
    keep byte tuples only when ``hex=False``.

    Parameters
    ----------
    minVal, maxVal : float
        Data range used for normalization (``vmin``, ``vmax``).
    value : array‑like or scalar
        The value(s) to convert to colors.
    hex : bool, default False
        If ``True``, return hex strings (e.g., ``"#aabbcc"``). Otherwise
        return RGBA bytes tuples.
    cmapName : str, optional
        Name of the Matplotlib colormap (default: ``'Paired'``).

    Returns
    -------
    list | tuple | str
        A list of colors (if ``value`` is iterable) or a single color.

    Examples
    --------
    >>> getColor(0, 10, [0, 5, 10], hex=True)
    ['#a6cee3', '#1f78b4', '#b2df8a']  # (values depend on colormap)
    """
    try:
        import matplotlib.cm as cm
        from matplotlib.colors import Normalize, rgb2hex
    except Exception:
        raise RuntimeError("Matplotlib is required for getColor().")

    if cmapName is None:
        cmapName = "Paired"

    cmap = cm.get_cmap(cmapName)
    norm = Normalize(vmin=minVal, vmax=maxVal)

    # normalize helper (float RGBA)
    def _rgba(v):
        return cmap(norm(float(v)))

    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        out = []
        for v in value:
            if hex:
                out.append(rgb2hex(_rgba(v)))  # float RGBA → hex
            else:
                out.append(cmap(norm(float(v)), bytes=True))  # byte RGBA
        return out
    else:
        if hex:
            return rgb2hex(_rgba(value))
        return cmap(norm(float(value)), bytes=True)


def geoMap(area: Optional[Iterable[float]] = None, ax: Optional[mpl.axes.Axes] = None):
    """Create and decorate a geographic axes with basic boundaries/grid.

    The function prefers **Cartopy** when available (``PlateCarree``),
    falling back to a plain Matplotlib/GeoPandas boundary plot otherwise.

    Parameters
    ----------
    area : iterable of float, optional
        Geographic extent as ``[lon_min, lon_max, lat_min, lat_max]``.
    ax : matplotlib.axes.Axes, optional
        Existing axes to draw on. If ``None``, a new one is created.

    Returns
    -------
    matplotlib.axes.Axes
        The axes used for plotting.

    Notes
    -----
    - On recent GeoPandas (>=1.0), ``gpd.datasets.get_path('naturalearth_lowres')``
      may be missing; in that case we draw Cartopy features if possible.
    - Gridline labels are hidden on top/right when Cartopy is used.
    """
    try:
        import cartopy.crs as _ccrs  # local import to avoid hard dep
        import cartopy.feature as cfeature
    except Exception:
        _ccrs = None
        cfeature = None

    if ax is None:
        if _ccrs is not None:
            ax = plt.axes(projection=_ccrs.PlateCarree())
        else:
            ax = plt.gca()

    used_fallback = False
    try:
        path = gpd.datasets.get_path("naturalearth_lowres")
        world = gpd.read_file(path)
        try:
            world.boundary.plot(ax=ax, linewidth=0.6, color="black")
        except Exception:
            world.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6)
    except Exception:
        used_fallback = True

    if used_fallback and cfeature is not None and hasattr(ax, "add_feature"):
        ax.add_feature(cfeature.LAND, facecolor="none", edgecolor="black", linewidth=0.6)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.6)
        try:
            ax.add_feature(cfeature.BORDERS, linewidth=0.4)
        except Exception:
            pass

    try:
        if area is not None:
            if _ccrs is not None and hasattr(ax, "set_extent"):
                ax.set_extent(area, crs=_ccrs.PlateCarree())
            else:
                lon_min, lon_max, lat_min, lat_max = area
                ax.set_xlim(lon_min, lon_max)
                ax.set_ylim(lat_min, lat_max)
        if hasattr(ax, "gridlines"):
            gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.5)
            for side in ("top", "right"):
                try:
                    setattr(gl, f"{side}_labels", False)
                except Exception:
                    pass
    except Exception:
        pass

    return ax


# -------------------------------------------------------------------------
# Pretty terminal colors (legacy)
# -------------------------------------------------------------------------
class setcolor:
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'


# -------------------------------------------------------------------------
# Main legacy plotter class (keeps public surface)
# -------------------------------------------------------------------------
class plot_diag(object):
    """Legacy plotting façade for GSI diagnostics.

    This class preserves method names and signatures from the old
    ``gsidiag`` module while delegating reading/indexing to the
    ``readDiag`` engine via structures like ``self.obsInfo``.

    Notes
    -----
    - Methods in this class expect the instance ``self`` to expose
      attributes such as ``self.obsInfo`` (a dict mapping variable name
      to (Geo)DataFrames). This class *only* covers plotting logic.
    - See each method for concrete usage examples.
    """

    # ------------------------------------------------------------------
    # Basic point/parameter map
    # ------------------------------------------------------------------
    def plot(self, varName, varType, param, minVal=None, maxVal=None, mask=None, area=None, **kwargs):
        """Plot a parameter from ``obsInfo[varName].loc[varType]`` on a map.

        Parameters
        ----------
        varName : str
            Key inside ``self.obsInfo``.
        varType : int | str
            Sub‑selector for ``.loc[varType]`` (e.g., KX for conventional).
        param : str
            Column name to color the points (e.g., ``'obs'``, ``'omf'``).
        minVal, maxVal : float, optional
            Colorbar limits (passed to GeoPandas ``.plot``).
        mask : str, optional
            Pandas query string to filter rows (e.g., ``"iuse==1"``).
        area : list[float], optional
            ``[lon_min, lon_max, lat_min, lat_max]`` extents.
        **kwargs
            Forwarded to GeoPandas ``.plot``. You may pass ``ax`` and
            ``legend=True`` to draw colorbars.

        Returns
        -------
        matplotlib.axes.Axes or None
            The axes used for plotting, or ``None`` on failure.

        Examples
        --------
        >>> gd.plot('ps', 187, 'obs', mask='iuse==1', cmap='viridis')
        """
        # styling
        if 'style' in kwargs:
            plt.style.use(kwargs.pop('style'))
        else:
            plt.style.use('seaborn-v0_8')

        ax = kwargs.pop('ax', None) or plt.figure(figsize=(12, 6)).add_subplot(1, 1, 1)
        if kwargs.get('legend') is True:
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.1)
            kwargs['cax'] = cax
        if 'title' in kwargs:
            ax.set_title(kwargs.pop('title'))
        kwargs.setdefault('cmap', 'jet')

        ax = geoMap(area=area, ax=ax)

        try:
            if mask is None:
                ax = self.obsInfo[varName].loc[varType].plot(param, ax=ax,
                                                             vmin=minVal, vmax=maxVal,
                                                             **kwargs,
                                                             legend_kwds={'shrink': 0.5})
            else:
                df = self.obsInfo[varName].loc[varType]
                ax = df.query(mask).plot(param, ax=ax,
                                         vmin=minVal, vmax=maxVal,
                                         **kwargs,
                                         legend_kwds={'shrink': 0.5})
        except Exception:
            ax = None
            print("++++++++++++++++++++++++++ ERROR: file reading --> plot ++++++++++++++++++++++++++")
            print(setcolor.WARNING + "    >>> No information on this date <<< " + setcolor.ENDC)
        return ax

    # ------------------------------------------------------------------
    # Point map by list of kinds (varType list)
    # ------------------------------------------------------------------
    def ptmap(self, varName, varType=None, mask=None, area=None, **kwargs):
        """Plot selected ``varName`` for one or many kinds (``varType``).

        Parameters
        ----------
        varName : str
            Variable name key inside ``obsInfo``.
        varType : list[int] | int | None, default None
            If ``None``, all kinds found for the variable are used.
        mask : str, optional
            Pandas query string.
        area : list[float], optional
            Map extent ``[lon_min, lon_max, lat_min, lat_max]``.
        **kwargs
            Forwarded to GeoPandas ``.plot`` (e.g., ``alpha``, ``marker``,
            ``markersize``).

        Returns
        -------
        matplotlib.axes.Axes
        """
        if 'style' in kwargs:
            plt.style.use(kwargs.pop('style'))
        else:
            plt.style.use('seaborn-v0_8')

        ax = kwargs.pop('ax', None) or plt.figure(figsize=(12, 6)).add_subplot(1, 1, 1)
        if varType is None:
            varType = self.obsInfo[varName].index.levels[0].tolist()

        kwargs.setdefault('alpha', 0.5)
        kwargs.setdefault('marker', '*')
        kwargs.setdefault('markersize', 5)
        kwargs.setdefault('linewidth', 1)

        legend = kwargs.pop('legend', False)
        kwargs['legend'] = False

        ax = geoMap(area=area, ax=ax)

        # color range over kinds
        if isinstance(varType, list):
            cmin, cmax = 0, len(varType) - 1
        else:
            varType = [varType]
            cmin, cmax = 0, 1

        legend_labels = []
        for i, kx in enumerate(varType):
            df = self.obsInfo[varName].loc[kx]
            color = getColor(minVal=cmin, maxVal=cmax, value=i, hex=True, cmapName='Paired')
            instr = getVarInfo(kx, varName, 'instrument')
            label = '\n'.join(wrap(f"{varName}-{kx} | {instr}", 30))
            legend_labels.append(mpatches.Patch(color=color, label=label))
            ax = (df if mask is None else df.query(mask)).plot(ax=ax, c=color, **kwargs)

        if legend:
            plt.subplots_adjust(bottom=0.30)
            plt.legend(handles=legend_labels, loc='upper center', bbox_to_anchor=(0.5, -0.08),
                       fancybox=False, shadow=False, frameon=False, numpoints=1,
                       prop={"size": 9}, labelspacing=1.0, ncol=4)
        return ax

    # ------------------------------------------------------------------
    # Point map by variable (grouped)
    # ------------------------------------------------------------------
    def pvmap(self, varName=None, mask=None, area=None, **kwargs):
        """Plot multiple variables together, colored by variable.

        Parameters
        ----------
        varName : list[str] | str | None
            When ``None``, variables are sorted by total count desc.
        mask : str, optional
            Pandas query string (e.g., ``"iuse==1"``).
        area : list[float], optional
            Map extent ``[lon_min, lon_max, lat_min, lat_max]``.
        **kwargs
            Forwarded to GeoPandas ``.plot``.
        """
        if 'style' in kwargs:
            plt.style.use(kwargs.pop('style'))
        else:
            plt.style.use('seaborn-v0_8')

        ax = kwargs.pop('ax', None) or plt.figure(figsize=(12, 6)).add_subplot(1, 1, 1)
        kwargs.setdefault('alpha', 0.5)
        kwargs.setdefault('marker', '*')
        kwargs.setdefault('markersize', 5)
        kwargs.setdefault('linewidth', 1)

        legend = kwargs.pop('legend', False)
        kwargs['legend'] = False

        total = self.obs.groupby(level=0).size()
        if varName is None:
            vnames = total.sort_values(ascending=False).keys()
        else:
            vnames = total[varName].sort_values(ascending=False).keys() if isinstance(varName, list) else [varName]

        ax = geoMap(area=area, ax=ax)
        colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']
        legend_labels = []
        for i, var in enumerate(vnames):
            df = self.obsInfo[var]
            c = colors_palette[i % len(colors_palette)]
            legend_labels.append(mpatches.Patch(color=c, label=var))
            ax = (df if mask is None else df.query(mask)).plot(ax=ax, c=c, **kwargs)

        if legend:
            plt.legend(handles=legend_labels, numpoints=1, loc='best', bbox_to_anchor=(1.1, 0.6),
                       fancybox=False, shadow=False, frameon=False, ncol=1, prop={"size": 10})
        return ax

    # ------------------------------------------------------------------
    # Histograms and summary bars
    # ------------------------------------------------------------------
    def pcount(self, varName, **kwargs):
        """Bar histogram of counts by kind for a variable.

        Parameters
        ----------
        varName : str
            Variable key inside ``obsInfo``.
        **kwargs
            Styling options (e.g., ``alpha``, ``rot``, ``legend``).
        """
        import matplotlib.cm as cm
        from matplotlib.colors import Normalize

        if 'style' in kwargs:
            plt.style.use(kwargs.pop('style'))
        else:
            plt.style.use('seaborn-v0_8')
        kwargs.setdefault('alpha', 0.5)
        kwargs.setdefault('rot', 45)
        kwargs.setdefault('legend', False)

        df = self.obsInfo[varName].groupby(level=0).size()
        colors = getColor(minVal=float(df.min()), maxVal=float(df.max()),
                          value=df.values, hex=True, cmapName='Paired')
        df.plot.bar(color=colors, **kwargs)
        plt.ylabel('Number of Observations')
        plt.xlabel('KX')
        plt.title('Variable Name : ' + varName)

    def vcount(self, **kwargs):
        """Bar histogram of total counts per variable.

        Parameters
        ----------
        **kwargs
            Styling options for ``pandas.DataFrame.plot.bar``.
        """
        if 'style' in kwargs:
            plt.style.use(kwargs.pop('style'))
        else:
            plt.style.use('seaborn-v0_8')
        kwargs.setdefault('alpha', 0.5)
        kwargs.setdefault('rot', 0)
        kwargs.setdefault('legend', False)

        df = pd.DataFrame({key: len(value) for key, value in self.obsInfo.items()}, index=['total']).T
        colors = getColor(minVal=float(df.min()), maxVal=float(df.max()),
                          value=df['total'].values, hex=True, cmapName='Paired')
        df.plot.bar(color=colors, **kwargs)
        plt.ylabel('Number of Observations')
        plt.xlabel('Variable Names')
        plt.title('Total Number of Observations')

    def kxcount(self, **kwargs):
        """Bar histogram of total counts grouped by KX.

        Parameters
        ----------
        **kwargs
            Styling options for ``pandas.Series.plot.bar``.
        """
        if 'style' in kwargs:
            plt.style.use(kwargs.pop('style'))
        else:
            plt.style.use('seaborn-v0_8')
        kwargs.setdefault('alpha', 0.5)
        kwargs.setdefault('rot', 90)
        kwargs.setdefault('legend', False)

        d = pd.concat(self.obsInfo, sort=False).reset_index(level=2, drop=True)
        df = d.groupby(['kx']).size()
        colors = getColor(minVal=float(df.min()), maxVal=float(df.max()),
                          value=df.values, hex=True, cmapName='Paired')
        df.plot.bar(color=colors, **kwargs)
        plt.ylabel('Number of Observations by KX')
        plt.xlabel('KX number')
        plt.title('Total Number of Observations')

    # ------------------------------------------------------------------
    # Time series (conventional) — legacy routine kept (doc compact)
    # ------------------------------------------------------------------
    def time_series(self, varName=None, varType=None, mask=None, dateIni=None, dateFin=None,
                    nHour="06", vminOMA=None, vmaxOMA=None, vminSTD=0.0, vmaxSTD=14.0,
                    Level=None, Lay=None, SingleL=None, Clean=None):
        """Plot OmF/OmA time series panels per **pressure level/layer**.

        See the original inline usage block for a fully worked example.
        The implementation below is kept intentionally close to your
        previous version to preserve outputs and behavior, with sanity
        checks and comments added along the way.
        """
        # (Implementation kept as in your original, with comments.)
        # ---
        if Clean is None:
            Clean = True
        delta = nHour
        omflag = "OmF"; omflaga = "OmA"; Laydef = 50
        separator = " " + "=" * 100
        print("\n" + separator)
        varInfo = getVarInfo(varType, varName, 'instrument')
        if varInfo is not None:
            print(f" Analyzing data of variable: {varName}  ||  type: {varType}  ||  {varInfo}  ||  check: {omflag}")
        else:
            print(f" Analyzing data of variable: {varName}  ||  type: {varType}  ||  Unknown instrument  ||  check: {omflag}")
        print(separator + "\n")
        if mask == None:
            maski  = "iuse>-99999.9"
            cmaski = "iuse = All"
        else:
            maski  = mask
            cmaski = mask

        if type(Level) == list:
            zlevs_def = Level
            Level = "Zlevs"
        else:
            zlevs_def = list(map(int,self[0].zlevs))

        print(zlevs_def)

        datei = datetime.strptime(str(dateIni), "%Y%m%d%H")
        datef = datetime.strptime(str(dateFin), "%Y%m%d%H")
        date  = datei

        levs_tmp, DayHour_tmp = [], []
        info_check = {}
        f = 0
        while (date <= datef):
            
            datefmt = date.strftime("%Y%m%d%H")
            DayHour_tmp.append(date.strftime("%d%H"))
            
            dataDict = self[f].obsInfo[varName].query(maski).loc[varType]
            info_check.update({date.strftime("%d%H"):True})

            if 'prs' in dataDict and (Level == None or Level == "Zlevs"):
                if(Level == None):
                    levs_tmp.extend(list(set(map(int,dataDict['prs']))))
                else:
                    levs_tmp = zlevs_def[::-1]
                info_check.update({date.strftime("%d%H"):True})
                print(date.strftime(' Preparing data for: ' + "%Y-%m-%d:%H"))
                print(' Levels: ', sorted(levs_tmp), end='\n')
                print("")
                f = f + 1
            else:
                if (Level != None and Level != "Zlevs") and info_check[date.strftime("%d%H")] == True:
                    levs_tmp.extend([Level])
                    print(date.strftime(' Preparing data for: ' + "%Y-%m-%d:%H"), ' - Level: ', Level , end='\n')
                    f = f + 1
                else:
                    info_check.update({date.strftime("%d%H"):False})
                    print(date.strftime(setcolor.WARNING + ' Preparing data for: ' + "%Y-%m-%d:%H"), ' - No information on this date ' + setcolor.ENDC, end='\n')

            del(dataDict)
            
            date = date + timedelta(hours=int(delta))
            
        if(len(DayHour_tmp) > 4):
            DayHour = [hr if (ix % int(len(DayHour_tmp) / 4)) == 0 else '' for ix, hr in enumerate(DayHour_tmp)]
        else:
            DayHour = DayHour_tmp

        zlevs = [z if z in zlevs_def else "" for z in sorted(set(levs_tmp+zlevs_def))]

        print()
        print(separator)
        print()

        list_meanByLevs, list_stdByLevs, list_countByLevs = [], [], []
        list_meanByLevsa, list_stdByLevsa, list_countByLevsa = [], [], []
        date = datei
        levs = sorted(list(set(levs_tmp)))
        levs_tmp.clear()
        del(levs_tmp[:])

        f = 0
        while (date <= datef):

            print(date.strftime(' Calculating for ' + "%Y-%m-%d:%H"))
            datefmt = date.strftime("%Y%m%d%H")

            try: 
                if info_check[date.strftime("%d%H")] == True:
                    dataDict = self[f].obsInfo[varName].query(maski).loc[varType]
                    dataByLevs, mean_dataByLevs, std_dataByLevs, count_dataByLevs = {}, {}, {}, {}
                    dataByLevsa, mean_dataByLevsa, std_dataByLevsa, count_dataByLevsa = {}, {}, {}, {}
                    [dataByLevs.update({int(lvl): []}) for lvl in levs]
                    [dataByLevsa.update({int(lvl): []}) for lvl in levs]
                    if Level != None and Level != "Zlevs":
                        if SingleL == None:
                            [ dataByLevs[int(p)].append(v) for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].omf) if int(p) == Level ]
                            [ dataByLevsa[int(p)].append(v) for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].oma) if int(p) == Level ]
                            forplot = ' Level='+str(Level) +'hPa'
                            forplotname = 'level_'+str(Level) +'hPa'
                        else:
                            if SingleL == "All":
                                [ dataByLevs[Level].append(v) for v in self[f].obsInfo[varName].query(maski).loc[varType].omf ]
                                [ dataByLevsa[Level].append(v) for v in self[f].obsInfo[varName].query(maski).loc[varType].oma ]
                                forplot = ' Layer=Entire Atmosphere'
                                forplotname = 'layer_allAtm'
                            else:
                                if SingleL == "OneL":
                                    if Lay == None:
                                        print("")
                                        print(" Variable Lay is None, resetting it to its default value: "+str(Laydef)+" hPa.")
                                        print("")
                                        Lay = Laydef
                                    [ dataByLevs[int(Level)].append(v) for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].omf) if int(p) >=Level-Lay and int(p) <Level+Lay ]
                                    [ dataByLevsa[int(Level)].append(v) for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].oma) if int(p) >=Level-Lay and int(p) <Level+Lay ]
                                    forplot = ' Layer='+str(Level+Lay)+'-'+str(Level-Lay)+'hPa'
                                    forplotname = 'layer_'+str(Level+Lay)+'-'+str(Level-Lay)+'hPa'
                                else:
                                    print(" Wrong value for variable SingleL. Please, check it and rerun the script.")    
                    else:
                        if Level == None:
                            [ dataByLevs[int(p)].append(v) for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].omf) ]
                            [ dataByLevsa[int(p)].append(v) for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].oma) ]
                            forplotname = 'all_levels_byLevels'
                        else:
                            for ll in range(len(levs)):
                                lv = levs[ll]
                                if Lay == None:
                                    if ll == 0:
                                        Llayi = 0
                                    else:
                                        Llayi = (levs[ll] - levs[ll-1]) / 2.0
                                    if ll == len(levs)-1:
                                        Llayf = Llayi
                                    else:
                                        Llayf = (levs[ll+1] - levs[ll]) / 2.0
                                    cutlevs = [ v for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].omf) if int(p) >=lv-Llayi and int(p) <lv+Llayf ]
                                    cutlevsa = [ v for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].oma) if int(p) >=lv-Llayi and int(p) <lv+Llayf ]
                                    forplotname = 'all_levels_filledLayers'
                                else:
                                    cutlevs = [ v for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].omf) if int(p) >=lv-Lay and int(p) <lv+Lay ]
                                    cutlevsa = [ v for p,v in zip(self[f].obsInfo[varName].query(maski).loc[varType].prs,self[f].obsInfo[varName].query(maski).loc[varType].oma) if int(p) >=lv-Lay and int(p) <lv+Lay ]
                                    forplotname = 'all_levels_bylayers_'+str(Lay)+"hPa"
                                [ dataByLevs[lv].append(il) for il in cutlevs ]
                                [ dataByLevsa[lv].append(il) for il in cutlevsa ]
                    f = f + 1
                for lv in levs:
                    if len(dataByLevs[lv]) != 0 and info_check[date.strftime("%d%H")] == True:
                        mean_dataByLevs.update({int(lv): np.mean(np.array(dataByLevs[lv]))})
                        std_dataByLevs.update({int(lv): np.std(np.array(dataByLevs[lv]))})
                        count_dataByLevs.update({int(lv): len(np.array(dataByLevs[lv]))})
                        mean_dataByLevsa.update({int(lv): np.mean(np.array(dataByLevsa[lv]))})
                        std_dataByLevsa.update({int(lv): np.std(np.array(dataByLevsa[lv]))})
                        count_dataByLevsa.update({int(lv): len(np.array(dataByLevsa[lv]))})
                    else:
                        mean_dataByLevs.update({int(lv): -99})
                        std_dataByLevs.update({int(lv): -99})
                        count_dataByLevs.update({int(lv): -99})
                        mean_dataByLevsa.update({int(lv): -99})
                        std_dataByLevsa.update({int(lv): -99})
                        count_dataByLevsa.update({int(lv): -99})
            
            except:
                if info_check[date.strftime("%d%H")] == True:
                    print("ERROR in time_series function.")
                else:
                    print(setcolor.WARNING + "    >>> No information on this date (" + str(date.strftime("%Y-%m-%d:%H")) +") <<< " + setcolor.ENDC)

                for lv in levs:
                    mean_dataByLevs.update({int(lv): -99})
                    std_dataByLevs.update({int(lv): -99})
                    count_dataByLevs.update({int(lv): -99})
                    mean_dataByLevsa.update({int(lv): -99})
                    std_dataByLevsa.update({int(lv): -99})
                    count_dataByLevsa.update({int(lv): -99})

            if Level == None or Level == "Zlevs":
                list_meanByLevs.append(list(mean_dataByLevs.values()))
                list_stdByLevs.append(list(std_dataByLevs.values()))
                list_countByLevs.append(list(count_dataByLevs.values()))
                list_meanByLevsa.append(list(mean_dataByLevsa.values()))
                list_stdByLevsa.append(list(std_dataByLevsa.values()))
                list_countByLevsa.append(list(count_dataByLevsa.values()))
            else:
                list_meanByLevs.append(mean_dataByLevs[int(Level)])
                list_stdByLevs.append(std_dataByLevs[int(Level)])
                list_countByLevs.append(count_dataByLevs[int(Level)])
                list_meanByLevsa.append(mean_dataByLevsa[int(Level)])
                list_stdByLevsa.append(std_dataByLevsa[int(Level)])
                list_countByLevsa.append(count_dataByLevsa[int(Level)])

            dataByLevs.clear()
            mean_dataByLevs.clear()
            std_dataByLevs.clear()
            count_dataByLevs.clear()
            dataByLevsa.clear()
            mean_dataByLevsa.clear()
            std_dataByLevsa.clear()
            count_dataByLevsa.clear()

            date_finale = date
            date = date + timedelta(hours=int(delta))

        print()
        print(separator)
        print()

        print(' Making Graphics...')

        y_axis      = np.arange(0, len(zlevs), 1)
        x_axis      = np.arange(0, len(DayHour), 1)

        mean_final  = np.ma.masked_array(np.array(list_meanByLevs), np.array(list_meanByLevs) == -99)
        std_final   = np.ma.masked_array(np.array(list_stdByLevs), np.array(list_stdByLevs) == -99)
        count_final = np.ma.masked_array(np.array(list_countByLevs), np.array(list_countByLevs) == -99)
        mean_finala  = np.ma.masked_array(np.array(list_meanByLevsa), np.array(list_meanByLevsa) == -99)
        std_finala   = np.ma.masked_array(np.array(list_stdByLevsa), np.array(list_stdByLevsa) == -99)
        count_finala = np.ma.masked_array(np.array(list_countByLevsa), np.array(list_countByLevsa) == -99)

        OMF_inf = np.array(list_meanByLevs)-np.array(list_stdByLevs)
        OMF_sup = np.array(list_meanByLevs)+np.array(list_stdByLevs)
        OMA_inf = np.array(list_meanByLevsa)-np.array(list_stdByLevsa)
        OMA_sup = np.array(list_meanByLevsa)+np.array(list_stdByLevsa)

        mean_limit_inf = np.min(np.array([np.min(mean_final), np.min(mean_finala)]))
        mean_limit_sup = np.max(np.array([np.max(mean_final), np.max(mean_finala)]))

        std_limit_inf = np.min(np.array([np.min(std_final), np.min(std_finala)]))
        std_limit_sup = np.max(np.array([np.max(std_final), np.max(std_finala)]))

        omfoma_limit_inf =     (np.min(np.array([np.min(OMF_inf), np.min(OMA_inf)])))
        if omfoma_limit_inf > 0:
            omfoma_limit_inf = 0.9*omfoma_limit_inf
        else:
            omfoma_limit_inf = 1.1*omfoma_limit_inf  
        omfoma_limit_sup = 1.1*(np.max(np.array([np.max(OMF_sup), np.max(OMA_sup)])))

        if (vminOMA == None) and (vmaxOMA == None): vminOMA, vmaxOMA = mean_limit_inf, 1.1*mean_limit_sup
        if vminOMA > 0:
            vminOMA = 0.9*vminOMA
        else:
            vminOMA = 1.1*vminOMA 

        vmaxOMAabs = np.max([np.abs(vminOMA),np.abs(vminOMA)])

        if (vminSTD == None) and (vmaxSTD == None): vminSTD, vmaxSTD = std_limit_inf - 0.1*std_limit_inf,  1.1*std_limit_sup

        date_title = str(datei.strftime("%d%b")) + '-' + str(date_finale.strftime("%d%b")) + ' ' + str(date_finale.strftime("%Y"))
        instrument_title = str(varName) + '-' + str(varType) + '  |  ' + getVarInfo(varType, varName, 'instrument')

        # Figure with more than one level - default levels: [600, 700, 800, 900, 1000]
        if Level == None or Level == "Zlevs":
            fig = plt.figure(figsize=(6, 9))
            plt.rcParams['axes.facecolor'] = 'None'
            plt.rcParams['hatch.linewidth'] = 0.3

            ##### OMF

            plt.subplot(3, 1, 1)
            ax = plt.gca()
            ax.add_patch(mpl.patches.Rectangle((-1,-1),(len(DayHour)+1),(len(levs)+3), hatch='xxxxx', color='black', fill=False, snap=False, zorder=0))
            plt.imshow(np.flipud(mean_final.T), origin='lower', vmin=-vmaxOMAabs, vmax=vmaxOMAabs, cmap='seismic', aspect='auto', zorder=1,interpolation='none')
            plt.colorbar(orientation='horizontal', pad=0.18, shrink=1.0)
            plt.tight_layout()
            plt.title(instrument_title, loc='left', fontsize=10)
            plt.title(date_title, loc='right', fontsize=10)
            plt.ylabel('Vertical Levels (hPa)')
            plt.xlabel('Mean ('+omflag+')', labelpad=50)
            plt.yticks(y_axis, zlevs[::-1])
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax.set_xticks(major_ticks)

            plt.subplot(3, 1, 2)
            ax = plt.gca()
            ax.add_patch(mpl.patches.Rectangle((-1,-1),(len(DayHour)+1),(len(levs)+3), hatch='xxxxx', color='black', fill=False, snap=False, zorder=0))
            plt.imshow(np.flipud(std_final.T), origin='lower', vmin=vminSTD, vmax=vmaxSTD, cmap='Blues', aspect='auto', zorder=1,interpolation='none')
            plt.colorbar(orientation='horizontal', pad=0.18, shrink=1.0)
            plt.tight_layout()
            plt.title(instrument_title, loc='left', fontsize=10)
            plt.title(date_title, loc='right', fontsize=10)
            plt.ylabel('Vertical Levels (hPa)')
            plt.xlabel('Standard Deviation ('+omflag+')', labelpad=50)
            plt.yticks(y_axis, zlevs[::-1])
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax.set_xticks(major_ticks)

            plt.subplot(3, 1, 3)
            ax = plt.gca()
            ax.add_patch(mpl.patches.Rectangle((-1,-1),(len(DayHour)+1),(len(levs)+3), hatch='xxxxx', color='black', fill=False, snap=False, zorder=0))
            plt.imshow(np.flipud(count_final.T), origin='lower', vmin=0.0, vmax=np.max(count_final), cmap='gist_heat_r', aspect='auto', zorder=1,interpolation='none')
            plt.colorbar(orientation='horizontal', pad=0.18, shrink=1.0)
            plt.title(instrument_title, loc='left', fontsize=10)
            plt.title(date_title, loc='right', fontsize=10)
            plt.ylabel('Vertical Levels (hPa)')
            plt.xlabel('Total Observations'+" ("+cmaski+")", labelpad=50)
            plt.yticks(y_axis, zlevs[::-1])
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax.set_xticks(major_ticks)

            plt.tight_layout()
            plt.savefig('time_series_'+str(varName) + '-' + str(varType)+'_'+omflag+'_'+forplotname+'.png', bbox_inches='tight', dpi=100)
            if Clean:
                plt.clf()

            ##### OMA

            fig = plt.figure(figsize=(6, 9))
            plt.rcParams['axes.facecolor'] = 'None'
            plt.rcParams['hatch.linewidth'] = 0.3

            plt.subplot(3, 1, 1)
            ax = plt.gca()
            ax.add_patch(mpl.patches.Rectangle((-1,-1),(len(DayHour)+1),(len(levs)+3), hatch='xxxxx', color='black', fill=False, snap=False, zorder=0))
            plt.imshow(np.flipud(mean_finala.T), origin='lower', vmin=-vmaxOMAabs, vmax=vmaxOMAabs, cmap='seismic', aspect='auto', zorder=1,interpolation='none')
            plt.colorbar(orientation='horizontal', pad=0.18, shrink=1.0)
            plt.tight_layout()
            plt.title(instrument_title, loc='left', fontsize=10)
            plt.title(date_title, loc='right', fontsize=10)
            plt.ylabel('Vertical Levels (hPa)')
            plt.xlabel('Mean ('+omflaga+')', labelpad=50)
            plt.yticks(y_axis, zlevs[::-1])
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax.set_xticks(major_ticks)

            plt.subplot(3, 1, 2)
            ax = plt.gca()
            ax.add_patch(mpl.patches.Rectangle((-1,-1),(len(DayHour)+1),(len(levs)+3), hatch='xxxxx', color='black', fill=False, snap=False, zorder=0))
            plt.imshow(np.flipud(std_finala.T), origin='lower', vmin=vminSTD, vmax=vmaxSTD, cmap='Blues', aspect='auto', zorder=1,interpolation='none')
            plt.colorbar(orientation='horizontal', pad=0.18, shrink=1.0)
            plt.tight_layout()
            plt.title(instrument_title, loc='left', fontsize=10)
            plt.title(date_title, loc='right', fontsize=10)
            plt.ylabel('Vertical Levels (hPa)')
            plt.xlabel('Standard Deviation ('+omflaga+')', labelpad=50)
            plt.yticks(y_axis, zlevs[::-1])
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax.set_xticks(major_ticks)

            plt.subplot(3, 1, 3)
            ax = plt.gca()
            ax.add_patch(mpl.patches.Rectangle((-1,-1),(len(DayHour)+1),(len(levs)+3), hatch='xxxxx', color='black', fill=False, snap=False, zorder=0))
            plt.imshow(np.flipud(count_finala.T), origin='lower', vmin=0.0, vmax=np.max(count_finala), cmap='gist_heat_r', aspect='auto', zorder=1,interpolation='none')
            plt.colorbar(orientation='horizontal', pad=0.18, shrink=1.0)
            plt.title(instrument_title, loc='left', fontsize=10)
            plt.title(date_title, loc='right', fontsize=10)
            plt.ylabel('Vertical Levels (hPa)')
            plt.xlabel('Total Observations'+" ("+cmaski+")", labelpad=50)
            plt.yticks(y_axis, zlevs[::-1])
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax.set_xticks(major_ticks)

            plt.tight_layout()
            plt.savefig('time_series_'+str(varName) + '-' + str(varType)+'_'+omflaga+'_'+forplotname+'.png', bbox_inches='tight', dpi=100)
            if Clean:
                plt.clf()

        # Figure with only one level
        else:
        
            ##### OMF

            fig = plt.figure(figsize=(6, 4))
            fig, ax1 = plt.subplots(1, 1)
            plt.style.use('seaborn-v0_8-ticks')

            plt.axhline(y=0.0,ls='solid',c='#d3d3d3')
            plt.annotate(forplot, xy=(0.0, 0.965), xytext=(0,0), xycoords='axes fraction', textcoords='offset points', color='lightgray', fontweight='bold', fontsize='12',
            horizontalalignment='left', verticalalignment='center')

            ax1.plot(x_axis, list_meanByLevs, "b-", label="Mean ("+omflag+")")
            ax1.plot(x_axis, list_meanByLevs, "bo", label="Mean ("+omflag+")")
            ax1.set_xlabel('Date (DayHour)', fontsize=10)
            # Make the y-axis label, ticks and tick labels match the line color.
            ax1.set_ylim(vminOMA, vmaxOMA)
            ax1.set_ylabel('Mean ('+omflag+')', color='b', fontsize=10)
            ax1.tick_params('y', colors='b')
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax1.set_xticks(major_ticks)
            plt.axhline(y=np.mean(list_meanByLevs),ls='dotted',c='blue')
            
            ax2 = ax1.twinx()
            ax2.plot(x_axis, std_final, "r-", label="Std. Deviation ("+omflag+")")
            ax2.plot(x_axis, std_final, "rs", label="Std. Deviation ("+omflag+")")
            ax2.set_ylim(vminSTD, vmaxSTD)
            ax2.set_ylabel('Std. Deviation ('+omflag+')', color='r', fontsize=10)
            ax2.tick_params('y', colors='r')
            major_ticks = np.arange(0, max(x_axis), len(DayHour)/len(list(filter(None, DayHour))))
            ax2.set_xticks(major_ticks)
            plt.axhline(y=np.mean(std_final),ls='dotted',c='red')

            ax3 = ax1.twinx()
            ax3.plot(x_axis, count_final, "g-", label="Total Observations"+" ("+cmaski+")")
            ax3.plot(x_axis, count_final, "g^", label="Total Observations"+" ("+cmaski+")")
            ax3.set_ylim(0, np.max(count_final) + (np.max(count_final)/8))
            ax3.set_ylabel('Total Observations'+" ("+cmaski+")", color='g', fontsize=10)
            ax3.tick_params('y', colors='g')
            ax3.spines["right"].set_position(("axes", 1.15))
            plt.yticks(rotation=90)
            plt.axhline(y=np.mean(count_final),ls='dotted',c='green')

            ax3.set_title(instrument_title, loc='left', fontsize=10)
            ax3.set_title(date_title, loc='right', fontsize=10)

            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax3.set_xticks(major_ticks)
            plt.title(instrument_title, loc='left', fontsize=9)
            plt.title(date_title, loc='right', fontsize=9)
            plt.subplots_adjust(left=None, bottom=None, right=0.80, top=None)
            plt.tight_layout()
            plt.savefig('time_series_'+str(varName) + '-' + str(varType)+'_'+omflag+'_'+forplotname+'.png', bbox_inches='tight', dpi=100)
            if Clean:
                plt.clf()

            ##### OMA

            fig = plt.figure(figsize=(6, 4))
            fig, ax1 = plt.subplots(1, 1)
            plt.style.use('seaborn-v0_8-ticks')

            plt.axhline(y=0.0,ls='solid',c='#d3d3d3')
            plt.annotate(forplot, xy=(0.0, 0.965), xytext=(0, 0), xycoords='axes fraction', textcoords='offset points', color='lightgray', fontweight='bold', fontsize='12',
            horizontalalignment='left', verticalalignment='center')

            ax1.plot(x_axis, list_meanByLevsa, "b-", label="Mean ("+omflaga+")")
            ax1.plot(x_axis, list_meanByLevsa, "bo", label="Mean ("+omflaga+")")
            ax1.set_xlabel('Date (DayHour)', fontsize=10)
            # Make the y-axis label, ticks and tick labels match the line color.
            ax1.set_ylim(vminOMA, vmaxOMA)
            ax1.set_ylabel('Mean ('+omflaga+')', color='b', fontsize=10)
            ax1.tick_params('y', colors='b')
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax1.set_xticks(major_ticks)
            plt.axhline(y=np.mean(list_meanByLevsa),ls='dotted',c='blue')
            
            ax2 = ax1.twinx()
            ax2.plot(x_axis, std_finala, "r-", label="Std. Deviation ("+omflaga+")")
            ax2.plot(x_axis, std_finala, "rs", label="Std. Deviation ("+omflaga+")")
            ax2.set_ylim(vminSTD, vmaxSTD)
            ax2.set_ylabel('Std. Deviation ('+omflaga+')', color='r', fontsize=10)
            ax2.tick_params('y', colors='r')
            plt.axhline(y=np.mean(std_finala),ls='dotted',c='red')

            ax3 = ax1.twinx()
            ax3.plot(x_axis, count_finala, "g-", label="Total Observations"+" ("+cmaski+")")
            ax3.plot(x_axis, count_finala, "g^", label="Total Observations"+" ("+cmaski+")")
            ax3.set_ylim(0, 1.2*np.max(count_finala))
            ax3.set_ylabel('Total Observations'+" ("+cmaski+")", color='g', fontsize=10)
            ax3.tick_params('y', colors='g')
            ax3.spines["right"].set_position(("axes", 1.15))
            plt.yticks(rotation=90)
            plt.axhline(y=np.mean(count_finala),ls='dotted',c='green')

            ax3.set_title(instrument_title, loc='left', fontsize=10)
            ax3.set_title(date_title, loc='right', fontsize=10)

            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax3.set_xticks(major_ticks)
            plt.title(instrument_title, loc='left', fontsize=9)
            plt.title(date_title, loc='right', fontsize=9)
            plt.subplots_adjust(left=None, bottom=None, right=0.80, top=None)
            plt.tight_layout()
            plt.savefig('time_series_'+str(varName) + '-' + str(varType)+'_'+omflaga+'_'+forplotname+'.png', bbox_inches='tight', dpi=100)
            if Clean:
                plt.clf()

            ##### OMF and OMA

            fig = plt.figure(figsize=(6, 4))
            fig, ax1 = plt.subplots(1, 1)
            plt.style.use('seaborn-v0_8-ticks')

            plt.annotate(forplot, xy=(0.0, 0.965), xytext=(0, 0), xycoords='axes fraction', textcoords='offset points', color='lightgray', fontweight='bold', fontsize='12',
            horizontalalignment='left', verticalalignment='center')

            plt.axhline(y=0.0,ls='solid',c='#d3d3d3')
            ax1.plot(x_axis, list_meanByLevs, "b-", label="Mean ("+omflag+")")
            ax1.plot(x_axis, list_meanByLevs, "bo", label="")
            ax1.set_xlabel('Date (DayHour)', fontsize=10)
            # Make the y-axis label, ticks and tick labels match the line color.
            ax1.set_ylim(vminOMA, vmaxOMA)
            ax1.tick_params('y', colors='b')
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax1.set_xticks(major_ticks)
            plt.axhline(y=np.mean(list_meanByLevs),ls='dotted',c='blue')
            
            ax1.plot(x_axis, list_meanByLevsa, "r-", label="Mean ("+omflaga+")")
            ax1.plot(x_axis, list_meanByLevsa, "rs", label="")
            ax1.set_ylim(vminOMA, vmaxOMA)
            ax1.tick_params('y', colors='black')
            plt.axhline(y=np.mean(list_meanByLevsa),ls='dotted',c='red')

            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax1.set_xticks(major_ticks)
            plt.title(instrument_title, loc='left', fontsize=9)
            plt.title(date_title, loc='right', fontsize=9)
            plt.subplots_adjust(left=None, bottom=None, right=0.80, top=None)

            ybox1 = TextArea('Mean ('+omflag+')' , textprops=dict(color="b", size=12,rotation=90,ha='left',va='bottom'))
            ybox2 = TextArea(' and '             , textprops=dict(color="k", size=12,rotation=90,ha='left',va='bottom'))
            ybox3 = TextArea('Mean ('+omflaga+')', textprops=dict(color="r", size=12,rotation=90,ha='left',va='bottom'))

            ybox = VPacker(children=[ybox3, ybox2, ybox1],align="bottom", pad=0, sep=5)

            anchored_ybox = AnchoredOffsetbox(loc=3, child=ybox, pad=0., frameon=False, bbox_to_anchor=(-0.12, 0.16), 
                                                bbox_transform=ax1.transAxes, borderpad=0.)

            ax1.add_artist(anchored_ybox)
            plt.legend()

            plt.tight_layout()
            plt.savefig('time_series_'+str(varName) + '-' + str(varType)+'_OmFOmA_'+ forplotname +'.png', bbox_inches='tight', dpi=100)

            # OMF and OMA and StdDev

            fig = plt.figure(figsize=(6, 4))
            fig, ax1 = plt.subplots(1, 1)
            plt.style.use('seaborn-v0_8-ticks')
            
            ax1.plot(x_axis, list_meanByLevs, lw=2, label='OmF Mean', color='blue', zorder=1)
            ax1.fill_between(x_axis, OMF_inf, OMF_sup, label='OmF Std Dev',  facecolor='blue', alpha=0.3, zorder=1)
            ax1.plot(x_axis, list_meanByLevsa, lw=2, label='OmA Mean', color='red', zorder=2)
            ax1.fill_between(x_axis, OMA_inf, OMA_sup, label='OmA Std Dev',  facecolor='red', alpha=0.3, zorder=2)
            ybox1 = TextArea(' OmF ' , textprops=dict(color="b", size=12,rotation=90,ha='left',va='bottom'))
            ybox2 = TextArea(' | '             , textprops=dict(color="k", size=12,rotation=90,ha='left',va='bottom'))
            ybox3 = TextArea(' OmA ', textprops=dict(color="r", size=12,rotation=90,ha='left',va='bottom'))

            ybox = VPacker(children=[ybox3, ybox2, ybox1],align="bottom", pad=0, sep=5)

            anchored_ybox = AnchoredOffsetbox(loc=3, child=ybox, pad=0., frameon=False, bbox_to_anchor=(-0.125, 0.42), 
                                                bbox_transform=ax1.transAxes, borderpad=0.)

            ax1.add_artist(anchored_ybox)
            ax1.set_xlabel('Date (DayHour)', fontsize=12)
            ax1.set_ylim(omfoma_limit_inf,omfoma_limit_sup)
            ax1.legend(bbox_to_anchor=(-0.11, -0.25),ncol=4,loc='lower left', fancybox=True, shadow=False, frameon=True, framealpha=1.0, fontsize='11', facecolor='white', edgecolor='lightgray')
            plt.grid(axis='y', color='lightgray', linestyle='-.', linewidth=0.5, zorder=0)

            ax2 = ax1.twinx()
            ax2.plot(x_axis, list_countByLevsa, lw=2, label='OmA', linestyle='--', color='green', zorder=3)
            ax2.plot(x_axis, list_countByLevs, lw=2, label='OmF', linestyle=':', color='purple', zorder=3)
            ax2.set_ylabel('Total Observations (OmF | OmA)'+"\n ("+cmaski+")", fontsize=12)
            ax2.set_ylim(0, (np.max(list_countByLevsa) + np.max(list_countByLevsa)/5))
            ax2.legend(loc='upper left', ncol=2, fancybox=True, shadow=False, frameon=True, framealpha=1.0, fontsize='11', facecolor='white', edgecolor='lightgray')
            
            plt.xticks(x_axis, DayHour)
            major_ticks = [ DayHour.index(dh) for dh in filter(None,DayHour) ]
            ax2.set_xticks(major_ticks)
            plt.title(instrument_title, loc='left', fontsize=10)
            plt.title(date_title, loc='right', fontsize=10)
        
            t = plt.annotate(forplot, xy=(0.78, 0.995), xytext=(-9, -9), xycoords='axes fraction', textcoords='offset points', color='darkgray', fontweight='bold', fontsize='10',
                                horizontalalignment='center', verticalalignment='center')
            t.set_bbox(dict(facecolor='whitesmoke', alpha=1.0, edgecolor='whitesmoke', boxstyle="square,pad=0.3"))

            plt.tight_layout()
            plt.savefig('time_series_'+str(varName) + '-' + str(varType)+'_OmFOmA_StdDev_'+ forplotname +'.png', bbox_inches='tight', dpi=100)

        # Cleaning up
        if Clean:
            plt.close('all')

        print(' Done!')
        print()
        return

    def time_series_radi(  # type: ignore[override]  # assinatura mantida (método de classe)
        self,
        varName: Optional[str] = None,
        varType: Optional[str] = None,
        mask: Optional[str] = None,
        dateIni: Optional[str | int] = None,
        dateFin: Optional[str | int] = None,
        nHour: str = "06",
        vminOMA: Optional[float] = None,
        vmaxOMA: Optional[float] = None,
        vminSTD: float | None = 0.0,
        vmaxSTD: float | None = 14.0,
        channel: Optional[int | List[int]] = None,
        Clean: Optional[bool] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Plot time series and Hovmöller panels of radiance OmF/OmA statistics per channel.
    
        This function preserves the legacy behavior/output while making the code
        more robust to missing dates, flexible to different column names
        (``channel`` or ``nchan``), and safer against empty selections.
    
        Parameters
        ----------
        varName : str or None
            Variable/instrument name key in ``self[f].obsInfo`` dict.
        varType : str or None
            Variable type used as `.loc[varType]` selector.
        mask : str or None
            Pandas query-string applied to the DataFrame (e.g., ``"iuse>-99999.9"``).
            If ``None``, uses ``"iuse>-99999.9"`` (i.e., no effective filtering).
        dateIni : str | int | None
            Start date in ``YYYYMMDDHH`` (string or int).
        dateFin : str | int | None
            End date in ``YYYYMMDDHH`` (string or int), inclusive.
        nHour : str, default "06"
            Temporal step in hours between cycles (e.g., "06").
        vminOMA, vmaxOMA : float or None
            Y-limits for mean (OmF/OmA) plots. If both ``None``, computed from data.
        vminSTD, vmaxSTD : float or None
            Y-limits for standard deviation plots. If both ``None``, computed from data.
        channel : int | list[int] | None
            Specific channel or list of channels to plot. If ``None``, the function
            infers channels from the data; if empty, it defaults to ``[1..15]``.
        Clean : bool or None
            If ``True``, clears figures from memory after saving.
            Defaults to ``True`` if not provided.
        *args, **kwargs :
            Extra positional/keyword-arguments are accepted for forward compatibility
            but are currently ignored.
    
        Notes
        -----
        - Expects ``self[f].obsInfo[varName]`` to be a (potentially multi-indexed)
          DataFrame where rows can be selected with ``.loc[varType]`` and then
          filtered via ``.query(mask)``.
        - Accepts either ``channel`` or ``nchan`` column names for the channel id.
        - Missing days/hours are handled by filling with sentinel ``-99`` (masked
          downstream for plotting).
        - The function prints progress and basic summaries (legacy behavior).
    
        Returns
        -------
        None
            Saves PNG figures to the current working directory and prints progress.
        """
    
        # -------------------- setup & helpers --------------------
        def _safe_print(msg: str, color: str = "") -> None:
            """Print with optional legacy `setcolor` support."""
            try:
                if color and "setcolor" in globals():
                    # type: ignore[name-defined]
                    print(getattr(setcolor, color, ""))  # type: ignore[misc]
                    print(msg + getattr(setcolor, "ENDC", ""))  # type: ignore[misc]
                else:
                    print(msg)
            except Exception:
                print(msg)
    
        def _chan_series(df) -> np.ndarray:
            """Return channel series as numpy array of ints (empty if not found)."""
            if df is None:
                return np.array([], dtype=int)
            cols = df.columns
            if "nchan" in cols:
                return np.asarray(df["nchan"]).astype(int, copy=False)
            if "channel" in cols:
                return np.asarray(df["channel"]).astype(int, copy=False)
            return np.array([], dtype=int)
    
        def _get_series(df, name: str) -> np.ndarray:
            """Return numpy array for column `name` or empty array if missing."""
            if df is None or name not in getattr(df, "columns", []):
                return np.array([], dtype=float)
            return np.asarray(df[name]).astype(float, copy=False)
    
        def _ensure_iterable_channels(ch) -> Tuple[List[int], int, List[int]]:
            """
            Normalize `channel` parameter.
            Returns (zchan_list, chanList_flag, zchans_def).
            """
            if isinstance(ch, list):
                return [int(c) for c in ch], 1, [int(c) for c in ch]
            if ch is None:
                # AMSU-A typical default 1..15 kept for legacy behavior
                return list(range(1, 16)), 0, list(range(1, 16))
            # single int
            return [int(ch)], 0, list(range(1, 16))
    
        # -------------------- defaults & inputs --------------------
        Clean = True if Clean is None else bool(Clean)
    
        maski = "iuse>-99999.9" if mask is None else str(mask)
        cmaski = "iuse = All" if mask is None else str(mask)
    
        # instrument info (legacy print)
        try:
            varInfo = getVarInfo(varType, varName, "instrument")  # type: ignore[name-defined]
        except Exception:
            varInfo = None
        varInfo = varInfo if varInfo is not None else "Unknown instrument"
    
        omflag, omflaga = "OmF", "OmA"
        separator = " " + "=" * 109
    
        print()
        print(separator)
        print(f" Variable: {varName}  ||  type: {varType}  ||  {varInfo}  ||  check: {omflag}")
        print(separator)
        print()
    
        # channels normalization
        zchan, chanList, zchans_def = _ensure_iterable_channels(channel)
    
        # dates
        datei = datetime.strptime(str(dateIni), "%Y%m%d%H")
        datef = datetime.strptime(str(dateFin), "%Y%m%d%H")
        hour_step = int(nHour)
        dates: List[datetime] = []
        d = datei
        while d <= datef:
            dates.append(d)
            d += timedelta(hours=hour_step)
    
        # axis labels (DayHour) with 1/4 spacing of ticks
        dayhour_all = [dt.strftime("%d%H") for dt in dates]
        if len(dayhour_all) > 4:
            step = max(1, len(dayhour_all) // 4)
            DayHour = [val if (ix % step) == 0 else "" for ix, val in enumerate(dayhour_all)]
        else:
            DayHour = dayhour_all
    
        # pass 1: detect data presence and collect channels
        info_check: Dict[str, bool] = {}
        found_channels: set[int] = set()
        for f, dt in enumerate(dates):
            key = dt.strftime("%d%H")
            try:
                df = self[f].obsInfo[varName].query(maski).loc[varType]  # type: ignore[index]
            except Exception:
                _safe_print(
                    f"    >>> No information on this date ({dt.strftime('%Y-%m-%d:%H')}) <<< ",
                    color="WARNING",
                )
                info_check[key] = False
                continue
    
            chs = _chan_series(df)
            if chs.size:
                info_check[key] = True
                if channel is None or chanList == 1:
                    # aggregate any present channels
                    # np.unique is faster and avoids repeated set ops
                    found_channels.update(np.unique(chs).tolist())
                print(dt.strftime(" Preparing data for: Canais de radiancia %Y-%m-%d:%H"))
            else:
                info_check[key] = False
                _safe_print(
                    dt.strftime(" Preparing data for: %Y-%m-%d:%H - No information on this date "),
                    color="WARNING",
                )
    
        # final channel list
        if found_channels:
            levs = sorted(int(c) for c in found_channels)
        else:
            # if nothing found, keep default definition
            levs = sorted(set(zchans_def))
        # labels printed on Y for Hovmöller
        if channel is None or chanList == 1:
            zlevs = [z if z in zchans_def else "" for z in sorted(set(levs + zchans_def))]
        else:
            zlevs = [int(zchan[0])]  # single-channel mode uses 1 column
    
        print()
        print(separator)
        print()
        print("channels = ", levs)
    
        # containers
        list_meanByLevs: List[Any] = []
        list_stdByLevs: List[Any] = []
        list_countByLevs: List[Any] = []
        list_meanByLevsa: List[Any] = []
        list_stdByLevsa: List[Any] = []
        list_countByLevsa: List[Any] = []
    
        # pass 2: compute stats per date/channel
        for f, dt in enumerate(dates):
            print(dt.strftime(" Calculating for %Y-%m-%d:%H"))
            key = dt.strftime("%d%H")
    
            # prepare dicts for this date
            mean_f: Dict[int, float] = {int(lv): -99.0 for lv in levs}
            std_f: Dict[int, float] = {int(lv): -99.0 for lv in levs}
            cnt_f: Dict[int, int] = {int(lv): -99 for lv in levs}
    
            mean_a: Dict[int, float] = {int(lv): -99.0 for lv in levs}
            std_a: Dict[int, float] = {int(lv): -99.0 for lv in levs}
            cnt_a: Dict[int, int] = {int(lv): -99 for lv in levs}
    
            if info_check.get(key, False):
                try:
                    df = self[f].obsInfo[varName].query(maski).loc[varType]  # type: ignore[index]
                    chs = _chan_series(df)
                    omf = _get_series(df, "omf")
                    oma = _get_series(df, "oma")
    
                    # quick exit if no usable columns
                    if chs.size == 0 or (omf.size == 0 and oma.size == 0):
                        pass
                    else:
                        # channel filter: all or specific
                        if channel is not None and chanList != 1:
                            # single channel path (zchan[0] guaranteed from normalization)
                            c = int(zchan[0])
                            sel = (chs == c)
                            if omf.size:
                                arr = omf[sel]
                                arr = arr[np.isfinite(arr)]
                                if arr.size:
                                    mean_f[c] = float(np.nanmean(arr))
                                    std_f[c] = float(np.nanstd(arr))
                                    cnt_f[c] = int(arr.size)
                            if oma.size:
                                arr = oma[sel]
                                arr = arr[np.isfinite(arr)]
                                if arr.size:
                                    mean_a[c] = float(np.nanmean(arr))
                                    std_a[c] = float(np.nanstd(arr))
                                    cnt_a[c] = int(arr.size)
                        else:
                            # all channels present in `levs`
                            # compute once: channel->indices
                            # speeds up when `levs` is long
                            for c in levs:
                                sel = (chs == int(c))
                                if omf.size:
                                    arr = omf[sel]
                                    arr = arr[np.isfinite(arr)]
                                    if arr.size:
                                        mean_f[c] = float(np.nanmean(arr))
                                        std_f[c] = float(np.nanstd(arr))
                                        cnt_f[c] = int(arr.size)
                                if oma.size:
                                    arr = oma[sel]
                                    arr = arr[np.isfinite(arr)]
                                    if arr.size:
                                        mean_a[c] = float(np.nanmean(arr))
                                        std_a[c] = float(np.nanstd(arr))
                                        cnt_a[c] = int(arr.size)
    
                except Exception:
                    # keep -99 sentinels
                    pass
    
            # append in the expected shape
            if channel is None or chanList == 1:
                # matrix (dates x channels), reversed for legacy orientation
                rev = list(reversed(levs))
                list_meanByLevs.append([mean_f[c] for c in rev])
                list_stdByLevs.append([std_f[c] for c in rev])
                list_countByLevs.append([cnt_f[c] for c in rev])
    
                list_meanByLevsa.append([mean_a[c] for c in rev])
                list_stdByLevsa.append([std_a[c] for c in rev])
                list_countByLevsa.append([cnt_a[c] for c in rev])
            else:
                c = int(zchan[0])
                list_meanByLevs.append(mean_f[c])
                list_stdByLevs.append(std_f[c])
                list_countByLevs.append(cnt_f[c])
    
                list_meanByLevsa.append(mean_a[c])
                list_stdByLevsa.append(std_a[c])
                list_countByLevsa.append(cnt_a[c])
    
        # -------------------- plotting --------------------
        print()
        print(separator)
        print()
        print(" Making Graphics...")
    
        x_axis = np.arange(0, len(DayHour), 1)
    
        # to arrays
        if channel is None or chanList == 1:
            A = np.array(list_meanByLevs, dtype=float)
            S = np.array(list_stdByLevs, dtype=float)
            C = np.array(list_countByLevs, dtype=float)
            Aa = np.array(list_meanByLevsa, dtype=float)
            Sa = np.array(list_stdByLevsa, dtype=float)
            Ca = np.array(list_countByLevsa, dtype=float)
        else:
            # (dates x 1) to reuse same logic
            A = np.array(list_meanByLevs, dtype=float)[:, None]
            S = np.array(list_stdByLevs, dtype=float)[:, None]
            C = np.array(list_countByLevs, dtype=float)[:, None]
            Aa = np.array(list_meanByLevsa, dtype=float)[:, None]
            Sa = np.array(list_stdByLevsa, dtype=float)[:, None]
            Ca = np.array(list_countByLevsa, dtype=float)[:, None]
    
        # masked versions for plotting
        mean_final = np.ma.masked_where(A == -99, A)
        std_final = np.ma.masked_where(S == -99, S)
        count_final = np.ma.masked_where(C == -99, C)
    
        mean_finala = np.ma.masked_where(Aa == -99, Aa)
        std_finala = np.ma.masked_where(Sa == -99, Sa)
        count_finala = np.ma.masked_where(Ca == -99, Ca)
    
        OMF_inf, OMF_sup = A - S, A + S
        OMA_inf, OMA_sup = Aa - Sa, Aa + Sa
    
        # auto-limits
        def _finite_min(x: np.ndarray, default: float = 0.0) -> float:
            with np.errstate(invalid="ignore"):
                m = np.nanmin(x) if x.size else np.nan
            return float(m) if np.isfinite(m) else default
    
        def _finite_max(x: np.ndarray, default: float = 1.0) -> float:
            with np.errstate(invalid="ignore"):
                m = np.nanmax(x) if x.size else np.nan
            return float(m) if np.isfinite(m) else default
    
        mean_limit_inf = _finite_min(np.asarray([mean_final.min(), mean_finala.min()], dtype=float), 0.0)
        mean_limit_sup = _finite_max(np.asarray([mean_final.max(), mean_finala.max()], dtype=float), 1.0)
        std_limit_inf = _finite_min(np.asarray([std_final.min(), std_finala.min()], dtype=float), 0.0)
        std_limit_sup = _finite_max(np.asarray([std_final.max(), std_finala.max()], dtype=float), 1.0)
    
        omfoma_limit_inf = _finite_min(np.asarray([OMF_inf.min(), OMA_inf.min()], dtype=float), 0.0)
        omfoma_limit_sup = _finite_max(np.asarray([OMF_sup.max(), OMA_sup.max()], dtype=float), 1.0)
        omfoma_limit_inf = 0.9 * omfoma_limit_inf if omfoma_limit_inf > 0 else 1.1 * omfoma_limit_inf
        omfoma_limit_sup = 1.1 * omfoma_limit_sup
    
        if vminOMA is None and vmaxOMA is None:
            vminOMA, vmaxOMA = mean_limit_inf, 1.1 * mean_limit_sup
        vminOMA = 0.9 * vminOMA if float(vminOMA) > 0 else 1.1 * float(vminOMA)
        vmaxOMAabs = max(abs(float(vminOMA)), abs(float(vminOMA)))  # keeps legacy “sym abs” intent
    
        if vminSTD is None and vmaxSTD is None:
            vminSTD, vmaxSTD = std_limit_inf - 0.1 * std_limit_inf, 1.1 * std_limit_sup
    
        date_title = f"{datei.strftime('%d%b')}-{dates[-1].strftime('%d%b')} {dates[-1].strftime('%Y')}"
        instrument_title = f"{varName}-{varType}  |  {varInfo}"
    
        # ---- multi-channel Hovmöller plots ----
        if channel is None or chanList == 1:
            y_ticks = np.arange(0, len(zlevs), 1)
            x_ticks = np.arange(0, len(DayHour), 1)
    
            def _common_panel(ax, arr, vmin, vmax, cmap, title_left: str, title_right: str, ylabel: str, xlabel: str) -> None:
                ax.add_patch(
                    mpl.patches.Rectangle(
                        (-1, -1),
                        (len(DayHour) + 1),
                        (len(levs) + 3),
                        hatch="xxxxx",
                        color="black",
                        fill=False,
                        snap=False,
                        zorder=0,
                    )
                )
                im = ax.imshow(
                    np.flipud(arr.T),
                    origin="lower",
                    vmin=vmin,
                    vmax=vmax,
                    cmap=cmap,
                    aspect="auto",
                    zorder=1,
                    interpolation="none",
                )
                plt.colorbar(im, orientation="horizontal", pad=0.18, shrink=1.0)
                ax.set_title(title_left, loc="left", fontsize=10)
                ax.set_title(title_right, loc="right", fontsize=10)
                ax.set_ylabel(ylabel)
                ax.set_xticks(x_ticks)
                ax.set_yticks(y_ticks)
                ax.set_xticklabels(DayHour)
                ax.set_yticklabels(zlevs)
                major_ticks = [DayHour.index(dh) for dh in filter(None, DayHour)]
                ax.set_xticks(major_ticks)
    
            plt.rcParams["axes.facecolor"] = "None"
            plt.rcParams["hatch.linewidth"] = 0.3
    
            # OmF
            fig = plt.figure(figsize=(6, 9))
            ax1 = plt.subplot(3, 1, 1)
            _common_panel(ax1, mean_final, -vmaxOMAabs, vmaxOMAabs, "seismic", instrument_title, date_title, "Channels", f"Mean ({omflag})")
    
            ax2 = plt.subplot(3, 1, 2)
            _common_panel(ax2, std_final, float(vminSTD), float(vmaxSTD), "Blues", instrument_title, date_title, "Channels", f"Standard Deviation ({omflag})")
    
            ax3 = plt.subplot(3, 1, 3)
            vmax_cnt = _finite_max(np.asarray([count_final.max()], dtype=float), 1.0)
            _common_panel(ax3, count_final, 0.0, vmax_cnt, "gist_heat_r", instrument_title, date_title, "Channels", f"Total Observations ({cmaski})")
    
            plt.tight_layout()
            plt.savefig(f"hovmoller_{varName}-{varType}_{omflag}.png", bbox_inches="tight", dpi=100)
            if Clean:
                plt.clf()
    
            # OmA
            fig = plt.figure(figsize=(6, 9))
            ax1 = plt.subplot(3, 1, 1)
            _common_panel(ax1, mean_finala, -vmaxOMAabs, vmaxOMAabs, "seismic", instrument_title, date_title, "Channels", f"Mean ({omflaga})")
    
            ax2 = plt.subplot(3, 1, 2)
            _common_panel(ax2, std_finala, float(vminSTD), float(vmaxSTD), "Blues", instrument_title, date_title, "Channels", f"Standard Deviation ({omflaga})")
    
            ax3 = plt.subplot(3, 1, 3)
            vmax_cnta = _finite_max(np.asarray([count_finala.max()], dtype=float), 1.0)
            _common_panel(ax3, count_finala, 0.0, vmax_cnta, "gist_heat_r", instrument_title, date_title, "Channels", f"Total Observations ({cmaski})")
    
            plt.tight_layout()
            plt.savefig(f"hovmoller_{varName}-{varType}_{omflaga}.png", bbox_inches="tight", dpi=100)
            if Clean:
                plt.clf()
    
        # ---- single-channel time series panels ----
        else:
            # dados 1D já prontos (listas) + envelopes
            plt.style.use("seaborn-v0_8-ticks")
            c = int(zchan[0])
            forplot = f"Channel = {c}"
            forplotname = f"Channel_{c}"
    
            # helper to place major xticks only where DayHour has labels
            def _apply_xticks(ax):
                ax.set_xticks(x_axis)
                ax.set_xticklabels(DayHour)
                major_ticks = [DayHour.index(dh) for dh in filter(None, DayHour)]
                ax.set_xticks(major_ticks)
    
            # Mean & Std (OmF)
            fig, ax1 = plt.subplots(1, 1, figsize=(6, 4))
            ax1.axhline(y=0.0, ls="solid", c="#d3d3d3")
            ax1.plot(x_axis, list_meanByLevs, "b-", label=f"Mean ({omflag})")
            ax1.plot(x_axis, list_meanByLevs, "bo", label="")
            ax1.set_xlabel("Date (DayHour)", fontsize=10)
            ax1.set_ylim(float(vminOMA), float(vmaxOMA))
            ax1.set_ylabel(f"Mean ({omflag})", color="b", fontsize=10)
            ax1.tick_params("y", colors="b")
            _apply_xticks(ax1)
            if len(list_meanByLevs):
                ax1.axhline(y=float(np.nanmean(list_meanByLevs)), ls="dotted", c="blue")
    
            ax2 = ax1.twinx()
            ax2.plot(x_axis, np.squeeze(S), "r-", label=f"Std. Deviation ({omflag})")
            ax2.plot(x_axis, np.squeeze(S), "rs", label="")
            ax2.set_ylim(float(vminSTD), float(vmaxSTD))
            ax2.set_ylabel(f"Std. Deviation ({omflag})", color="r", fontsize=10)
            ax2.tick_params("y", colors="r")
            if np.size(S):
                ax2.axhline(y=float(np.nanmean(S)), ls="dotted", c="red")
    
            ax3 = ax1.twinx()
            ax3.plot(x_axis, np.squeeze(C), "g-", label=f"Total Observations ({cmaski})")
            ax3.plot(x_axis, np.squeeze(C), "g^", label="")
            vmax_cnt = _finite_max(np.asarray([np.nanmax(C)], dtype=float), 1.0)
            ax3.set_ylim(0.0, vmax_cnt + (vmax_cnt / 8.0))
            ax3.set_ylabel(f"Total Observations ({cmaski})", color="g", fontsize=10)
            ax3.tick_params("y", colors="g")
            ax3.spines["right"].set_position(("axes", 1.15))
            ax3.set_title(instrument_title, loc="left", fontsize=10)
            ax3.set_title(date_title, loc="right", fontsize=10)
            _apply_xticks(ax3)
    
            plt.title(instrument_title, loc="left", fontsize=9)
            plt.title(date_title, loc="right", fontsize=9)
            plt.tight_layout()
            plt.savefig(f"time_series_{varName}-{varType}_{omflag}_{forplotname}.png", bbox_inches="tight", dpi=100)
            if Clean:
                plt.clf()
    
            # Mean & Std (OmA)
            fig, ax1 = plt.subplots(1, 1, figsize=(6, 4))
            ax1.axhline(y=0.0, ls="solid", c="#d3d3d3")
            ax1.plot(x_axis, list_meanByLevsa, "b-", label=f"Mean ({omflaga})")
            ax1.plot(x_axis, list_meanByLevsa, "bo", label="")
            ax1.set_xlabel("Date (DayHour)", fontsize=10)
            ax1.set_ylim(float(vminOMA), float(vmaxOMA))
            ax1.set_ylabel(f"Mean ({omflaga})", color="b", fontsize=10)
            ax1.tick_params("y", colors="b")
            _apply_xticks(ax1)
            if len(list_meanByLevsa):
                ax1.axhline(y=float(np.nanmean(list_meanByLevsa)), ls="dotted", c="blue")
    
            ax2 = ax1.twinx()
            ax2.plot(x_axis, np.squeeze(Sa), "r-", label=f"Std. Deviation ({omflaga})")
            ax2.plot(x_axis, np.squeeze(Sa), "rs", label="")
            ax2.set_ylim(float(vminSTD), float(vmaxSTD))
            ax2.set_ylabel(f"Std. Deviation ({omflaga})", color="r", fontsize=10)
            ax2.tick_params("y", colors="r")
            if np.size(Sa):
                ax2.axhline(y=float(np.nanmean(Sa)), ls="dotted", c="red")
    
            ax3 = ax1.twinx()
            ax3.plot(x_axis, np.squeeze(Ca), "g-", label=f"Total Observations ({cmaski})")
            ax3.plot(x_axis, np.squeeze(Ca), "g^", label="")
            vmax_cnta = _finite_max(np.asarray([np.nanmax(Ca)], dtype=float), 1.0)
            ax3.set_ylim(0.0, 1.2 * vmax_cnta)
            ax3.set_ylabel(f"Total Observations ({cmaski})", color="g", fontsize=10)
            ax3.tick_params("y", colors="g")
            ax3.spines["right"].set_position(("axes", 1.15))
            ax3.set_title(instrument_title, loc="left", fontsize=10)
            ax3.set_title(date_title, loc="right", fontsize=10)
            _apply_xticks(ax3)
    
            plt.title(instrument_title, loc="left", fontsize=9)
            plt.title(date_title, loc="right", fontsize=9)
            plt.tight_layout()
            plt.savefig(f"time_series_{varName}-{varType}_{omflaga}_{forplotname}.png", bbox_inches="tight", dpi=100)
            if Clean:
                plt.clf()
    
            # OmF & OmA overlay
            from matplotlib.offsetbox import AnchoredOffsetbox, TextArea, VPacker
    
            fig, ax1 = plt.subplots(1, 1, figsize=(6, 4))
            ax1.axhline(y=0.0, ls="solid", c="#d3d3d3")
            ax1.plot(x_axis, list_meanByLevs, "b-", label=f"Mean ({omflag})")
            ax1.plot(x_axis, list_meanByLevsa, "r-", label=f"Mean ({omflaga})")
            ax1.set_xlabel("Date (DayHour)", fontsize=10)
            ax1.set_ylim(float(vminOMA), float(vmaxOMA))
            _apply_xticks(ax1)
            if len(list_meanByLevs):
                ax1.axhline(y=float(np.nanmean(list_meanByLevs)), ls="dotted", c="blue")
            if len(list_meanByLevsa):
                ax1.axhline(y=float(np.nanmean(list_meanByLevsa)), ls="dotted", c="red")
    
            ybox1 = TextArea(f"Mean ({omflag})", textprops=dict(color="b", size=12, rotation=90, ha="left", va="bottom"))
            ybox2 = TextArea(" and ", textprops=dict(color="k", size=12, rotation=90, ha="left", va="bottom"))
            ybox3 = TextArea(f"Mean ({omflaga})", textprops=dict(color="r", size=12, rotation=90, ha="left", va="bottom"))
            ybox = VPacker(children=[ybox3, ybox2, ybox1], align="bottom", pad=0, sep=5)
            anchored_ybox = AnchoredOffsetbox(loc=3, child=ybox, pad=0.0, frameon=False, bbox_to_anchor=(-0.12, 0.16), bbox_transform=ax1.transAxes, borderpad=0.0)
            ax1.add_artist(anchored_ybox)
    
            plt.legend()
            plt.tight_layout()
            plt.savefig(f"time_series_{varName}-{varType}_OmFOmA_{forplotname}.png", bbox_inches="tight", dpi=100)
            if Clean:
                plt.clf()
    
            # OmF & OmA with Std envelopes
            fig, ax1 = plt.subplots(1, 1, figsize=(6, 4))
            ax1.plot(x_axis, list_meanByLevs, lw=2, label="OmF Mean", color="blue", zorder=1)
            ax1.fill_between(x_axis, (A - S).flatten(), (A + S).flatten(), label="OmF Std Dev", alpha=0.3, zorder=1)
            ax1.plot(x_axis, list_meanByLevsa, lw=2, label="OmA Mean", color="red", zorder=2)
            ax1.fill_between(x_axis, (Aa - Sa).flatten(), (Aa + Sa).flatten(), label="OmA Std Dev", alpha=0.3, zorder=2)
    
            ybox1 = TextArea(" OmF ", textprops=dict(color="b", size=12, rotation=90, ha="left", va="bottom"))
            ybox2 = TextArea(" | ", textprops=dict(color="k", size=12, rotation=90, ha="left", va="bottom"))
            ybox3 = TextArea(" OmA ", textprops=dict(color="r", size=12, rotation=90, ha="left", va="bottom"))
            ybox = VPacker(children=[ybox3, ybox2, ybox1], align="bottom", pad=0, sep=5)
            anchored_ybox = AnchoredOffsetbox(loc=3, child=ybox, pad=0.0, frameon=False, bbox_to_anchor=(-0.125, 0.42), bbox_transform=ax1.transAxes, borderpad=0.0)
            ax1.add_artist(anchored_ybox)
    
            ax1.set_xlabel("Date (DayHour)", fontsize=12)
            ax1.set_ylim(omfoma_limit_inf, omfoma_limit_sup)
            ax1.legend(
                bbox_to_anchor=(-0.11, -0.25),
                ncol=4,
                loc="lower left",
                fancybox=True,
                shadow=False,
                frameon=True,
                framealpha=1.0,
                fontsize="11",
            )
            plt.grid(axis="y", color="lightgray", linestyle="-.", linewidth=0.5, zorder=0)
    
            ax2 = ax1.twinx()
            ax2.plot(x_axis, list_countByLevsa, lw=2, label="OmA", linestyle="--", color="green", zorder=3)
            ax2.plot(x_axis, list_countByLevs, lw=2, label="OmF", linestyle=":", color="purple", zorder=3)
            ax2.set_ylabel(f"Total Observations (OmF | OmA)\n ({cmaski})", fontsize=12)
            ymax_ = max(
                1.0,
                float(np.nanmax(list_countByLevsa)) if len(list_countByLevsa) else 1.0,
            )
            ax2.set_ylim(0.0, ymax_ + ymax_ / 5.0)
            ax2.legend(loc="upper left", ncol=2, fancybox=True, shadow=False, frameon=True, framealpha=1.0, fontsize="11")
    
            ax2.set_xticks(x_axis)
            ax2.set_xticklabels(DayHour)
            major_ticks = [DayHour.index(dh) for dh in filter(None, DayHour)]
            ax2.set_xticks(major_ticks)
            plt.title(instrument_title, loc="left", fontsize=10)
            plt.title(date_title, loc="right", fontsize=10)
    
            plt.tight_layout()
            plt.savefig(f"time_series_{varName}-{varType}_OmFOmA_StdDev_{forplotname}.png", bbox_inches="tight", dpi=100)
    
        # cleanup
        if Clean:
            plt.close("all")
    
        print(" Done!\n")

    # ------------------------------------------------------------------
    # Radiance counts/time‑series (assimilated/monitored/rejected)
    # ------------------------------------------------------------------
    def statcount(self, varName=None, varType=None, noiqc=False,
                  dateIni=None, dateFin=None, nHour="06",
                  channel=None, figTS=False, figMap=False, **kwargs):
        """Count observations across time (optionally per radiance channel).

        Parameters
        ----------
        varName : str
            Variable/instrument (e.g., ``'amsua'``).
        varType : str
            Source id (e.g., ``'n19'`` for radiance).
        noiqc : bool, default False
            If ``False``, counts only ``idqc==0`` (post‑IQC used). When
            ``True``, disables this filter.
        dateIni, dateFin : int | str
            Time window (``YYYYMMDDHH``).
        nHour : str, default "06"
            Step (hours) between cycles.
        channel : int, optional
            If provided, restrict counts to a single channel.
        figTS : bool, default False
            If ``True``, produce a time series figure.
        figMap : bool, default False
            If ``True``, produce a simple lon/lat scatter for the last
            available cycle.

        Returns
        -------
        None
        The StatCount function plots a time series of assimilated, monitored and rejected data. 

        Example:

        varName = 'uv'           # Variable
        varType = 224            # Source Type
        noiqc = False            # noiqc GSI namelist parameter (OI QC - True or False)
        dateIni = 2013010100     # Inicial Date
        dateFin = 2013010900     # Final Date
        nHour = "06"             # Time Interval
        channel = None           # Radiance channel number (None for the conventional dataset)
        figTS = True             # Creates the time series plot
        figMap = False           # Creates the spatial plot for each time
        
        ! Case conventional dataset: channel = None
        ! The QC process creates a number indicating the data quality for each observation.
        ! These numbers are called QC markers in PrepBUFR files and are important as parts of
        ! the observation information. GSI uses QC markers to decide how to use the data. A 
        ! brief summary of the meaning of the QC markers is as follows:
        ! 
        !    +-----------------+-----------------------------------------------------------+
        !    | QC markes range | Data Process in GSI                                       |
        !    +-----------------+-----------------------------------------------------------+
        !    |  > 15 or        |GSI skips these observations during reading procedure. That|
        !    |  <= 0           |means these observations are tossed                        | 
        !    +-----------------+-----------------------------------------------------------+
        !    |  >= lim_qm      |These observations will be in monitoring status. That means|
        !    |  and            |these observations will be read in and be processed through|
        !    |  < = 15         |GSI QC process (gross check) and innovation calculation    | 
        !    |                 |stage but will not be used in inner iteration.             |
        !    +-----------------+-----------------------------------------------------------+
        !    |  > 0            |Observations will be used in further gross check (failure  |
        !    |  and            |observation will be list in rejection), innovation         |
        !    |  < lim_qm       |caalculation, and the analysis (inner iteration).          |
        !    +-----------------+-----------------------------------------------------------+

        !    +----------------------+---------------+---------------+
        !    |The value of namelist | lim_qm for Ps | lim_qm others |
        !    |option noiqc          |               |               |
        !    +----------------------+---------------+---------------+
        !    |True (without OI QC)  |       7       |       8       |
        !    +----------------------+---------------+---------------+
        !    |False (with OI QC)    |       4       |       4       |
        !    +----------------------+---------------+---------------+
        
        
        ! Case radiance dataset: channel = number
        ! There are three types of data classification: assimilated, monitored and rejected.
        ! Monitored data is organized into two groups: possibly assimilated and possibly rejected.
        !
        !    +------------------------+-------------+--------------------+
        !    |                        |   idqc      |        iuse        |
        !    +------------------------+-------------+--------------------+
        !    | Assimilated            |   == 0      |   >= 1             |
        !    +------------------------+-------------+--------------------+
        !    |            assimilated |   == 0      |   >= -1 and < 1    |
        !    | Monitored              |             |                    |
        !    |            rejected    |   != 0      |   >= -1 and < 1    |
        !    +------------------------+-------------+--------------------+
        !    | Rejected               |   != 0      |   >= 1             |
        !    +------------------------+-------------+--------------------+
        """

    
        # ---------- helpers ----------
        def _chan_series(df):
            if "nchan" in df.columns:
                return df["nchan"]
            if "channel" in df.columns:
                return df["channel"]
            return pd.Series([], dtype="int64")
    
        def _safe_len(x):
            try: return int(len(x))
            except Exception: return 0
    
        # máscara “iuse” e “idqc” (quando noiqc=False, aplica idqc==0)
        base_mask = "iuse>-99999.9"
        if not noiqc:
            base_mask += " & idqc==0"
    
        # cabeçalho
        sep = " " + "="*109
        print("\n"+sep)
        instr = getVarInfo(varType, varName, "instrument") or "Unknown instrument"
        print(f" Variable: {varName}  ||  type: {varType}  ||  {instr}  ||  STATCOUNT")
        print(sep+"\n")
    
        # parse datas
        datei = datetime.strptime(str(dateIni), "%Y%m%d%H")
        datef = datetime.strptime(str(dateFin), "%Y%m%d%H")
        step  = int(nHour)
    
        # ---------- 1) Varre datas: detecta dados e coleta canais ----------
        DayHour, info_check = [], {}
        chans_seen = set()
        f = 0
        d = datei
        while d <= datef:
            dh = d.strftime("%d%H")
            DayHour.append(dh)
            try:
                df_t = self[f].obsInfo[varName].query(base_mask).loc[varType]
                if _safe_len(df_t) > 0:
                    info_check[dh] = True
                    chs = _chan_series(df_t)
                    if _safe_len(chs) > 0:
                        chans_seen.update(int(c) for c in np.asarray(chs).astype(int))
                else:
                    info_check[dh] = False
                    print("++++++++++++++++++++++++++ ERROR: file reading --> STATCOUNT ++++++++++++++++++++++++++")
                    print(setcolor.WARNING + f"    >>> No information on this date ({d.strftime('%Y-%m-%d:%H')}) <<< " + setcolor.ENDC)
            except Exception:
                info_check[dh] = False
                print("++++++++++++++++++++++++++ ERROR: file reading --> STATCOUNT ++++++++++++++++++++++++++")
                print(setcolor.WARNING + f"    >>> No information on this date ({d.strftime('%Y-%m-%d:%H')}) <<< " + setcolor.ENDC)
            finally:
                f += 1
                d += timedelta(hours=step)
    
        # modo de canal / rótulos
        if channel is None:
            chan_mode = "all"
            forplot = "All Channels"
            forplotname = "All_Channels"
        else:
            chan_mode = "one"
            channel   = int(channel)
            forplot = f"Channel = {channel}"
            forplotname = f"Channel_{channel}"
    
        chans_sorted = sorted(chans_seen) if chans_seen else []
    
        # ---------- 2) Contagem por data ----------
        total_counts = []
        per_channel_counts = {int(c): [] for c in chans_sorted}
        f = 0
        d = datei
        while d <= datef:
            dh = d.strftime("%d%H")
            tot = 0
            per_chan = {int(c): 0 for c in chans_sorted}
            try:
                if info_check.get(dh, False):
                    df_t = self[f].obsInfo[varName].query(base_mask).loc[varType]
                    chs = _chan_series(df_t)
                    if chan_mode == "one":
                        if _safe_len(chs) > 0:
                            arr = np.asarray(chs).astype(int)
                            tot = int(np.count_nonzero(arr == channel))
                        else:
                            tot = 0
                    else:
                        tot = _safe_len(df_t)
                        if _safe_len(chs) > 0:
                            arr = np.asarray(chs).astype(int)
                            for c in chans_sorted:
                                per_chan[c] = int(np.count_nonzero(arr == c))
                # avança f correspondente a esta data
                f += 1
            except Exception:
                f += 1  # não trava sequência
            total_counts.append(tot)
            for c in chans_sorted:
                per_channel_counts[c].append(per_chan[c])
            d += timedelta(hours=step)
    
        # ---------- 3) Plots ----------
        # ticks a cada ~1/4
        x = np.arange(len(DayHour))
        if len(DayHour) > 4:
            ticks = [i for i in range(len(DayHour)) if i % max(1, len(DayHour)//4) == 0]
        else:
            ticks = list(range(len(DayHour)))
    
        # Série temporal (figTS)
        if figTS:
            plt.style.use('seaborn-v0_8-ticks')
            if chan_mode == "one":
                fig, ax = plt.subplots(1, 1, figsize=(7, 4))
                ax.plot(x, total_counts, "-o")
                ax.set_ylabel("Total Observations (" + ("no IQC" if noiqc else "iuse=idqc==0") + ")")
                ax.set_xlabel("Date (DayHour)")
                ax.set_xticks(ticks); ax.set_xticklabels([DayHour[i] for i in ticks])
                ax.set_title(f"{varName}-{varType}  |  {instr}", loc="left", fontsize=10)
                ax.set_title(f"{datei.strftime('%d%b')}-{datef.strftime('%d%b %Y')}", loc="right", fontsize=10)
                plt.axhline(y=(np.mean(total_counts) if total_counts else 0.0), ls='dotted', c='gray')
                t = plt.annotate(forplot, xy=(0.02, 0.96), xycoords='axes fraction',
                                 color='gray', fontsize=10, fontweight='bold')
                t.set_bbox(dict(facecolor='whitesmoke', alpha=1.0, edgecolor='whitesmoke',
                                boxstyle="square,pad=0.2"))
                plt.tight_layout()
                plt.savefig(f"statcount_{varName}-{varType}_{forplotname}.png",
                            bbox_inches='tight', dpi=100)
                plt.clf(); plt.close(fig)
            else:
                if chans_sorted:
                    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
                    stack = np.vstack([per_channel_counts[c] for c in chans_sorted]) if chans_sorted else np.zeros((1, len(DayHour)))
                    ax.stackplot(x, stack, labels=[f"ch {c}" for c in chans_sorted], alpha=0.7)
                    ax.plot(x, total_counts, "k-", lw=1.2, label="Total")
                    ax.set_ylabel("Total Observations (" + ("no IQC" if noiqc else "iuse=idqc==0") + ")")
                    ax.set_xlabel("Date (DayHour)")
                    ax.set_xticks(ticks); ax.set_xticklabels([DayHour[i] for i in ticks])
                    ax.set_title(f"{varName}-{varType}  |  {instr}", loc="left", fontsize=10)
                    ax.set_title(f"{datei.strftime('%d%b')}-{datef.strftime('%d%b %Y')}", loc="right", fontsize=10)
                    ax.legend(loc="upper left", ncol=min(4, len(chans_sorted)+1), fontsize=8)
                    t = plt.annotate(forplot, xy=(0.02, 0.96), xycoords='axes fraction',
                                     color='gray', fontsize=10, fontweight='bold')
                    t.set_bbox(dict(facecolor='whitesmoke', alpha=1.0, edgecolor='whitesmoke',
                                    boxstyle="square,pad=0.2"))
                    plt.tight_layout()
                    plt.savefig(f"statcount_{varName}-{varType}_{forplotname}.png",
                                bbox_inches='tight', dpi=100)
                    plt.clf(); plt.close(fig)
                else:
                    fig, ax = plt.subplots(1, 1, figsize=(7, 4))
                    ax.plot(x, total_counts, "-o")
                    ax.set_ylabel("Total Observations (" + ("no IQC" if noiqc else "iuse=idqc==0") + ")")
                    ax.set_xlabel("Date (DayHour)")
                    ax.set_xticks(ticks); ax.set_xticklabels([DayHour[i] for i in ticks])
                    ax.set_title(f"{varName}-{varType}  |  {instr}", loc="left", fontsize=10)
                    ax.set_title(f"{datei.strftime('%d%b')}-{datef.strftime('%d%b %Y')}", loc="right", fontsize=10)
                    plt.axhline(y=(np.mean(total_counts) if total_counts else 0.0), ls='dotted', c='gray')
                    t = plt.annotate(forplot, xy=(0.02, 0.96), xycoords='axes fraction',
                                     color='gray', fontsize=10, fontweight='bold')
                    t.set_bbox(dict(facecolor='whitesmoke', alpha=1.0, edgecolor='whitesmoke',
                                    boxstyle="square,pad=0.2"))
                    plt.tight_layout()
                    plt.savefig(f"statcount_{varName}-{varType}_{forplotname}.png",
                                bbox_inches='tight', dpi=100)
                    plt.clf(); plt.close(fig)
    
        # Mapa (mantido por compat; opcional)
        if figMap:
            try:
                # conta total por ponto na última data com dados (representativo)
                last_idx = None
                for i in range(len(DayHour)-1, -1, -1):
                    if info_check.get(DayHour[i], False):
                        last_idx = i
                        break
                if last_idx is not None:
                    df_last = self[last_idx].obsInfo[varName].query(base_mask).loc[varType]
                    if _safe_len(df_last) > 0 and {'lat','lon'}.issubset(df_last.columns):
                        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
                        ax.scatter(df_last['lon'], df_last['lat'], s=2, alpha=0.5)
                        ax.set_title(f"{varName}-{varType}  |  {instr}  |  {forplot}")
                        ax.set_xlabel("lon"); ax.set_ylabel("lat")
                        plt.tight_layout()
                        plt.savefig(f"statcount_map_{varName}-{varType}_{forplotname}.png",
                                    bbox_inches='tight', dpi=100)
                        plt.clf(); plt.close(fig)
            except Exception:
                pass
    
        print(" Done!\n")

        return

# --- End of class plot_diag ----------------------------------------------

# EOF

