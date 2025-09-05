# Migration Guide: Legacy (`gsidiag`) → Modern (`readDiag`)

This guide shows how to move from legacy imports/usage to the modern `readDiag` API.

## Quick map

| Legacy (old)                       | Modern (new)                                     |
|-----------------------------------|---------------------------------------------------|
| `import gsidiag as gd`            | `from readDiag import read_diag`                  |
| `gd.read_diag(file)`              | `read_diag(file)` → returns `DiagnosticAPI`       |
| `frame(var,kx)` ambiguous         | `d.frame_conv(var, kx)`                           |
| `channels()` loose                | `d.channels()`                                    |
| `plot_kx_count(d)` (old module)   | `diagPlotter(d).plot_kx_count()` or wrapper       |
| `plot_omf_map(...)`               | `diagPlotter(d).plot_spatial_conv(...,"omf")`     |
| `plot_oma_map(...)`               | `diagPlotter(d).plot_spatial_conv(...,"oma")`     |

## Policy

- Legacy lives in `src/gsidiag`. It re-exports a minimal set to help old scripts.
- The modern `readDiag` is free of legacy branches/imports.
- New docs/examples use the modern API only.

## Minimal modern usage

```python
from readDiag import read_diag, diagPlotter

d = read_diag("path/to/diag_conv_01.2024013018")
print(d.kind(), d.variables())
kx_list = d.kx_list("t")
df = d.frame_conv("t", kx_list[0])

plotter = diagPlotter(d)
ax = plotter.plot_kx_count()
```

## Plot wrappers (for convenience)

```python
from readDiag.plotting.wrappers import plot_kx_count, plot_omf_map
plot_kx_count(d)
plot_omf_map(d, "t", 120)
```
