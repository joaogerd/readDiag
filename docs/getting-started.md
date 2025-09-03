# Getting Started with readDiag
> Uma introdução passo a passo para quem nunca usou o **readDiag** (leitura de diagnósticos do GSI), com exemplos práticos e comandos prontos para copiar e colar.

!!! tip "O que é o readDiag?"
    O **readDiag** é um pacote Python que lê arquivos de diagnóstico do **GSI** (convencionais e radiâncias), gera *plots* e calcula métricas de impacto (TI/FI/FBI). Ele oferece uma API moderna (`diagAccess`, `diagPlotter`, `ImpactAnalyzer`) e também uma camada de compatibilidade com a API antiga (`read_diag(...).plot/ptmap/pvmap`).

---

## 1) Requisitos
- **Python 3.10+**
- Recomendado: um ambiente isolado (Conda/Miniforge ou venv)
- Dependências principais são instaladas via `pip`. Para mapas (opcional), instale também **cartopy**.

```bash
# Exemplo com conda/miniforge
conda create -n readdiag python=3.11 -y
conda activate readdiag
```

---

## 2) Instalação rápida (usuário)
Se o pacote já estiver publicado no seu índice (PyPI ou artefato interno), algo assim deve funcionar:

```bash
pip install readDiag
```

Se você estiver trabalhando com o repositório local (clonado), use a instalação em modo *editable*:

```bash
# Dentro do diretório do projeto
pip install -e .
```

### Verifique a instalação
```bash
python -c "import readDiag; readDiag.show_versions()"
# ou, se seu pacote já tiver CLI principal habilitado:
python -m readDiag --show-versions
```

---

## 3) Preparando dados de exemplo
Os exemplos assumem uma pasta `data/` com arquivos GSI como:
- `diag_conv_01.YYYYMMDDHH`
- `diag_conv_03.YYYYMMDDHH`
- `diag_amsua_*.YYYYMMDDHH` (radiâncias)

Você pode:
- **Colocar** seus arquivos em `data/` na raiz do projeto, **ou**
- Definir uma variável de ambiente para apontar para seus dados:
  ```bash
  export READDIAG_DATA=/caminho/para/meus/diagnosticos
  ```

!!! note "Sobre OMF/OMA"
    - **OMF** (*obs minus fcst*, O−B): diferença entre observação e *background* (pré-análise).
    - **OMA** (*obs minus analysis*, O−A): diferença entre observação e análise (pós-análise).
    - Para impacto (TI/FI/FBI), normalmente pareamos arquivos **OMF** e **OMA** do mesmo ciclo.

---

## 4) Rodando os exemplos prontos
Os arquivos abaixo vieram com o seu pacote (ou foram enviados). Execute a partir da raiz do projeto.

### 4.1 Convencional (Quickstart)
```bash
python examples/01_quickstart_conv.py --file data/diag_conv_01.2020010100 --save
```
O *script* abre o arquivo, lista variáveis e KX, plota:
- **Contagem por KX** (barras empilhadas por variável)
- **Histogramas** (por variável/KX e por métrica, como `omf`)
- **Séries temporais** (se houver múltiplos ciclos)
- **Mapa espacial** (opcional; requer `cartopy`) com uma máscara simples (`iuse == 1`, por exemplo)

As figuras são salvas em `outputs/examples/` se `--save` for usado; sem `--save`, as janelas de *plot* são exibidas.

### 4.2 Radiância (Quickstart)
```bash
python examples/02_quickstart_rad.py --file data/diag_amsua_n15_01.2020010100 --save
```
Gera, por exemplo:
- **Estatísticas por canal** (média, desvio de `omf`, etc.)
- **Distribuição O−F** para um canal específico

### 4.3 Galerias de plots
```bash
# Convencional
python examples/03_plots_conv.py --file data/diag_conv_01.2020010100 --save

# Radiância
python examples/04_plots_rad.py  --file data/diag_amsua_n15_01.2020010100 --save
```

