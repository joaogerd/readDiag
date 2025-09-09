from __future__ import annotations
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
import sys
"""
Uso:
  python 06_kx_count_stacked.py <diag_conv_path> [vars_csv]
Ex:
  python 06_kx_count_stacked.py data/diag_conv_01.2024013018 t,q,uv
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    vars_csv = arg_or_default(2, "")
    vars_list = [v.strip() for v in vars_csv.split(",") if v.strip()] or None
    ax = diagPlotter(open_diag(fpath)).plot_kx_count_stacked(vars=vars_list, title="Stacked por KX/variável")
    out = ensure_outdir() / "06_kx_count_stacked.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
