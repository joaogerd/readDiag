\
#!/usr/bin/env bash
set -euo pipefail

echo "[INFO] readDiag refactor helper — split io/plotting/analysis and isolate legacy"

# Detect repo root
if [ ! -d ".git" ]; then
  echo "[ERROR] Run this script from the repository root (where .git is)"
  exit 1
fi

branch="feat/arch-split-io-plot-analysis"
if git rev-parse --verify "$branch" >/dev/null 2>&1; then
  echo "[INFO] Branch $branch already exists."
else
  echo "[INFO] Creating branch $branch"
  git checkout -b "$branch"
fi

# Ensure src layout exists
mkdir -p src/readDiag/{io,surface,plotting,analysis}
mkdir -p src/gsidiag

# Safe move helper: mv if exists and not already in target
safemv() {
  if [ -e "$1" ]; then
    local tgt="$2"
    if [ -e "$tgt" ]; then
      echo "[SKIP] Target exists: $tgt"
    else
      echo "[MV] $1 -> $tgt"
      git mv "$1" "$tgt"
    fi
  else
    echo "[MISS] $1 (not found, skip)"
  fi
}

# Try to move common files if they exist (best-effort)
# Reader/IO
safemv src/readDiag/reader.py           src/readDiag/io/reader.py
safemv src/readDiag/conv.py             src/readDiag/io/conv_reader.py
safemv src/readDiag/rad.py              src/readDiag/io/rad_reader.py
safemv src/readDiag/backends            src/readDiag/io/backends

# Surface/Adapters
safemv src/readDiag/surface.py          src/readDiag/surface/api.py
safemv src/readDiag/adapters/access.py  src/readDiag/surface/access_adapter.py
safemv src/readDiag/adapters            src/readDiag/surface/adapters

# Plotting
safemv src/readDiag/plotting.py         src/readDiag/plotting/core.py
safemv src/readDiag/style.py            src/readDiag/plotting/style.py

# Analysis
safemv src/readDiag/impact.py           src/readDiag/analysis/impact.py
safemv src/readDiag/stats.py            src/readDiag/analysis/stats.py
safemv src/readDiag/aggregations.py     src/readDiag/analysis/aggregations.py
safemv src/readDiag/analysis_utils.py   src/readDiag/analysis/utils.py

# Copy new wrappers module (won't overwrite existing)
if [ ! -e src/readDiag/plotting/wrappers.py ]; then
  echo "[ADD] plotting/wrappers.py"
  mkdir -p src/readDiag/plotting
  cp readDiag_plotting_wrappers.py src/readDiag/plotting/wrappers.py
  git add src/readDiag/plotting/wrappers.py
fi

# Add MIGRATION_LEGACY.md
if [ ! -e MIGRATION_LEGACY.md ]; then
  echo "[ADD] MIGRATION_LEGACY.md"
  cp MIGRATION_LEGACY.md ./MIGRATION_LEGACY.md
  git add MIGRATION_LEGACY.md
fi

# 1) Recria __init__.py moderno de forma segura
python - <<'PY'
from pathlib import Path
p = Path("src/readDiag/__init__.py")
p.parent.mkdir(parents=True, exist_ok=True)

content = r'''
# readDiag public API (clean, no legacy inside this package)

# -- Surface contract/adapter --
try:
    from .surface.access_adapter import AccessAdapter  # type: ignore
except Exception as _e:
    AccessAdapter = None  # type: ignore

try:
    from .surface.api import DiagnosticAPI  # type: ignore
except Exception:
    class DiagnosticAPI: ...  # type: ignore

# -- Low-level opener (fallbacks) --
_open_impl = None
try:
    # Preferred: a factory in io/reader.py
    from .io.reader import open_diagnostic as _open_impl  # type: ignore
except Exception:
    pass

if _open_impl is None:
    try:
        # Alt name some trees use
        from .io.reader import read_diag as _open_impl  # type: ignore
    except Exception:
        pass

if _open_impl is None:
    try:
        # Last-resort: build from diagAccess class
        from .io.reader import diagAccess  # type: ignore
        def _open_impl(path: str):
            return diagAccess(path)
    except Exception:
        # If nothing is available, make it explicit at call time
        def _open_impl(path: str):
            raise RuntimeError("No opener found in readDiag.io.reader; expected open_diagnostic/read_diag/diagAccess")

def open_diagnostic(path: str) -> "DiagnosticAPI":
    if AccessAdapter is None:
        raise RuntimeError("AccessAdapter not available (readDiag.surface.access_adapter missing)")
    backend = _open_impl(path)
    return AccessAdapter(backend)

# Friendly alias
read_diag = open_diagnostic

# -- Plotting --
try:
    from .plotting.core import diagPlotter  # type: ignore
except Exception:
    class diagPlotter: ...  # type: ignore

# Optional convenience wrappers (no legacy; just thin helpers)
try:
    from .plotting.wrappers import (
        plot_kx_count, plot_omf_map, plot_oma_map,
        plot_histogram_omf, plot_histogram_oma, plot_scatter,
    )  # type: ignore
except Exception:
    # Keep package importable even if wrappers are not present
    def _missing(*args, **kwargs):
        raise RuntimeError("Plot wrappers not available")
    plot_kx_count = plot_omf_map = plot_oma_map = \
    plot_histogram_omf = plot_histogram_oma = plot_scatter = _missing

__all__ = [
    "DiagnosticAPI","open_diagnostic","read_diag",
    "AccessAdapter","diagPlotter",
    "plot_kx_count","plot_omf_map","plot_oma_map",
    "plot_histogram_omf","plot_histogram_oma","plot_scatter",
]
'''
p.write_text(content.strip() + "\n", encoding="utf-8")
print("[OK] wrote src/readDiag/__init__.py")
PY

# 2) Garante os optional-dependencies no pyproject.toml
python - <<'PY'
from pathlib import Path
p = Path("pyproject.toml")
if not p.exists():
    print("[WARN] pyproject.toml not found; skipping extras patch")
else:
    txt = p.read_text(encoding="utf-8")
    if "[project.optional-dependencies]" not in txt:
        txt += (
            "\n[project.optional-dependencies]\n"
            "maps = [\"cartopy>=0.22,<0.26\", \"geopandas>=1.0,<1.3\"]\n"
            "docs = [\"mkdocs-material\", \"mkdocs-static-i18n\", \"mkdocstrings[python]\", \"griffe\", \"pymdown-extensions\"]\n"
            "dev = [\"pytest\", \"pytest-cov\", \"ruff\", \"black\", \"mypy\"]\n"
        )
        p.write_text(txt, encoding="utf-8")
        print("[OK] Added optional dependencies to pyproject.toml")
    else:
        print("[SKIP] optional-dependencies already present")
PY

# Final status and commit
git add -A
git commit -m "[refactor] Split io/surface/plotting/analysis; add plotting wrappers; add MIGRATION_LEGACY.md; optional deps"
echo "[DONE] Commit created on $branch"

echo
echo "[NEXT] Run tests and try basic imports:"
echo "  - pytest -q"
echo "  - python -c 'from readDiag import read_diag, diagPlotter; print(\"ok\")'"
