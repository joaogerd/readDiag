# How **readDiag** Understands GSI Diagnostic Files

This page explains how **readDiag** interprets the internal structure of GSI diagnostic files for **conventional (conv)** and **radiance (rad)** data, and what that means in practice when plotting.

---

# **CONV Structure** (`diag_conv_*.YYYYMMDDHH`)

## 1) How GSI writes it

* Format: **unformatted sequential Fortran records**.
* Each observation is stored as **integer** and **real** vectors of size `nreal` (may vary by type).
* The **first \~20 reals** are the so-called “**BASE20**” (common fields); when `nreal > 20`, extra reals follow, specific to the obs type/variable.
* The file mixes **multiple variables** (e.g., `t`, `q`, `u/v`, `ps`, etc.) and **multiple KX** values (observation type codes from WMO/BUFR).

## 2) How **readDiag** reads and models it

* Reading is implemented in `conv_reader.py` (Fortran records), orchestrated by `conv.py`.
* **Sentinels**: any “garbage”/sentinel values (magnitude ≥ `1e10`, typical of GSI) are immediately converted into **NaN**.
* Standard output of the reader is normalized as:

```python
 dict[var][kx] -> pandas.DataFrame
```

* The modern facade exposed by the *Surface API* (via `open_diagnostic()` / Adapter) provides:

  * `variables()` → list of variables available (e.g., `["t", "q", "u", "v", "ps"]`)
  * `kx_list()` → ordered list of KX present (e.g., `[187, 120, ...]`)
  * `frame_conv(var, kx)` → **DataFrame** for that variable/KX combination.

### 2.1 Canonical columns (BASE20 + normalization)

Column names may vary depending on source/version of GSI, but `readDiag` attempts to **standardize** them when possible:

| Column            | Meaning (conv)                                               |
| ----------------- | ------------------------------------------------------------ |
| `lat`, `lon`      | latitude/longitude (degrees)                                 |
| `prs` / `lev`     | pressure (hPa) **or** level (depends on type)                |
| `time`            | time relative to the cycle (minutes)                         |
| `obs`             | observed value                                               |
| `omf`             | O−B (Obs − Background); typical of “01” diag files           |
| `oma`             | O−A (Obs − Analysis); typical of “03” diag files             |
| `errinv`          | **1/σ** (inverse of the error; σ = error standard deviation) |
| `error` / `sigma` | σ (derived from `1/errinv` when feasible)                    |
| `qcmark`          | GSI QC mark (0 = good; >0 depending on scheme)               |
| `iuse`            | usage flag (1 = used; 0 = monitor; −1 = rejected, etc.)      |
| `jiter` / `iter`  | minimizer iteration (when present)                           |
| `stnid` / `id`    | station/report identifier (if available)                     |

!!! tipo "Note"
      **BASE20** is implemented in `conv.py`; when **`nreal > 20`**, additional columns are appended (obs-type dependent).

### 2.2 Plotting implications (conv)

* **Double key**: you always select **`var` + `kx`** to get a flat, plot-ready DataFrame (`frame_conv(var, kx)`).
* **NaNs**: since sentinels become `NaN`, histograms/counts must use `dropna()` (the plotter handles this in most cases).
* **Axes/units**: `time` is in **minutes relative to the cycle**; `prs/lev` may be in hPa or level — check before plotting profiles.
* **O−B vs O−A**: usually **01 → `omf`** and **03 → `oma`**; for impact (TI/FI/FBI), the `ImpactAnalyzer` pairs 01/03 files.

---

# **RAD Structure** (`diag_amsu*`, `diag_iasi*`, etc.)

## 1) How GSI writes it

* Multi-block structure, typically called:

  * **Header/DB**: metadata per “sample” (geometry, time, etc.).
  * **DBC (diagbufchan)**: **per-channel** block (observed TB, simulated TB, O−B/O−A, QC, error…).
  * **DBE (extras)**: **bias predictors** and auxiliary terms (size depends on `npred`).

* Dimensions: `n_obs × n_channels` (not necessarily dense; QC/IUSE determine actual usage).

## 2) How **readDiag** reads and models it

* Implemented in `rad.py` with optional **`numpy.memmap`** to reduce RAM usage.

* Produces three logical layers:

  1. **Global header** (DataFrame, one row per “sample”/FOV/scan):
     geolocation, timestamps, angles, base flags.
  2. **List of DataFrames per channel** (one DF **per channel**):
     observed/simulated BTs, O−B/O−A, QC, error, scanline/FOV indices, etc.
  3. **Extras/DBE** (optional): bias predictors per channel (e.g., secant of angle, surface temperature, etc.).

