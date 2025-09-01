"""
compare_sensor_impact_multi_cycle.py

Statistical analysis and visualization script for observation impact of
multiple AMSUA sensors (e.g., N18 and N19) over several data assimilation cycles.

This example:
    - Reads OMF/OMA diagnostics for two sensors over a set of cycles.
    - Aligns data, computes robust statistics per channel (kx).
    - Generates multiple plots for scientific interpretation.
    - Highlights statistically significant differences.
    - Outputs a comprehensive CSV file for further analysis.

Required structure:
    - LOCAL_BASE/cycle/diag_amsua_SENSOR_01.cycle
    - LOCAL_BASE/cycle/diag_amsua_SENSOR_03.cycle

Authors:
    João Gerd Zell de Mattos, 2024
"""

import os
import matplotlib.pyplot as plt
from readDiag import ImpactAnalyzer, ExperimentComparator, ComparisonPlotter
import numpy as np
from datetime import datetime, timedelta

def generate_cycles(start_str, num_days, step_hours):
    """
    Generate a list of cycle strings (YYYYMMDDHH) given a start datetime,
    number of days, and time step in hours.

    Args:
        start_str (str): Initial cycle in 'YYYYMMDDHH' format (e.g. '2023041600')
        num_days (int): Number of days to include
        step_hours (int): Time step in hours (e.g. 6 for 00,06,12,18)

    Returns:
        List[str]: List of cycle strings
    """
    cycles = []
    start_dt = datetime.strptime(start_str, "%Y%m%d%H")
    total_steps = int((24 * num_days) / step_hours)
    for i in range(total_steps):
        cycle_dt = start_dt + timedelta(hours=i*step_hours)
        cycles.append(cycle_dt.strftime("%Y%m%d%H"))
    return cycles

# ---- User Configuration ----
LOCAL_BASE = "./dataout"  # Directory containing cycle subfolders with diag files
CYCLES = generate_cycles("2023041600", num_days=4, step_hours=6)
print(CYCLES)

SENSORS = ["n18", "n19"]   # List of sensors for analysis
SENSOR_A = SENSORS[0]      # Reference/Experiment 1
SENSOR_B = SENSORS[1]      # Comparison/Experiment 2

def montar_pares(sensor, cycles, local_base):
    """
    Build list of (omf, oma) file pairs for a given sensor.

    Args:
        sensor (str): Sensor ID (e.g. 'n18')
        cycles (list of str): List of cycle names (YYYYMMDDHH)
        local_base (str): Base directory with cycle folders

    Returns:
        list of tuple: List of (omf, oma) file paths for all available cycles.
    """
    pares = []
    for cyc in cycles:
        pasta = os.path.join(local_base, cyc)
        omf = os.path.join(pasta, f"diag_amsua_{sensor}_01.{cyc}")
        oma = os.path.join(pasta, f"diag_amsua_{sensor}_03.{cyc}")
        if os.path.exists(omf) and os.path.exists(oma):
            pares.append((omf, oma))
    return pares

# --- Data loading and pair construction ---
exp1 = montar_pares(SENSOR_A, CYCLES, LOCAL_BASE)
exp2 = montar_pares(SENSOR_B, CYCLES, LOCAL_BASE)

print(f"Sensor {SENSOR_A}: {len(exp1)} cycles found.")
print(f"Sensor {SENSOR_B}: {len(exp2)} cycles found.")

if not exp1 or not exp2:
    raise RuntimeError("Insufficient files found for one or both sensors.")

# --- Statistical comparison ---
comparator = ExperimentComparator(exp1, exp2)
comparator.compare()
df = comparator.comparison_df

# 1. Mean difference plot per channel
# Shows the average difference in total impact (TI) between sensors, with 95% confidence intervals.
# Red triangles mark channels with statistically significant differences (t-test or Wilcoxon).
plt.figure(figsize=(12,5))
plt.bar(df['kx'], df['mean_diff'], color='steelblue', label='Mean difference')
plt.errorbar(df['kx'], df['mean_diff'],
             yerr=[df['mean_diff'] - df['CI_low'], df['CI_high'] - df['mean_diff']],
             fmt='none', ecolor='black', capsize=4, label='95% CI')
for i, signif in enumerate(df['signif_t'] | df['signif_w']):
    if signif:
        plt.scatter(df['kx'].iloc[i], df['mean_diff'].iloc[i], color='red', marker='^', s=80, label='Significant' if i == 0 else "")
