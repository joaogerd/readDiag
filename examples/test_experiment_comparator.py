"""
Exemplo completo de uso das classes ImpactAnalyzer, ExperimentComparator e ComparisonPlotter
para comparar o impacto de observações entre duas plataformas de radiância (AMSUA METOP-A vs N18)
e para dados convencionais (ex: temperatura).

Requisitos:
- As classes precisam estar disponíveis em seu pacote readDiag
- Ajuste os caminhos dos arquivos conforme sua estrutura de diretórios
- Instale matplotlib, pandas, numpy, scipy, statsmodels, scikit-learn

Execute: python example_compare_impact.py
"""

import matplotlib.pyplot as plt
from readDiag import ImpactAnalyzer, ExperimentComparator, ComparisonPlotter

# -------------------------------
# Comparação de Plataformas AMSUA
# -------------------------------

# Defina as listas de arquivos (omf, oma) para cada experimento (plataforma)
exp1_rad = [
    ("data/diag_amsua_n18_01.2020010100", "data/diag_amsua_n18_03.2020010100"),
]
exp2_rad = [
    ("data/diag_amsua_n15_01.2020010100", "data/diag_amsua_n15_03.2020010100"),
]

# Crie o comparador e rode a análise
comparator_rad = ExperimentComparator(exp1_rad, exp2_rad)
comparator_rad.compare()

# Plote o gráfico de diferença de impacto por canal
plotter_rad = ComparisonPlotter(comparator_rad.comparison_df)
ax_rad = plotter_rad.plot_diff(metric="diff")
plt.title("AMSUA Impact Comparison: METOP-A vs N18")
plt.tight_layout()
plt.show()

# ---------------------------------------
# Comparação de Dados Convencionais (ex: t)
# ---------------------------------------

# Para dados convencionais, informe a variável ("t" para temperatura, "uv" para vento, etc)
exp1_conv = [
    ("data/diag_conv_01.2020010100", "data/diag_conv_03.2020010100"),
]
exp2_conv = [
    ("data/diag_conv_01.2020010100", "data/diag_conv_03.2020010100"),
]

comparator_conv = ExperimentComparator(exp1_conv, exp2_conv, var="t")
comparator_conv.compare()

plotter_conv = ComparisonPlotter(comparator_conv.comparison_df)
ax_conv = plotter_conv.plot_diff(metric="diff")
plt.title("Conventional Data Impact Comparison (Temperature)")
plt.tight_layout()
plt.show()

# -----------------------------------------
# Visualização lado a lado (Subplots, opc.)
# -----------------------------------------
# (Descomente para visualizar ambos em uma mesma figura)

# fig, axs = plt.subplots(1, 2, figsize=(16, 6))

# # Radiância
# plotter_rad.plot_diff(metric="diff", figsize=(8, 6))
# axs[0].set_title("AMSUA Impact: METOP-A vs N18")

# # Convencional
# plotter_conv.plot_diff(metric="diff", figsize=(8, 6))
# axs[1].set_title("Convencional (Temperatura)")

# plt.tight_layout()
# plt.show()

"""
Notas:
- Você pode adicionar múltiplos ciclos (vários pares de arquivos em exp1_rad, exp2_rad) para obter resultados médios.
- Para outros tipos de dados convencionais, altere o argumento var conforme necessário (ex: var="uv" para vento).
- O ComparisonPlotter aceita argumentos para customizar legendas, tamanho dos gráficos, etc.
- A estrutura é idêntica para comparar qualquer par de experimentos suportados pelo seu pacote.
"""


