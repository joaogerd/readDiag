# readDiag Examples

This folder contains runnable examples grouped by topic plus a full **kitchen sink** demo.

## Quick start

```bash
# Conventional
python examples/01_quickstart_conv.py --file data/diag_conv_01.2020010100 --save

# Radiance
python examples/02_quickstart_rad.py  --file data/diag_amsua_n15_01.2020010100 --save
```

## Plot galleries

```bash
python examples/03_plots_conv.py --file data/diag_conv_01.2020010100 --save
python examples/04_plots_rad.py  --file data/diag_amsua_n15_01.2020010100 --save
```

## Impact

```bash
# Single pair (conv var example)
python examples/05_impact_basic.py  --omf data/diag_conv_01.2020010100 --oma data/diag_conv_03.2020010100 --var t --save

# Series & experiment comparison
python examples/06_impact_series.py --pairs \
  data/diag_conv_01.2020010100 data/diag_conv_03.2020010100 \
  data/diag_conv_01.2020010100 data/diag_conv_03.2020010100 \
  --var t --save
```

## Legacy compatibility

```bash
python examples/07_legacy_compat.py --file data/diag_conv_01.2020010100 --save
```

## Kitchen sink

```bash
python examples/kitchen_sink.py \
  --conv data/diag_conv_01.2020010100 \
  --rad  data/diag_amsua_n15_01.2020010100 \
  --impact-omf data/diag_conv_01.2020010100 \
  --impact-oma data/diag_conv_03.2020010100 \
  --outdir outputs/examples --save
```

> The spatial map requires `cartopy`. If not installed, the examples will skip that step gracefully.
