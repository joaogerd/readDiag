from __future__ import annotations
import argparse
from .open import open_diagnostic

def cli() -> int:
    p = argparse.ArgumentParser(prog="readDiag")
    p.add_argument("file", help="diagnostic file (conv or rad)")
    args = p.parse_args()

    api = open_diagnostic(args.file)
    m = api.meta()
    print(f"{m.kind} | date={m.date} | file={m.file_name}")
    if m.kind == "conv":
        for v in api.variables():
            kx = api.kx_list(v)
            print(f"  var={v} kx={kx}")
    else:
        print(f"  channels={api.channels()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(cli())

