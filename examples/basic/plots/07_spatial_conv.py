from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 07_spatial_conv.py <diag_conv_path> [var] [kx] [param]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "t")
    kx    = int(arg_or_default(3, 120))
    param = arg_or_default(4, "omf")
    p = diagPlotter(open_diag(fpath))
    try:
        ax = p.plot_spatial_conv(var, kx, param=param, cmap="coolwarm", title=f"Mapa {var}@{kx} – {param}")
        out = ensure_outdir() / f"07_spatial_conv_{var}_kx{kx}_{param}.png"
        ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
    except RuntimeError as e:
        print(f"[aviso] Cartopy ausente? {e}")
