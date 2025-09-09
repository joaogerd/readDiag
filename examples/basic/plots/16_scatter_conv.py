from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 16_scatter_conv.py <diag_conv_path> [var] [kx] [x] [y]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "t")
    kx    = int(arg_or_default(3, 120))
    x     = arg_or_default(4, "end_err")
    y     = arg_or_default(5, "omf")
    ax = diagPlotter(open_diag(fpath)).plot_scatter_conv(var, kx, x=x, y=y, s=3, alpha=0.6)
    out = ensure_outdir() / f"16_scatter_conv_{var}_kx{kx}_{x}_vs_{y}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
