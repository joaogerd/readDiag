from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 13_pvmap.py <diag_conv_path> [vars_csv or -]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    vars_csv = arg_or_default(2, "t,q")
    vars_list = None if vars_csv == "-" else [v.strip() for v in vars_csv.split(",") if v.strip()]
    p = diagPlotter(open_diag(fpath))
    try:
        ax = p.plot_pvmap(vars_list, legend=True)
        out = ensure_outdir() / "13_pvmap.png"
        ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
    except Exception as e:
        print(f"[aviso] {e}")
