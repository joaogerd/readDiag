#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
try:
    import cartopy.crs as ccrs, cartopy.feature as cfeature
    _HAS_CARTOPY=True
except Exception: _HAS_CARTOPY=False
from readDiag import diagAccess

def build_parser():
    p=argparse.ArgumentParser(description="AMSU-A swath plot")
    p.add_argument("--file", default="data/diag_amsua_n19_01.2024013018")
    p.add_argument("--channel", type=int, default=14)
    p.add_argument("--value", choices=("tb_obs","omf","oma"), default="tb_obs")
    p.add_argument("--basemap", action="store_true")
    p.add_argument("--resolution", default="110m")
    p.add_argument("--marker-size", type=float, default=6.0)
    p.add_argument("--cmap", default="jet")
    p.add_argument("--outdir", default="outputs/examples")
    p.add_argument("--save", action="store_true")
    return p

def main():
    a=build_parser().parse_args()
    outdir=Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    d=diagAccess(a.file)
    ch_idx=a.channel-1
    dfs=d.get_data_frame()["dataframes"]["diagbufchan_df"]
    if ch_idx<0 or ch_idx>=len(dfs): raise SystemExit("invalid channel")
    # merge geo + channel
    geo=d.get_data_frame()["dataframes"]["diagbuf_df"][["lat","lon"]].reset_index(drop=True)
    ch =dfs[ch_idx].reset_index(drop=True)
    df=pd.concat([geo,ch],axis=1)
    if a.value not in df.columns: raise SystemExit(f"missing {a.value}")
    if a.basemap and _HAS_CARTOPY:
        fig,ax=plt.subplots(figsize=(12,6), subplot_kw=dict(projection=ccrs.PlateCarree()))
        ax.set_global(); ax.gridlines(draw_labels=False, linestyle=":", alpha=0.4)
        ax.coastlines(resolution=a.resolution, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS.with_scale(a.resolution), linewidth=0.3)
        ax.add_feature(cfeature.LAND.with_scale(a.resolution), facecolor="lightgray", alpha=0.6)
        transform=ccrs.PlateCarree()
        extra=dict(transform=transform)
    else:
        fig,ax=plt.subplots(figsize=(12,6)); ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
        extra={}
    sc=ax.scatter(df["lon"], df["lat"], c=df[a.value], s=a.marker_size, cmap=a.cmap, **extra)
    cb=plt.colorbar(sc, ax=ax, pad=0.02); cb.set_label({"tb_obs":"Brightness Temperature [K]","omf":"O–F","oma":"O–A"}[a.value])
    fig.suptitle("Radiance - AMSU-A - NOAA-19.    Channel ={}                         30Jan2024 - 1800 GMT".format(a.channel), y=0.98, fontsize=10)
    plt.tight_layout(rect=(0,0,1,0.97))
    if a.save:
        out=outdir/f"amsua_swath_ch{a.channel}_{a.value}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight"); print("[saved]", out)
    else:
        plt.show()
    plt.close(fig)

if __name__=="__main__": main()
