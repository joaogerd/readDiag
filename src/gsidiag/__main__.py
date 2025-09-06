from __future__ import annotations
import argparse
from .legacy_api import read_diag

def cli() -> int:
    p = argparse.ArgumentParser(prog="gsidiag (legacy)")
    p.add_argument("file", help="diagnostic file (conv or rad)")
    p.add_argument("--var", help="variable (conv only)")
    p.add_argument("--kx", type=int, help="kx (conv only)")
    args = p.parse_args()

    rd = read_diag(args.file)
    rd.pfileinfo()
    if args.var:
        print(rd.summarize(varName=args.var, kx=args.kx))
    return 0

if __name__ == "__main__":
    raise SystemExit(cli())

