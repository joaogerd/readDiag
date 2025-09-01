#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot AMSU-A radiance swath (channel 15, NOAA-19).
"""
import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from readDiag import diagAccess, diagPlotter

# caminho do diag radiance AMSU-A
ROOT = os.path.dirname(os.path.dirname(__file__))

RAD_FILE = os.path.join(ROOT, "data", "diag_amsua_n15_01.2024013018")

def main():
    diag = diagAccess(RAD_FILE)
    plotter = diagPlotter(diag)

    # Faz um scatter map do canal 14 (índice 13 se 0-based)
    ch_idx = 13   # canal 14 → índice 13
    dfs = diag.get_data_frame()["dataframes"]["diagbufchan_df"]
    df_geo = diag.get_data_frame()["dataframes"]["diagbuf_df"][["lat","lon"]]
    df = dfs[ch_idx].reset_index(drop=True)
    df = pd.concat([df_geo.reset_index(drop=True), df.reset_index(drop=True)], axis=1)
    

    # cria figura com projeção PlateCarree
    fig, ax = plt.subplots(subplot_kw=dict(projection=ccrs.PlateCarree()), figsize=(12,6))
    ax.set_global()
    ax.coastlines(resolution="110m", linewidth=0.5)
    ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.3)
    ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor="lightgray", alpha=0.6)

    sc = ax.scatter(
        df["lon"], df["lat"], c=df["tb_obs"],
        s=6, cmap="jet", transform=ccrs.PlateCarree()
    )
    cb = plt.colorbar(sc, ax=ax, orientation="vertical", pad=0.02)
    cb.set_label("Brightness Temperature [K]")

    ax.set_title("Radiance - AMSU-A NOAA-19 (Channel 14)\n01 Feb 2024 00 UTC", loc="left")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()

