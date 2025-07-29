# example_plotting.py
import os

import matplotlib.pyplot as plt
from readDiag import diagAccess, diagPlotter

ROOT = os.path.dirname(os.path.dirname(__file__))

CONV_FILE = os.path.join(ROOT, "data", "diag_conv_01.2020010100")
RAD_FILE = os.path.join(ROOT, "data", "diag_amsua_n15_01.2020010100")

# ——————————————
# Funções de demonstração
# ——————————————
def demo_conv_plots():
    diag = diagAccess(CONV_FILE)
    plotter = diagPlotter(diag)

    ax1 = plotter.plot_hist_conv(
        var="t", kx=181, bins=5,
        color="red", alpha=0.6,
        title="Custom Temp Histogram",
        xlabel="Temperature [K]",
        ylabel="Frequency"
    ); ax1.grid(True)
    
    ax2 = plotter.plot_boxplot_kxs_conv(
        var="t", col="omf",
        notch=True,
        title="O-F Boxplot per KX",
        ylabel="O-F Error"
    ); ax2.grid(axis="y")

    ax3 = plotter.plot_kx_count(
        color="blue", linestyle="--",
        alpha=0.45,
        title="Total Obs by KX",
        xlabel="Sensor",
        ylabel="Total Obs"
    )

    ax4 = plotter.plot_kx_count_stacked(
        title="Total Obs by KX",
        xlabel="Sensor",
        ylabel="Total Obs"
    )
   
    ax5 = plotter.plot_observation_counts(
        varName="t",
        color="green",
        alpha=0.75,
        title="Observations per Sensor",
        xlabel="Sensor Index",
        ylabel="Count"
    )

    
    plt.tight_layout()
    plt.show()

def demo_rad_plots():
    diag = diagAccess(RAD_FILE)
    plotter = diagPlotter(diag)

    ax6 = plotter.plot_channel_stats_rad(
        metric="omf", agg="mean",
        marker="x", color="orange",
        title="Mean OMF per Channel",
        xlabel="Channel #",
        ylabel="Mean OMF"
    ); ax6.grid(True)

    ax7 = plotter.plot_omf_distribution_rad(
        channel_index=1, corrected=True, bins=4,
        color="magenta", alpha=0.7,
        title="Corrected O-F Dist (Channel 1)",
        xlabel="O-F Value",
        ylabel="Frequency"
    ); ax7.grid(axis="y")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    demo_conv_plots()
    demo_rad_plots()

