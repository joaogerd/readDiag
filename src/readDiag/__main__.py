"""
CLI: python -m readDiag <diag_file>
Shows a quick metadata summary. Use --help for usage.
"""
import sys
import argparse
from . import read_diag

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m readDiag", add_help=True)
    parser.add_argument("diag_file", nargs="?", help="Path to GSI diag file (conv or rad)")
    args = parser.parse_args(argv)
    if not args.diag_file:
        parser.print_help()
        return 0
    d = read_diag(args.diag_file)
    m = d.meta()
    print(f"File: {getattr(m, 'file_name', '?')}")
    print(f"Date: {getattr(m, 'date', '?')}")
    print(f"Kind: {getattr(m, 'kind', '?')}")
    try:
        if getattr(m, "kind", None) == "conv":
            print("Variables:", ", ".join(d.variables())[:200])
        else:
            print("Channels:", ", ".join(map(str, d.channels()))[:200])
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
