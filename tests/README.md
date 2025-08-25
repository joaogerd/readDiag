tests/
  conftest.py                 ← fixtures e utilidades (backend Agg, caminhos, helpers)
  test_api_read_any.py        ← API funcional (read_any) conv/rad
  test_legacy_compat.py       ← read_diag + pcount/vcount/kxcount + impacto
  test_plotting_aliases.py    ← aliases deprecados e métodos modernos
  test_endianness_rad.py      ← sanity para endian (rad)
  test_read_baseline.py       ← leitura conv/rad (ajustado)
  test_read_radiance.py       ← estrutura radiância (ajustado)
  test_error_cases.py         ← casos de erro (ajustado)
  test_benchmark.py           ← benchmarks (opcional, marker)
pytest.ini
Makefile

