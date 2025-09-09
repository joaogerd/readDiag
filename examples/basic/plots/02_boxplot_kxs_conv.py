from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter

"""
Uso:
  python 02_boxplot_kxs_conv.py <diag_conv_path> [var] [param]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "q")
    param = arg_or_default(3, "omf")

    diag = open_diag(fpath)
    p = diagPlotter(diag)
    ax = p.plot_boxplot_kxs_conv(var, param=param, title=f"{var} – {param} por KX")
    out = ensure_outdir() / f"02_boxplot_kxs_conv_{var}_{param}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight")
    print(f"salvo: {out}")
