from __future__ import annotations
import sys
from _common import open_diag, ensure_outdir, arg_or_default, PROJECT_ROOT
from readDiag.plotting.core import diagPlotter
if __name__ == "__main__":
    fpath = arg_or_default(1, PROJECT_ROOT / "data/diag_amsua_n19_01.2024013018")
    ch    = int(arg_or_default(2, 10))
    p = diagPlotter(open_diag(fpath))
    try:
        ax = p.plot_abs_omf_map_channel(ch, s=1)
        out = ensure_outdir() / f"20_abs_omf_map_channel_{ch}.png"
        ax.get_figure().savefig(out, dpi=150, bbox_inches="tight"); print(f"salvo: {out}")
    except Exception as e:
        print(f"[aviso] {e}")
