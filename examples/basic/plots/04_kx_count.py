from __future__ import annotations
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
import sys
"""
Uso:
  python 04_kx_count.py <diag_conv_path>
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    p = diagPlotter(open_diag(fpath))
    ax = p.plot_kx_count(title="Total de observações por KX")
    out = ensure_outdir() / "04_kx_count.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
