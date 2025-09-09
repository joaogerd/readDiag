from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 09_omf_distribution_rad.py <diag_rad_path> [ch] [corrected(0/1)] [bins]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_amsua_n19_01.2024013018")
    ch    = int(arg_or_default(2, 1))
    corr  = bool(int(arg_or_default(3, 0)))
    bins  = int(arg_or_default(4, 50))
    ax = diagPlotter(open_diag(fpath)).plot_omf_distribution_rad(ch-1, corrected=corr, bins=bins)
    out = ensure_outdir() / f"09_omf_dist_ch{ch}_{'nbc' if corr else 'raw'}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
