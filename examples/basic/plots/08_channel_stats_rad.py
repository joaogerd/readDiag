from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 08_channel_stats_rad.py <diag_rad_path> [param] [agg]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_amsua_n19_01.2024013018")
    param = arg_or_default(2, "omf")
    agg   = arg_or_default(3, "mean")
    ax = diagPlotter(open_diag(fpath)).plot_channel_stats_rad(param=param, agg=agg, marker="o")
    out = ensure_outdir() / f"08_channel_stats_{param}_{agg}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
