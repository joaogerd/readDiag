# Changelog

Todas as mudanças notáveis neste projeto serão documentadas aqui.  
O formato segue as recomendações do [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) e versionamento semântico (SemVer).

---

## [2.0.0-rc.1] - 2025-09-02
### ⚠️ Breaking changes
- **API estável** introduzida via `readDiag.adapters`:
  - `AccessAdapter` — camada estável sobre `diagAccess`.
  - `LegacyCompatAdapter` — compatibilidade para backends legados e fakes de teste.
- **Removido**: `src/readDiag/diagAccess_legacy.py`.
- **Plotting**:
  - Métodos decorados com `@check_kind("conv" | "rad")`.
  - `diagPlotter` agora detecta automaticamente API nova vs legado e escolhe o adapter adequado.
- **Utils**:
  - `check_kind` aceita `kind()` callables.
  - Helpers de endianness tornaram-se **idempotentes** (compatíveis com NumPy <2 e ≥2).

### 🚀 Melhorias
- `LegacyCompatAdapter` faz *best-effort* para inferir `kind`, `date`, `n_channels`, `n_obs`.
- Shims de legado preservados: `get_variables`, `get_kx_list`, `get_dataframe(...)` etc.
- Novos exemplos em `examples/`:
  - `01_quickstart_conv.py`, `02_quickstart_rad.py`, `03_plots_conv.py`, `04_plots_rad.py`, …
  - `07_legacy_compat.py` mostra migração a partir do legado.
- Testes abrangentes para `AccessAdapter` e `LegacyCompatAdapter`.

### 🛠 Refatorações
- `readDiag/api.py` e `__init__.py` expõem a nova API.
- `reader.py`: acessos mais seguros para fakes sem `_data_frame`.
- `plotting.py`: melhor *fallback* para chamadas antigas sem quebrar imagens já geradas.

### 🧹 Remoções
- Exemplos/scritps antigos e material obsoleto no diretório `examples/old/` e correlatos.

---

## [1.x] - Histórico
### 1.0.0 – 1.9.x
- Versões iniciais do `readDiag`, baseadas em `diagAccess` diretamente.
- Suporte a arquivos convencionais (`conv`) e de radiância (`rad`).
- Primeiras rotinas de *plotting* e *impact analysis*.
- Estrutura de testes iniciais para garantir compatibilidade mínima.

---

### Notas de migração
- Código que dependia de `diagAccess_legacy.py` deve migrar para:
  - **Novo**: `AccessAdapter(diagAccess(...))` (preferido), ou
  - **Compat**: `LegacyCompatAdapter(...)` quando ainda não for possível alterar o backend.
- Em `plotting`, evite usar métodos “crus” do backend; prefira `diagPlotter(backend_ou_adapter)`.

> Esta versão é uma *Release Candidate*; a API estável pode sofrer pequenos ajustes antes do 2.0 final.
