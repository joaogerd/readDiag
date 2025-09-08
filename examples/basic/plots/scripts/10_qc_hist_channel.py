from __future__ import annotations
import os, sys
import matplotlib.pyplot as plt
import readDiag as rd
import readDiag.plotting as rp

def _resolve_default(path: str) -> str:
    env = os.environ.get("READDIAG_DATA")
    if env and not os.path.isabs(path):
        candidate = os.path.join(env, path)
        if os.path.exists(candidate):
            return candidate
    return path

def main():
    if len(sys.argv) < 4:
        print("Usage: python 10_qc_hist_channel.py <rad_file> <channel> <qc_col>")
        sys.exit(1)
    path, ch, qc_col = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    path = _resolve_default(path)
    api = rd.open_diagnostic(path)
    rp.plot_qc_hist_channel(api, ch, col=qc_col)
    out = f"10_qc_hist_channel_{qc_col}_ch{ch}.png"
    plt.savefig(out, bbox_inches="tight", dpi=150)
    print(f"[INFO] saved: {out}")

if __name__ == "__main__":
    main()