### 4.4 Impacto (TI/FI/FBI) — básico
```bash
python examples/05_impact_basic.py   --omf data/diag_conv_01.2020010100   --oma data/diag_conv_03.2020010100   --outdir outputs/examples --save
```
- Calcula **TI**, **FI** e **FBI** por tipo/variável/KX.
- Salva um **CSV** (`impact_metrics.csv`) e gráficos de barras dos *top‑k* contribuintes.

### 4.5 Impacto — séries & comparação de experimentos
```bash
python examples/06_impact_series.py   --omf-list data/diag_conv_01.2024013000 data/diag_conv_01.2024013012 ...   --oma-list data/diag_conv_03.2024013000 data/diag_conv_03.2024013012 ...   --compare-exp1 data/diag_amsua_n18_01.2024013018:data/diag_amsua_n18_03.2024013018 ...   --compare-exp2 data/diag_amsua_n18_01.2024013018:data/diag_amsua_n19_03.2024013018 ...   --outdir outputs/examples --save
```
- Constrói **médias e desvio padrão** ao longo de vários ciclos.
- Compara dois conjuntos de pares (EX: **EXP1** vs **EXP2**) e plota a diferença.

### 4.6 Compatibilidade com a API legada
```bash
python examples/07_legacy_compat.py --file data/diag_conv_01.2020010100 --save
```
Mostra como usar `read_diag(...).plot/ptmap/pvmap`, útil para migração gradual.

### 4.7 Mapa de varredura (swath) AMSU‑A
```bash
python examples/08_plot_amsua_swath.py
```
Requer `cartopy`. Plota *scatter* de `tb_obs` numa projeção geográfica.

### 4.8 Explorar DataFrame de conv (vars/KX/uso)
```bash
python examples/09_show_conv_dataframe.py   --file data/diag_conv_01.2024013018   --var uv ps t q --usage all --limit 5
```
- Lista variáveis e KX disponíveis.
- Mostra *heads* de DataFrame e permite **filtrar por uso** (pré/pós) detectando automaticamente `iuse` ou `iusev`.

### 4.9 Filtros de uso (pré/pós) com utilitários
```bash
python examples/11_usage_filter_demo.py   --file data/diag_conv_01.2024013018   --var uv --mode post:assimilated --stage auto --field auto --limit 500
```
Demonstra **decode_iuse / attach_iuse_decoded / apply_usage_filter** para cenários reais.

### 4.10 Tudo em um (kitchen sink)
```bash
python examples/kitchen_sink.py   --conv data/diag_conv_01.2020010100   --rad  data/diag_amsua_n15_01.2020010100   --impact-omf data/diag_conv_01.2020010100   --impact-oma data/diag_conv_03.2020010100   --outdir outputs/examples --save
```

---

## 5) Usando a API no seu próprio código
A forma mais direta é abrir um arquivo com `diagAccess` e entregar para o `diagPlotter`.

```python
from readDiag import diagAccess, diagPlotter, PlotConfig

d = diagAccess("data/diag_conv_01.2024013018")
p = diagPlotter(d, config=PlotConfig(style="paper"))  # estilo opcional

# Descobrir o que há no arquivo
vars_disponiveis = d.get_variables()          # ex.: ["uv", "t", "q", "ps", ...]
kx_para_uv      = d.get_kx_list("uv")        # lista de códigos KX para aquela variável

# Um exemplo de histograma para UV, primeiro KX disponível
kx = int(kx_para_uv[0])
ax = p.plot_hist_conv(var="uv", kx=kx, param="omf", bins=50, mask="iuse==1")
ax.set_title(f"Distribuição O−F (uv, kx={kx})")
ax.figure.savefig("uv_kx_hist.png", bbox_inches="tight")
```

### Radiâncias (por canal)
```python
d = diagAccess("data/diag_amsua_n15_01.2024013018")
p = diagPlotter(d)

# Estatísticas por canal (média O−F, por exemplo)
ax = p.plot_channel_stats_rad(metric="omf", agg="mean")
ax.figure.savefig("rad_mean_omf.png", bbox_inches="tight")

# Distribuição O−F para um canal específico
ax = p.plot_omf_distribution_rad(channel_index=0, corrected=False, bins=50)
ax.figure.savefig("rad_ch0_hist_omf.png", bbox_inches="tight")
```

