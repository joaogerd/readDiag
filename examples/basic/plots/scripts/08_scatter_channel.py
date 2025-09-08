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
    if len(sys.argv) < 5:
        print("Usage: python 08_scatter_channel.py <rad_file> <channel> <xcol> <ycol>")
        sys.exit(1)
    path, ch, xcol, ycol = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    path = _resolve_default(path)
    api = rd.open_diagnostic(path)
    rp.plot_scatter_channel(api, ch, x=xcol, y=ycol)
    out = f"08_scatter_channel_{xcol}_vs_{ycol}_ch{ch}.png"
    plt.savefig(out, bbox_inches="tight", dpi=150)
    print(f"[INFO] saved: {out}")

if __name__ == "__main__":
    main()
