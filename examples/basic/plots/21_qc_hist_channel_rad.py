from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 21_qc_hist_channel.py <diag_rad_path> [channel] [param]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_amsua_n19_01.2024013018")
    ch    = int(arg_or_default(2, 4))
    param = arg_or_default(3, "idqc")  # exemplo de alias legado
    ax = diagPlotter(open_diag(fpath)).plot_qc_hist_channel(ch, param=param)
    out = ensure_outdir() / f"21_qc_hist_channel_{ch}_{param}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
