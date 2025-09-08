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
        print("Usage: python 02_spatial_conv_auto.py <conv_file> <var> <kx>")
        sys.exit(1)
    path, var, kx = sys.argv[1], sys.argv[2], int(sys.argv[3])
    path = _resolve_default(path)
    api = rd.open_diagnostic(path)
    rp.plot_spatial_conv_auto(api, var, kx)
    out = f"02_spatial_conv_auto_{var}_kx{kx}.png"
    plt.savefig(out, bbox_inches="tight", dpi=150)
    print(f"[INFO] saved: {out}")

if __name__ == "__main__":
    main()
