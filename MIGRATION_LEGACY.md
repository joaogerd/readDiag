# Migration Guide — do LEGACY (`gsidiag`) para o NOVO (`readDiag`)

Este guia explica como sair da API legada (`gsidiag`) e migrar para a API nova e estável do pacote `readDiag`.

- **LEGACY**: tudo sob `gsidiag/` (classe `read_diag`, métodos `pfileinfo`, `summarize`, `tmsummarize`, etc.).  
  → **Suporte congelado**. Importar `gsidiag` emite `DeprecationWarning`.

- **NOVO**: tudo sob `readDiag/`.  
  → Entrada estável: `readDiag.open.open_diagnostic()` que retorna um **`DiagnosticAPI`**.  
  → Leitor baixo-nível moderno (não legacy): `readDiag.io.reader.diagAccess`.

> Regra: **`gsidiag` = legado; `readDiag` = novo**. `diagAccess` é **novo/baixo-nível**, não é legado.

---

## Tabela de mapeamento (antes → depois)

| Tarefa                                   | LEGACY (`gsidiag`)                                 | NOVO (`readDiag`)                                                                                     |
|------------------------------------------|----------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| Abrir arquivo (alto nível estável)       | `gd.read_diag("diag_conv_...")`                    | `api = rd.open_diagnostic("diag_conv_...")`  → `api: DiagnosticAPI`                                   |
| Tipo do dataset                          | `obj._file_type` (1 conv, 2 rad)                   | `api.kind() -> "conv" | "rad"`                                                                    |
| Metadados básicos                        | `obj._idate`, `obj._diag_file`                     | `api.meta() -> Metadata(file_name, date, kind, sensor, platform, ...)`                                |
| Variáveis e KX (conv)                    | `obj.varNames`, `obj._variablesList[var]`          | `api.variables()`, `api.kx_list(var)`                                                                  |
| DataFrame por var/kx (conv)              | `obj.obsInfo` (MultiIndex idate/var/kx)            | `api.frame_conv(var, kx)`                                                                              |
| Canais (rad)                              | (não padronizado; cada script fazia de um jeito)    | `api.channels()`, `api.frame_channel(ch)`                                                              |
| Sumários estatísticos (legado)           | `obj.summarize(varName="t", kx=120)`               | (faça direto em pandas: `api.frame_conv("t",120).describe()`)                                         |
| Plotagens legado (nomes antigos)         | `obj.kxcount()`, `obj.plot(..., param='omf')`      | `from readDiag.plotting.wrappers import plot_kx_count, plot_omf_map, plot_oma_map`                    |
| Encerrar                                 | `obj.close()`                                      | não necessário (sem efeito)                                                                            |

---

## Exemplos práticos

### 1) **Legado** (continua funcionando, mas com aviso)
```python
import gsidiag as gd

conv = gd.read_diag("data/diag_conv_01.2024013018")
conv.pfileinfo()
print(conv.summarize(varName="t", kx=120))
````

### 2) **Novo** (recomendado)

#### 2.1 Convencional

```python
import readDiag as rd

api = rd.open_diagnostic("data/diag_conv_01.2024013018")  # DiagnosticAPI
print(api.kind())           # "conv"
print(api.variables())      # ["t","q","u","v","ps", ...]

for var in api.variables():
    for kx in api.kx_list(var):
        df = api.frame_conv(var, kx)  # pandas.DataFrame com colunas padrão (lat, lon, omf, oma, etc.)
        # ... seu fluxo de análise/plot ...
```

#### 2.2 Radiância

```python
import readDiag as rd

api = rd.open_diagnostic("data/diag_amsua_n19_01.2024013018")
print(api.kind())         # "rad"
print(api.channels())     # [1, 2, 3, ...]
df_ch1 = api.frame_channel(1)
```

#### 2.3 Plotagens (wrappers simples)

```python
from readDiag.plotting.wrappers import plot_kx_count, plot_omf_map, plot_oma_map
import readDiag as rd

api = rd.open_diagnostic("data/diag_conv_01.2024013018")
plot_kx_count(api)
plot_omf_map(api, var="t", kx=120)
plot_oma_map(api, var="t", kx=120)
```

---

## FAQ

**“`diagAccess` é legacy?”**
Não. `readDiag.io.reader.diagAccess` é o **motor baixo-nível moderno**. O que é **legacy** é o **pacote `gsidiag`**.

**Quando `gsidiag` será removido?**
`gsidiag` está congelado e será removido numa major futura (planeje migrar para a 3.0). Até lá, ele segue disponível com `DeprecationWarning`.

**Preciso reescrever tudo?**
Não. Você pode migrar gradualmente: abra com `open_diagnostic`, use `DiagnosticAPI` nas partes novas e mantenha o legado onde não dá para mexer agora.

**Por que usar `DiagnosticAPI`?**
Porque é **estável**, independente do backend. O motor por baixo pode evoluir sem quebrar seu código.

---

## Checklist de migração

* [ ] Substituir `import gsidiag as gd` por `import readDiag as rd` **quando possível**.
* [ ] Trocar `read_diag(...)` por `open_diagnostic(...)`.
* [ ] Em conv: `obsInfo` → consultas com `api.frame_conv(var,kx)` e `df.describe()` quando quiser estatísticas.
* [ ] Em rad: usar `api.channels()` e `api.frame_channel(ch)`.
* [ ] Para mapas/contagens rápidas: usar `readDiag.plotting.wrappers`.
* [ ] Não referenciar objetos internos do backend; usar apenas `DiagnosticAPI`.

---

## Scripts/CLI

* **Novo**: `readDiag FILE` imprime metadados e lista var/kx ou canais.
* **Legacy**: `gsidiag FILE [--var VAR --kx KX]` preservado para compat.

---

## Política de deprecação

* Importar `gsidiag` emite `DeprecationWarning` com instrução de migração.
* `gsidiag` **congelado**: só correções críticas.
* Remoção na **major 3.x** (anunciada no CHANGELOG/README).


---

# Bloco para o README (cole na seção inicial ou após “Instalação”)

## Legacy vs New (LEIA ISTO)

- **LEGACY**: o pacote `gsidiag/` mantém a classe `read_diag` e métodos antigos.  
  Ele continua funcionando **apenas para compatibilidade** e emite `DeprecationWarning`.
- **NOVO**: o pacote `readDiag/` expõe uma entrada estável:
```python
  import readDiag as rd
  api = rd.open_diagnostic("path/to/diag_file")  # -> DiagnosticAPI

  if api.kind() == "conv":
      for v in api.variables():
          for kx in api.kx_list(v):
              df = api.frame_conv(v, kx)
  else:
      for ch in api.channels():
          df = api.frame_channel(ch)
````

* O leitor baixo-nível **moderno** é `readDiag.io.reader.diagAccess` (não é legacy).
* Para mapas/contagens rápidas:

```python
from readDiag.plotting.wrappers import plot_kx_count, plot_omf_map, plot_oma_map
plot_kx_count(api)
plot_omf_map(api, var="t", kx=120)
```

