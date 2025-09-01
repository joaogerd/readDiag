"""
Generate all example figures for the documentation (robust).

Run from the repository root:
    python scripts/make_figs.py

Outputs go to docs/assets/figs/.
"""
from pathlib import Path
from readDiag.reader import diagAccess
from readDiag.plotting import diagPlotter

DATA_CONV_01 = "data/diag_conv_01.2024013018"
DATA_CONV_03 = "data/diag_conv_03.2024013018"
DATA_RAD_N15_03 = "data/diag_amsua_n15_03.2024013018"

OUTDIR = Path("docs/assets/figs")
OUTDIR.mkdir(parents=True, exist_ok=True)


def save_ax(ax, name: str) -> None:
    out = OUTDIR / name
    ax.figure.savefig(out, dpi=160, bbox_inches="tight")
    print(f"[OK] saved {out}")


def quick_start() -> None:
    conv = diagAccess(DATA_CONV_01)
    p = diagPlotter(conv)
    ax = p.plot_observation_counts("t", title="Counts for T")
    save_ax(ax,"quickstart_conv_counts.png")
    
    rad = diagAccess(DATA_RAD_N15_03)
    pr = diagPlotter(rad)
    ax = pr.plot_channel_stats_rad(metric="omf", agg="mean", marker="o")
    save_ax(ax,"quickstart_rad_stats.png")


def build_conv() -> None:
    conv = diagAccess(DATA_CONV_01)
    p = diagPlotter(conv)

    ax = p.plot_variable_count(title="Total per variable", xlabel="Variable", ylabel="Count")
    save_ax(ax, "conv_variable_count.png")

    ax = p.plot_hist_conv("t", 120, col="omf", bins=60, title="Histogram O–F – T @KX120")
    save_ax(ax, "conv_hist_t_kx120.png")

    ax = p.plot_boxplot_kxs_conv("t", col="omf", color="black",
                                 title="O–F distribution across KX",
                                 xlabel="KX", ylabel="O–F")
    save_ax(ax, "conv_boxplot_t_omf_by_kx.png")

    ax = p.plot_kx_count_stacked(vars=["t", "q", "ps"], title="Stacked counts by KX and variable")
    save_ax(ax, "conv_kx_count_stacked_t_q_ps.png")


    ax = p.plot_observation_counts("uv", title="Counts for UV", rotation=45)
    save_ax(ax,"conv_counts_uv.png")
    
    ax = p.plot_kx_count(title="Total Observations by KX", rotation=45)
    save_ax(ax,"conv_counts_kx.png")
    
    ax = p.plot_variable_count(title="Total per variable", xlabel="Variable", ylabel="Count")
    save_ax(ax,"conv_counts_var.png")
    
    ax = p.plot_kx_count_stacked(vars=["t","q","ps"], title="Stacked counts by KX and variable")
    save_ax(ax,"conv_counts_stacked.png")


    # Spatial plot with fallback mask
    for mask in ( "iusev==1.0 and idqc==2.0", "iusev==1.0", None):
        try:
            ax = p.plot_spatial_conv("t", 181, param="omf", 
                                     area=[270, -60, 330, 15], cmap="RdBu_r",
                                     title="Spatial O–F (T, KX=181)")
            save_ax(ax, "conv_spatial_t_kx181.png")
            break
        except Exception as e:
            print(f"[WARN] spatial plot failed with mask={mask!r} -> {e}")

#    # Legacy-style conv
#    try:
#        ax = p.plot(varName="uv", param="omf_u",
#                    mask="(kx==220) and (iusev==1 and iqc==2.0)", s=10)
#        save_ax(ax, "conv_legacy_plot_uv_kx220.png")
#    except Exception as e:
#        print(f"[WARN] legacy conv strict mask failed -> {e}")
#        ax = p.plot(varName="uv", param="omf", mask="iusev==1", s=10)
#        save_ax(ax, "conv_legacy_plot_uv.png")


def build_rad() -> None:
    rad = diagAccess(DATA_RAD_N15_03)
    pr = diagPlotter(rad)

    ax = pr.plot_channel_stats_rad(metric="omf", agg="mean", linestyle="--", marker="o",
                                   title="Mean O–F per channel",
                                   xlabel="Channel", ylabel="mean(O–F)")
    save_ax(ax, "rad_channel_stats_omf_mean.png")

    # Try channel 7, fallback to first valid
    target_channel = 7
    try:
        ax = pr.plot_omf_distribution_rad(target_channel, corrected=True, bins=60,
                                          title=f"O–F NBC – Channel {target_channel}")
        save_ax(ax, f"rad_dist_ch{target_channel}.png")
    except Exception as e:
        print(f"[WARN] hist for channel {target_channel} failed -> {e}")
        try:
            chs = pr.diag.get_channel_list("amsua") if hasattr(pr.diag, "get_channel_list") else []
            if not chs:
                chs = list(range(1, 31))
            for ch in chs:
                try:
                    ax = pr.plot_omf_distribution_rad(ch, corrected=True, bins=60,
                                                      title=f"O–F NBC – Channel {ch}")
                    save_ax(ax, f"rad_dist_ch{ch}.png")
                    target_channel = ch
                    break
                except Exception:
                    continue
        except Exception as e2:
            print(f"[ERROR] could not determine fallback channel -> {e2}")

    # Legacy-style rad
    try:
        ax = pr.plot(varName="amsua", varType="n15", param="omf",
                     mask=f"(nchan=={target_channel}) and (iusev>=1)", s=8)
        save_ax(ax, f"rad_legacy_plot_amsua_n15_ch{target_channel}.png")
    except Exception as e:
        print(f"[WARN] legacy rad strict mask failed -> {e}")
        ax = pr.plot(varName="amsua", varType="n15", param="omf", mask="iusev>=1", s=8)
        save_ax(ax, "rad_legacy_plot_amsua_n15.png")


def main() -> None:
    quick_start()
    build_conv()
    build_rad()


if __name__ == "__main__":
    main()

