from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter

"""
Uso:
  python 01_hist_conv.py <diag_conv_path> [var] [kx] [param] [bins]
Ex:
  python 01_hist_conv.py data/diag_conv_01.2024013018 t 120 omf 60
"""

if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "t")
    kx    = int(arg_or_default(3, 120))
    param = arg_or_default(4, "omf")
    bins  = int(arg_or_default(5, 50))

    diag = open_diag(fpath)
    p = diagPlotter(diag)
    ax = p.plot_hist_conv(var, kx, param=param, bins=bins, title=f"{var}@{kx} – {param}")
    out = ensure_outdir() / f"01_hist_conv_{var}_kx{kx}_{param}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight")
    print(f"salvo: {out}")
