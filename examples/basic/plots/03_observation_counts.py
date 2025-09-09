from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
"""
Uso:
  python 03_observation_counts.py <diag_conv_path> [var]
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "t")
    diag = open_diag(fpath)
    p = diagPlotter(diag)
    ax = p.plot_observation_counts(var, title=f"Contagem por KX – {var}")
    out = ensure_outdir() / f"03_observation_counts_{var}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight")
    print(f"salvo: {out}")