### Impacto (TI/FI/FBI)
```python
from readDiag import ImpactAnalyzer

ia = ImpactAnalyzer(omf_file="data/diag_conv_01.2024013000",
                    oma_file="data/diag_conv_03.2024013000",
                    var="uv")  # opcional: restringir a uma variável
df = ia.compute_all_metrics()   # retorna DataFrame com TI/FI/FBI
ax = ia.plot_impact_bar(metric="TI", top_k=10)
ax.figure.savefig("impact_ti.png", bbox_inches="tight")
```

### Comparação de experimentos
```python
from readDiag import ExperimentComparator, ComparisonPlotter

exp1 = [("diag_amsua_n18_01.2024013018", "diag_amsua_n18_03.2024013018"), ...]
exp2 = [("diag_amsua_n18_01.2024013018", "diag_amsua_n19_03.2024013018"), ...]

comp = ExperimentComparator(exp1, exp2, var="uv")  # var opcional
comp.compare()
plotter = ComparisonPlotter(comp.comparison_df)
ax = plotter.plot_diff(metric="mean_diff")  # exemplo de métrica comparativa
ax.figure.savefig("impact_comparison.png", bbox_inches="tight")
```

---

## 6) Máscaras, “uso” (iuse/iusev) e estágios (pré/pós)
Os arquivos *conv* podem trazer diferentes convenções de “uso”:
- **Pré‑análise** (*background*): coluna típica `iuse` (ou `use`).
- **Pós‑análise**: colunas como `iusev`/`analysis_use`.

O readDiag detecta **automaticamente** qual coluna usar nas funções e utilitários mais novos. Exemplos de filtros:
- `iuse == 1` → pontos usados na análise
- `iuse == 2` → monitorados (não assimilados)
- `iqc == 0` → passou controle de qualidade básico no GSI

Você pode passar **expressões de máscara** nas funções de *plot*, por exemplo:
```python
ax = p.plot_spatial_conv("uv", kx=120, param="omf", mask="iuse==1 and iqc==0")
```

!!! tip "Demonstração completa"
    Veja `examples/11_usage_filter_demo.py` para um fluxo fim‑a‑fim utilizando `decode_iuse`, `attach_iuse_decoded` e `apply_usage_filter`.

---

## 7) Erros comuns e soluções
- **`ModuleNotFoundError: cartopy`**: instale `cartopy` para mapas geográficos, ou rode os exemplos com `--save` (eles pulam o mapa se não houver cartopy).
- **Dados ausentes**: confira o caminho (`--file`) ou use `READDIAG_DATA` para apontar para seus diagnósticos.
- **Cores/estilo**: use `PlotConfig(style="paper"|"notebook"|...)` para padronizar visual.
- **Compatibilidade legada**: se tiver *scripts* antigos com `read_diag(...)`, use `examples/07_legacy_compat.py` como referência de migração.

---

## 8) Próximos passos
- Integre o `readDiag` nos seus *pipelines* (ex.: SLURM/HPC) para gerar relatórios periódicos.
- Compare sensores/experimentos com `ExperimentComparator`.
- Gere **páginas de relatório** com figuras + CSV (ex.: `05_impact_basic.py`).

---

## 9) Referência rápida (o que usar quando)
- **Explorar conv**: `01_quickstart_conv.py`, `09_show_conv_dataframe.py`
- **Explorar rad**: `02_quickstart_rad.py`, `04_plots_rad.py`, `08_plot_amsua_swath.py`
- **Impacto**: `05_impact_basic.py`, `06_impact_series.py`
- **Legado**: `07_legacy_compat.py`
- **Tudo junto**: `kitchen_sink.py`

---

## 10) Créditos e licença
- Projeto: **readDiag**
- Licença padrão do repositório (ex.: **LGPL v3**). Verifique `LICENSE` no projeto.