import os
import matplotlib.pyplot as plt
from readDiag import ImpactAnalyzer

# Diretório com os arquivos diag_*_01.* (OmF) e diag_*_03.* (OmA)
DATA_DIR = "data"

# Lista dos pares OmF e OmA (considera somente arquivos *_01 como base)
omf_files = sorted([f for f in os.listdir(DATA_DIR) if "_01." in f])
oma_files = [f.replace("_01.", "_03.") for f in omf_files]

# Cria uma figura com subplots automáticos
fig, axes = plt.subplots(len(omf_files), 1, figsize=(10, 4 * len(omf_files)))
if len(omf_files) == 1:
    axes = [axes]

# Loop pelos arquivos e plota o impacto
for i, (omf, oma) in enumerate(zip(omf_files, oma_files)):
    omf_path = os.path.join(DATA_DIR, omf)
    oma_path = os.path.join(DATA_DIR, oma)

    # Detecta se é conv ou rad
    is_conv = "conv" in omf
    var = "t" if is_conv else None

    try:
        impact = ImpactAnalyzer.from_pair(omf_path, oma_path, var=var)
        impact.plot_impact_bar(metric="TI", ax=axes[i],
                               title=f"Impacto {omf}", rotation=0, fontsize=10)
    except Exception as e:
        print(f"[ERRO] {omf}: {e}")

plt.tight_layout()
plt.show()

