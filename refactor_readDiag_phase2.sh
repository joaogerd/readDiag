\
#!/usr/bin/env bash
set -euo pipefail

echo "[INFO] readDiag refactor — Phase 2: finish split and isolate legacy"

# Check repo root
if [ ! -d ".git" ]; then
  echo "[ERROR] Run this script from the repository root (where .git is)"
  exit 1
fi

branch="feat/arch-split-io-plot-analysis"
if git rev-parse --verify "$branch" >/dev/null 2>&1; then
  echo "[INFO] Using existing branch $branch"
  git checkout "$branch"
else
  echo "[INFO] Creating branch $branch"
  git checkout -b "$branch"
fi

mkdir -p src/gsidiag
mkdir -p tests/legacy

# Move legacy-prone files if they exist
if [ -e src/readDiag/legacy.py ]; then
  git mv src/readDiag/legacy.py src/gsidiag/legacy_api.py
fi
if [ -e src/readDiag/impact_original.py ]; then
  git mv src/readDiag/impact_original.py src/gsidiag/impact_legacy.py
fi
if [ -e src/readDiag/conftest.py ]; then
  git mv src/readDiag/conftest.py tests/legacy/conftest.py
fi

# Internal utils reshuffle (keep public compat via thin re-export with warning)
if [ -e src/readDiag/utils_plotting.py ]; then
  mkdir -p src/readDiag/plotting
  git mv src/readDiag/utils_plotting.py src/readDiag/plotting/_utils.py
fi
if [ -e src/readDiag/utils_integrity.py ]; then
  mkdir -p src/readDiag/io
  git mv src/readDiag/utils_integrity.py src/readDiag/io/integrity.py
fi
if [ -e src/readDiag/utils.py ]; then
  git mv src/readDiag/utils.py src/readDiag/_utils.py
  # add a public shim back
  cat > src/readDiag/utils.py <<'PY'
"""
Deprecated public utils shim.
Use `from readDiag._utils import ...` instead.
"""
import warnings as _w
_w.warn("readDiag.utils is deprecated; import from readDiag._utils", DeprecationWarning, stacklevel=2)
from ._utils import *  # noqa: F401,F403
PY
  git add src/readDiag/utils.py
fi

# Replace top-level api.py with clean re-export (if exists)
if [ -e src/readDiag/api.py ]; then
  cat > src/readDiag/api.py <<'PY'
"""
Public surface contract re-export.
Prefer: `from readDiag.surface.api import DiagnosticAPI`
"""
from .surface.api import *  # noqa: F401,F403
PY
  git add src/readDiag/api.py
fi

# Replace top-level open.py with clean opener alias (if exists)
if [ -e src/readDiag/open.py ]; then
  cat > src/readDiag/open.py <<'PY'
"""
Backward-compat opener alias.
Prefer: `from readDiag import read_diag` or `open_diagnostic`.
"""
from .io.reader import open_diagnostic as open_diagnostic  # type: ignore
read_diag = open_diagnostic
__all__ = ["open_diagnostic", "read_diag"]
PY
  git add src/readDiag/open.py
fi

# Ensure __main__.py provides a minimal CLI aligned to modern API
if [ -e src/readDiag/__main__.py ]; then
  cat > src/readDiag/__main__.py <<'PY'
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
PY
  git add src/readDiag/__main__.py
fi

# Add deprecation banner to gsidiag/__init__.py
cat > src/gsidiag/__init__.py <<'PY'
"""
Legacy compatibility package for old gsidiag-style imports.

This package provides shims and adapters to help migrate to the modern
`readDiag` API. New code should import from `readDiag` directly.
"""
import warnings as _w
_w.warn(
    "You are importing from `gsidiag` (legacy). Please migrate to `readDiag`. "
    "See MIGRATION_LEGACY.md for details.",
    DeprecationWarning, stacklevel=2
)

# Re-export conveniences if needed by old scripts (add minimally):
try:
    from readDiag import read_diag, open_diagnostic  # type: ignore
except Exception:
    pass
PY
git add src/gsidiag/__init__.py

# Ensure package-data includes YAML files in readDiag root (table.yml)
if [ -e pyproject.toml ]; then
python3 - <<'PY'
from pathlib import Path
p = Path("pyproject.toml")
txt = p.read_text(encoding="utf-8")
if "[tool.setuptools.package-data]" not in txt:
    txt += (
        '\n[tool.setuptools.package-data]\n'
        'readDiag = ["*.yml", "*.yaml", "*.json", "*.csv"]\n'
    )
    p.write_text(txt, encoding="utf-8")
    print("[OK] Added [tool.setuptools.package-data] for YAML/CSV at package root")
else:
    print("[SKIP] package-data already present")
PY
fi

git add -A
git commit -m "[refactor][phase2] Move remaining legacy to gsidiag; re-export shims; package-data for YAML; minimal CLI"
echo "[DONE] Phase 2 commit created on $branch"

echo
echo "[NEXT] Validate imports and basic CLI:"
echo "  python -c 'from readDiag import read_diag, diagPlotter; print(\"ok\")'"
echo "  python -m readDiag --help || true"
