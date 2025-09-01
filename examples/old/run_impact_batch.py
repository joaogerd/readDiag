import os
from readDiag.impact import plot_all_impact_subplots

DATA_DIR = "data"

file_roots = [
    "diag_amsua_metop-a",
    "diag_amsua_n15",
    "diag_amsua_n18",
    "diag_amsua_n19",
    "diag_conv"
]

pairs = []
for root in file_roots:
    omf_file = os.path.join(DATA_DIR, f"{root}_01.2020010100")
    oma_file = os.path.join(DATA_DIR, f"{root}_03.2020010100")
    label = root

    # Detecta tipo conv e insere var='t'
    if 'conv' in root:
        pairs.append((omf_file, oma_file, label, 't'))
    else:
        pairs.append((omf_file, oma_file, label, None))

# Adapte a chamada da função plot_all_impact_subplots
from readDiag.impact import ImpactAnalyzer

analyzers = [ImpactAnalyzer.from_pair(omf, oma, var=var) for omf, oma, _, var in pairs]
from readDiag.impact import plot_all_impact_subplots
plot_all_impact_subplots(analyzers, labels=[label for _, _, label, _ in pairs], metric="TI", suptitle="Total Impact (TI) - 2020010100")

