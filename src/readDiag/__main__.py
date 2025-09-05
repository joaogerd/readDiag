"""
CLI: python -m readDiag <diag_file>
Prints quick metadata summary.
"""
import sys
from . import read_diag

def main(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if not argv:
    print("Usage: python -m readDiag <diag_file>")
    return 2
  d = read_diag(argv[0])
  m = d.meta()
  print(f"File: {m.file_name}")
  print(f"Date: {m.date}")
  print(f"Kind: {m.kind}")
  if m.kind == "conv":
    print("Variables:", ", ".join(d.variables())[:200])
  else:
    print("Channels:", ", ".join(map(str, d.channels()))[:200])
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
