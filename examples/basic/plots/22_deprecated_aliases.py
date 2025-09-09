from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter

"""
Demonstra as *aliases* deprecated: pcount, kxcount, vcount, plot_value_counts.
Uso:
  python 22_deprecated_aliases.py <diag_conv_path>
"""
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_conv_01.2024013018")
    p = diagPlotter(open_diag(fpath))

    # pcount(var)
    ax = p.pcount("t")
    out = ensure_outdir() / "22a_pcount_t.png"; ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")

    # kxcount()
    ax = p.kxcount()
    out = ensure_outdir() / "22b_kxcount.png"; ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")

    # vcount(var, kx=?, param=?, bins=?)
    ax = p.vcount("t", kx=120, param="omf", bins=30, color="C2")
    out = ensure_outdir() / "22c_vcount_t_kx120_omf.png"; ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")

    # plot_value_counts()
    ax = p.plot_value_counts()
    out = ensure_outdir() / "22d_plot_value_counts.png"; ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