* In the *Surface API*/Adapter you have:

  * `channels()` → list of available channels (e.g., `[1, 2, 3, ..., 15]`).
  * `frame_channel(ch)` → **DataFrame** containing only that channel (merge of essential header+dbc+dbe fields).
  * `table(name)` → raw access to internal “tables” (`"header"`, `"chan_info"`, `"extras"`, …).

### 2.1 Canonical columns (per channel)

Again, these may vary by sensor/GSI version, but `readDiag` strives for consistent exposure:

| Column                | Meaning (rad)                                                           |
| --------------------- | ----------------------------------------------------------------------- |
| `scanline`, `fov`     | scanline / field of view indices                                        |
| `lat`, `lon`          | observation position                                                    |
| `sat_zen`, `sun_zen`  | satellite/solar zenith angles (when present)                            |
| `tb_obs`              | **Observed brightness temperature (K)**                                 |
| `tb_bkg` / `hxb`      | Background-simulated BT (if available)                                  |
| `tb_ana` / `hxa`      | Analysis-simulated BT (if available)                                    |
| `omf`                 | O−B in BT units                                                         |
| `oma`                 | O−A in BT units                                                         |
| `errinv`              | 1/σ (inverse of the channel error)                                      |
| `error` / `sigma`     | σ derived from `errinv`                                                 |
| `qcmark` / `qc`       | GSI QC mark for that channel/sample                                     |
| `iuse`                | usage flag (`1` used; `-1` rejected; `0` monitor, etc.)                 |
| `landfrac` / `lsmask` | land fraction or land/sea mask (if provided)                            |
| `cloud`               | cloud flag/indicator (if provided)                                      |
| `channel`             | channel number (fixed in that DF)                                       |
| `datetime` / `time`   | observation time (some files store relative minutes, others epoch-like) |

!!! tip "Important Reminder"
      `readDiag` computes **`error = 1 / errinv`** when stable, but preserves **both fields** to avoid information loss.

### 2.2 Plotting implications (rad)

* The **basic unit for plotting is channel**: use `frame_channel(ch)` to obtain a **clean, consistent DF**.
* **Header vs per-channel**: don’t mix columns only in the *header* with a **channel DF** (or vice versa). The Adapter resolves essential joins, but raw calls like `table("header")` return different granularity (1 row per obs vs 1 row per obs-channel).
* **Memory/I/O**: with `use_memmap=True`, RAM usage drops, but plotting with heavy per-channel filters can cause lots of I/O. Prefer selecting a subset before plotting.

---

# Practical Debugging Tips for Plotting

Always **inspect before plotting** using the Surface API:

```python
from readDiag.open import open_diagnostic

h = open_diagnostic("/path/to/diag_*")

print("KIND:", h.kind())

if h.kind() == "conv":
    print("vars:", h.variables())    # e.g. ['t', 'q', 'u', 'v', 'ps']
    print("kxs :", h.kx_list())      # e.g. [187, 120, ...]
    df = h.frame_conv("t", 187)
    print(df.columns.tolist(), df.shape)

if h.kind() == "rad":
    print("channels:", h.channels())  # e.g. [1,2,3,15,...]
    df = h.frame_channel(1)
    print(df.columns.tolist(), df.shape)
    # raw tables if needed:
    # hdr = h.table("header"); print(hdr.columns)
```

**Typical plotting errors and how to avoid them:**

1. **Conv:** calling plot without selecting **`var` and `kx`** → always pick `frame_conv(var, kx)`.
2. **Rad:** mixing *header* columns with per-channel DF → stick to `frame_channel(ch)`.
3. **Sentinels:** values ≥ `1e10` are already `NaN`, but if you manually merged tables, check with `dropna()`.
4. **Time/unit:** `time` (minutes) vs `datetime`; `prs` (hPa) vs `lev` — verify before setting scales/logs.

---

# Quick Reference (cheat-sheet)

* **CONV** = **dict\[var]\[kx] → DataFrame**
  Canonical fields: `lat, lon, prs/lev, time, obs, omf, oma, errinv, error, qcmark, iuse, jiter, stnid/id`.
  Access: `variables()`, `kx_list()`, `frame_conv(var, kx)`.

* **RAD** = **list of per-channel DataFrames** (+ auxiliary tables)
  Canonical fields per channel: `scanline, fov, lat, lon, sat_zen, tb_obs, tb_bkg, tb_ana, omf, oma, errinv, error, qcmark, iuse, channel, time/datetime`.
  Access: `channels()`, `frame_channel(ch)`, `table("header"|"extras"|...)`.

---

👉 If you run into a **plotting issue** (and can provide the exact file and plot), we can deliver a ready-to-use fix in `plotting.py` or in the Adapter. In most cases, it’s just about ensuring the right **granularity** (conv var/kx vs rad channel) and consistent column names.

