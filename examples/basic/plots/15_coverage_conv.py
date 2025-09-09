from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    var   = arg_or_default(2, "t")
    kx    = int(arg_or_default(3, 120))
    ax = diagPlotter(open_diag(fpath)).plot_coverage_conv(var, kx, s=2)
    out = ensure_outdir() / f"15_coverage_{var}_kx{kx}.png"
    ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
