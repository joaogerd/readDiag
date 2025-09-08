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
        print("Usage: python 06_box_by_kx.py <conv_file> <var> <param> [kx_limit]")
        sys.exit(1)
    path, var, param = sys.argv[1], sys.argv[2], sys.argv[3]
    kx_limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
    path = _resolve_default(path)
    api = rd.open_diagnostic(path)
    rp.plot_box_by_kx(api, var, param, kx_limit=kx_limit)
    suffix = f"_top{kx_limit}" if kx_limit else ""
    out = f"06_box_by_kx_{param}_{var}{suffix}.png"
    plt.savefig(out, bbox_inches="tight", dpi=150)
    print(f"[INFO] saved: {out}")

if __name__ == "__main__":
    main()
