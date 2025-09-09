from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 11_unified_plot_rad.py <diag_rad_path> [param] [channel]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_amsua_n19_01.2024013018")
    param = arg_or_default(2, "omf")
    ch    = int(arg_or_default(3, 5))
    p = diagPlotter(open_diag(fpath))
    try:
        ax = p.plot(varName="amsua", varType="n19", param=param, channel=ch, cmap="coolwarm", s=4.0)
        out = ensure_outdir() / f"11_unified_rad_ch{ch}_{param}.png"
        ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
    except RuntimeError as e:
        print(f"[aviso] Cartopy ausente? {e}")
