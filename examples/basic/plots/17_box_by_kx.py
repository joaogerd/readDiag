from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 17_box_by_kx.py <diag_conv_path> [var] [param]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "q")
    param = arg_or_default(3, "omf")
    ax = diagPlotter(open_diag(fpath)).plot_box_by_kx(var, param=param)
    out = ensure_outdir() / f"17_box_by_kx_{var}_{param}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
