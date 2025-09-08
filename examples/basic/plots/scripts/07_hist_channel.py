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
    if len(sys.argv) < 3:
        print("Usage: python 07_hist_channel.py <rad_file> <channel> [param]")
        sys.exit(1)
    path, ch = sys.argv[1], int(sys.argv[2])
    param = sys.argv[3] if len(sys.argv) > 3 else None
    path = _resolve_default(path)
    api = rd.open_diagnostic(path)
    rp.plot_hist_channel(api, ch, param=param)
    p = param or "auto"
    out = f"07_hist_channel_ch{ch}_{p}.png"
    plt.savefig(out, bbox_inches="tight", dpi=150)
    print(f"[INFO] saved: {out}")

if __name__ == "__main__":
    main()
