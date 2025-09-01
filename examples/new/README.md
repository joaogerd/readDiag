# readDiag Examples (fixed test set)

Defaults point to:
- data/diag_amsua_n19_01.2024013018, data/diag_amsua_n19_03.2024013018
- data/diag_conv_01.2024013018, data/diag_conv_03.2024013018

Run all saved PNGs:
```bash
python examples/kitchen_sink.py --save
python examples/01_quickstart_conv.py --save
python examples/02_quickstart_rad.py --save
python examples/03_plots_conv.py --save
python examples/04_plots_rad.py --save
python examples/05_impact_basic.py --save
python examples/06_impact_series.py --save
python examples/07_legacy_compat.py --save
python examples/08_plot_amsua_swath.py --channel 14 --value tb_obs --basemap --save
```
