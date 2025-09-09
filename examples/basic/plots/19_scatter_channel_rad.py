from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 19_scatter_channel.py <diag_rad_path> [channel] [x] [y]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_amsua_n19_01.2024013018")
    ch    = int(arg_or_default(2, 7))
    x     = arg_or_default(3, "omf")
    y     = arg_or_default(4, "zasat")
    ax = diagPlotter(open_diag(fpath)).plot_scatter_channel(ch, x=x, y=y, s=2, alpha=0.5)
    out = ensure_outdir() / f"19_scatter_channel_{ch}_{x}_vs_{y}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