plt.axhline(0, color='k', linestyle='--')
plt.xlabel("KX / Channel")
plt.ylabel("Mean difference N19-N18")
plt.title("Mean impact difference by channel (95% CI, significance)")
plt.legend()
plt.tight_layout()
plt.show()

# 2. Effect size plot (Cohen's d)
# Cohen's d quantifies the magnitude of difference between sensors in units of pooled std deviation.
# Interpretation: |d|<0.2 negligible; 0.2–0.5 small; 0.5–0.8 medium; >0.8 large effect.
plt.figure(figsize=(10,5))
plt.bar(df['kx'], df['cohens_d'], color='C0')
plt.axhline(0, color='k', linestyle='--')
plt.xlabel("KX / Channel")
plt.ylabel("Cohen's d")
plt.title("Effect size (Cohen's d) by channel")
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()

# 3. Temporal trend plot (slope)
# Shows the linear trend (slope) of the impact difference over cycles.
# Positive slope: difference increasing over time; negative: decreasing.
plt.figure(figsize=(10,5))
plt.bar(df['kx'], df['slope'], color='C1')
plt.axhline(0, color='k', linestyle='--')
plt.xlabel("KX / Channel")
plt.ylabel("Slope (ΔTI/cycle)")
plt.title("Temporal trend of impact difference by channel")
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()

# 4. Superiority frequency plot
# Shows, for each channel, the percentage of cycles where sensor B (N19) outperformed sensor A (N18).
# 50% means no preference; above 50% indicates systematic advantage for N19.
plt.figure(figsize=(10,5))
plt.bar(df['kx'], df['perc_exp2_maior'], color='C2')
plt.axhline(50, color='k', linestyle='--', label='50%')
plt.xlabel("KX / Channel")
plt.ylabel("% cycles where N19 > N18")
plt.title("Relative frequency of N19 superiority by channel")
plt.legend()
plt.tight_layout()
plt.show()

# 5. Median difference plot (robustness to outliers)
# Plots the channel-wise median of the difference (N19-N18), a robust estimator less sensitive to outliers.
plt.figure(figsize=(10,5))
plt.bar(df['kx'], df['median_diff'], color='C3')
plt.axhline(0, color='k', linestyle='--')
plt.xlabel("KX / Channel")
plt.ylabel("Median difference")
plt.title("Median of impact difference N19 vs N18 by channel")
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()

# 6. Boxplot of cycle-by-cycle differences per channel
# Shows the distribution, central tendency, and spread of differences across cycles for each channel.
df_cycles = comparator.per_cycle_df
diffs_por_canal = []
canal_labels = []
for kx in df['kx']:
    d1 = df_cycles[(df_cycles['experiment']==1) & (df_cycles['kx']==kx)].sort_values("cycle")['TI'].values
    d2 = df_cycles[(df_cycles['experiment']==2) & (df_cycles['kx']==kx)].sort_values("cycle")['TI'].values
    n = min(len(d1), len(d2))
    if n >= 2:
        diffs = d2[:n] - d1[:n]
        diffs_por_canal.append(diffs)
        canal_labels.append(str(kx))
plt.figure(figsize=(13,5))
plt.boxplot(diffs_por_canal, labels=canal_labels, showmeans=True)
plt.axhline(0, color='k', linestyle='--')
plt.xlabel("KX / Channel")
plt.ylabel("Difference (N19-N18)")
plt.title("Cycle-by-cycle distribution of impact differences by channel")
plt.tight_layout()
plt.show()

# 7. Significant channels printout
# Prints a summary of all channels with statistically significant difference according to t-test or Wilcoxon.
sig = df[(df['signif_t']) | (df['signif_w'])]
print("\nCHANNELS WITH SIGNIFICANT DIFFERENCE (t or Wilcoxon):")
if not sig.empty:
    print(sig[['kx','mean_diff','std_diff','cohens_d','slope','t_p','w_p','sign_p','perc_exp2_maior']])
else:
    print("No significant channels found.")

# 8. Export all statistics to CSV for reporting, supplementary tables, or further analysis.
df.to_csv(f"full_statistics_{SENSOR_A}_{SENSOR_B}.csv", index=False)
print(f"\nCSV file saved: full_statistics_{SENSOR_A}_{SENSOR_B}.csv")

