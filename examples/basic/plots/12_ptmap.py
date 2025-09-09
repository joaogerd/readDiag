from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 12_ptmap.py <diag_conv_path> [var] [kxs_csv or -]
Ex:
  python 12_ptmap.py data/diag_conv_01.2024013018 t 120,130,187
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "t")
    kxs   = arg_or_default(3, "-")
    klist = None if kxs == "-" else [int(k) for k in kxs.split(",") if k]
    p = diagPlotter(open_diag(fpath))
    try:
        ax = p.plot_ptmap(var, varType=klist, legend=True)
        out = ensure_outdir() / f"12_ptmap_{var}.png"
        ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
    except Exception as e:
        print(f"[aviso] {e}")
