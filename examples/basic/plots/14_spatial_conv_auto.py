from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "t")
    kx    = int(arg_or_default(3, 120))
    p = diagPlotter(open_diag(fpath))
    try:
        ax = p.plot_spatial_conv_auto(var, kx, area=[-90,-60,0,15])
        out = ensure_outdir() / f"14_spatial_conv_auto_{var}_kx{kx}.png"
        ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
    except RuntimeError as e:
        print(f"[aviso] Cartopy ausente? {e}")
