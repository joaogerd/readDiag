
# gsidiag — Installation Validation Test Suite

This `pytest` suite sanity‑checks a clean installation of **gsidiag** by:
- Verifying the package imports and emits a deprecation warning (legacy surface).
- Ensuring the bundled `table.yml` parses correctly and exposes expected entries.
- Exercising the public helpers in `gsidiag.legacy_api.plot` (`geoMap`, `getColor`) with a non‑interactive backend.

## Usage

```bash
python -m pip install -U pytest
pytest -q
```

> The tests include light stubs for optional dependencies (`readDiag` facade and `geopandas`) to keep the validation self‑contained. In environments where the real packages are installed, those will take precedence automatically.
