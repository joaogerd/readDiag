#!/usr/bin/env bash
set -euo pipefail

echo "[INFO] Applying quick compat fixes (adapters shim, io.utils shim, diagAccess export, api.read_any, CLI --help)"

# 0) Ensure branch
branch="feat/arch-split-io-plot-analysis"
if git rev-parse --verify "$branch" >/dev/null 2>&1; then
  git checkout "$branch"
fi

# 1) Shim for readDiag/io/utils.py (satisfy `from .utils import ...` inside io/reader.py)
mkdir -p src/readDiag/io
cat > src/readDiag/io/utils.py <<'PY'
"""
Shim module: `readDiag.io.utils`

This re-exports helpers from the package-level `_utils` so that
`from .utils import ...` inside `readDiag.io.reader` keeps working
after the refactor.
"""
from .._utils import *  # noqa: F401,F403
PY
git add src/readDiag/io/utils.py

# 2) Shim for `readDiag.adapters` to re-export AccessAdapter (tests use it)
mkdir -p src/readDiag/adapters
cat > src/readDiag/adapters/__init__.py <<'PY'
"""
Deprecated shim: `readDiag.adapters`

Re-exports the modern AccessAdapter from `readDiag.surface.access_adapter`.
"""
import warnings as _w
_w.warn("readDiag.adapters is deprecated; use readDiag.surface.access_adapter.AccessAdapter", DeprecationWarning, stacklevel=2)
from ..surface.access_adapter import AccessAdapter  # type: ignore
__all__ = ["AccessAdapter"]
PY
git add src/readDiag/adapters/__init__.py

# 3) Shim for `readDiag.legacy` to point to `gsidiag` (tests import it)
cat > src/readDiag/legacy.py <<'PY'
"""
Deprecated: `readDiag.legacy`
Redirects to `gsidiag.legacy_api` for old helpers.
"""
import warnings as _w
_w.warn("readDiag.legacy is deprecated; use gsidiag.legacy_api", DeprecationWarning, stacklevel=2)
from gsidiag.legacy_api import *  # type: ignore  # noqa: F401,F403
PY
git add src/readDiag/legacy.py

# 4) Export `diagAccess` from package root for legacy tests (`from readDiag import diagAccess`)
python - <<'PY'
from pathlib import Path
p = Path("src/readDiag/__init__.py")
src = p.read_text(encoding="utf-8")

inject = r'''
# -- Legacy export (deprecated): diagAccess for old tests/scripts --
try:
    from .io.reader import diagAccess as diagAccess  # type: ignore
except Exception:
    pass
if "__all__" in globals():
    if "diagAccess" not in __all__:
        __all__.append("diagAccess")
'''

if "diagAccess for old tests/scripts" not in src:
    src = src.rstrip() + "\n" + inject + "\n"
    p.write_text(src, encoding="utf-8")
    print("[OK] Injected diagAccess export into __init__.py")
else:
    print("[SKIP] diagAccess export already present")
PY
git add src/readDiag/__init__.py || true

# 5) Provide `read_any` in readDiag.api for tests that import it
python - <<'PY'
from pathlib import Path
p = Path("src/readDiag/api.py")
if p.exists():
    txt = p.read_text(encoding="utf-8")
    if "def read_any(" not in txt and "read_any =" not in txt:
        txt += """

# Back-compat helper expected by some tests
from . import read_diag as read_any  # type: ignore
"""
        p.write_text(txt, encoding="utf-8")
        print("[OK] Added read_any alias in readDiag.api")
    else:
        print("[SKIP] read_any already present in readDiag.api")
else:
    print("[WARN] src/readDiag/api.py not found; skipping")
PY
git add src/readDiag/api.py || true

# 6) Improve CLI: handle -h/--help without trying to open a file
python - <<'PY'
from pathlib import Path
p = Path("src/readDiag/__main__.py")
if p.exists():
    txt = p.read_text(encoding="utf-8").splitlines()
    out = []
    injected = False
    for line in txt:
        out.append(line)
        if line.strip().startswith("def main(") and not injected:
            out.append("  if argv and argv[0] in ('-h','--help'):\n    print('Usage: python -m readDiag <diag_file>'); return 0")
            injected = True
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("[OK] Patched CLI to support -h/--help")
else:
    print("[WARN] __main__.py not found; skipping")
PY
git add src/readDiag/__main__.py || true

git commit -m "[fix][compat] io.utils shim; adapters shim; legacy shim; diagAccess export; api.read_any; CLI --help"

echo "[DONE] Compat fixes applied."
echo
echo "[NEXT] Try again:"
echo "  python -c 'from readDiag import read_diag, diagPlotter, diagAccess; print("imports OK")'"
echo "  python -m readDiag --help || true"
echo "  pytest -q || true"
