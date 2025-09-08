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
    path = sys.argv[1] if len(sys.argv) > 1 else "data/diag_conv_01.2024013018"
    path = _resolve_default(path)
    api = rd.open_diagnostic(path)
    rp.plot_kx_count(api)
    out = "01_kx_count.png"
    plt.savefig(out, bbox_inches="tight", dpi=150)
    print(f"[INFO] saved: {out}")

if __name__ == "__main__":
    main()
