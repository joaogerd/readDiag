"""
Canonical naming and alias resolution for readDiag.

This module defines *canonical* column names for **conventional** and
**radiance** diagnostic files and provides helpers to translate legacy field
names to the canonical schema. It also offers guardrails to gradually migrate
downstream code: optional deprecation warnings for legacy names and an opt-in
"strict mode" that rejects unknown/non-canonical columns.

The design favors:
- Minimal surface area (a couple of dicts + small helpers)
- Zero runtime dependencies
- Backward compatibility (aliases keep older scripts running)
- Easy extension (drop new aliases, or new canonical names, into the tables)

Examples
--------
Basic resolution for a single name:

>>> resolve_name("kx", domain="conv")
'obs_type_code'

Resolving a list of names (helper):

>>> resolve_names(["lat", "lon", "omf_nbc"], domain="rad")
['lat', 'lon', 'omf_nobc']

Enabling strict canonical validation:

>>> with set_canonical_policy(strict=True, deprecations=True):
...     resolve_name("kx", "conv")       # ok (warns, maps to 'obs_type_code')
...     resolve_name("unknown", "conv")  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
KeyError: "Column 'unknown'→'unknown' is not recognized canonical name."

Notes
-----
- Columns starting with ``pred`` or ``extra`` are *always* accepted even in
  strict mode, to allow user-augmented features (predictions, extra metadata).
- This module intentionally does **not** import pandas or any plotting libs.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, List, Mapping, MutableMapping, Sequence
import warnings as _w

# ---------------------------------------------------------------------------
# Config flags (module-level, user-adjustable)
# ---------------------------------------------------------------------------

#: If ``True``, reject any non-canonical names in :func:`resolve_name`
#: (except those starting with ``pred`` or ``extra``). Defaults to ``False``.
STRICT_CANON_NAMES: bool = False

#: If ``True``, emit ``DeprecationWarning`` when a legacy name is translated
#: to its canonical counterpart. Defaults to ``True``.
DEPRECATION_WARNINGS: bool = True

# ---------------------------------------------------------------------------
# Aliases (legacy → canonical)
# ---------------------------------------------------------------------------
# The mapping tables below translate legacy/old field names, as typically found
# in historical GSI diagnostic outputs or older wrappers, into the names we
# expose as the stable public schema. Keys are legacy; values are canonical.

ALIASES_CONV: Mapping[str, str] = {
    # Identification / location
    "kx": "obs_type_code",
    "ksub": "obs_subtype",
    "sid": "obs_id",
    "lat": "lat",
    "lon": "lon",
    "elev": "elev",
    "prs": "pressure",
    "hgt": "model_height",
    "time": "time_hours",

    # Quality / use
    "iqc": "qc_flag",
    "qc_setup": "qc_setup_flag",
    "iuse": "use_flag",
    "analysis_use": "analysis_use_flag",
    "rwgt": "spread",

    # Errors
    "errinv_inp": "errinv_input",
    "errinv_adj": "errinv_adjusted",
    "errinv_fin": "errinv",
    "end_err": "err_value",

    # Obs and increments
    "obs": "obs_value",
    "omf": "omf",
    "omf_wob": "omf_nobc",
    "spread": "spread",
    "factw": "spread",

    # Wind components (for vector vars exposed as u/v)
    "obs_u": "obs_value_u",
    "omf_u": "omf_u",
    "omf_wob_u": "omf_nobc_u",
    "obs_v": "obs_value_v",
    "omf_v": "omf_v",
    "omf_wob_v": "omf_nobc_v",
}

ALIASES_RAD: Mapping[str, str] = {
    # Common fields
    "lat": "lat",
    "lon": "lon",
    "elev": "elev",
    "time": "time_hours",

    # Geometry
    "iscanp": "scan_position",
    "zasat": "sat_zenith",
    "ilazi": "sat_azimuth",
    "pangs": "sol_zenith",
    "isazi": "sol_azimuth",
    "sgagl": "sun_glint_angle",

    # Surface
    "sfcst": "sfc_temp",
    "sfcstp": "sfc_temp_prev",
    "sfcws": "sfc_wind",
    "sfcwt": "sfc_water_frac",
    "sfclt": "sfc_land_frac",
    "sfcic": "sfc_ice_frac",
    "sfcsd": "sfc_snow_depth",
    "sfclc": "sfc_snow_frac",
    "sfcsmc": "sfc_soil_moist",
    "sfcltp": "sfc_soil_temp",
    "sfcvf": "sfc_veg_frac",
    "sfcsc": "sfc_class",
    "clsORclw": "clw",
    "cldpORtpwc": "tpwc",

    # Per-channel values
    "tb_obs": "obs_value",
    "omf": "omf",
    "omf_nbc": "omf_nobc",
    "oma": "oma",
    "errinv": "errinv",
    "end_err": "err_value",
    "idqc": "qc_flag",
    "emiss": "emissivity",
    "tlach": "tlap",
    "ts": "skin_temp",
    "spread": "spread",
    "ich": "channel",
    "freq": "freq",
    "pol": "pol",
    "wave": "wave",
    "varch": "varch",
    "tlap": "tlap",
}

# Canonical set for validation (includes *all* canonical values we map to)
CANON_CORE = set(ALIASES_CONV.values()) | set(ALIASES_RAD.values())

__all__ = [
    "STRICT_CANON_NAMES",
    "DEPRECATION_WARNINGS",
    "ALIASES_CONV",
    "ALIASES_RAD",
    "CANON_CORE",
    "resolve_name",
    "resolve_names",
    "is_canonical",
    "set_canonical_policy",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _maybe_warn_deprecated(old: str, new: str) -> None:
    """Emit a deprecation warning if a legacy name was translated.

    Parameters
    ----------
    old : str
        The user-provided (possibly legacy) name.
    new : str
        The resolved canonical name.
    """
    if DEPRECATION_WARNINGS and old != new:
        # stacklevel=3 points the warning at the *caller of resolve_name*,
        # which is usually the user's code (nicer UX for migration).
        _w.warn(
            f"Column name '{old}' is deprecated; use '{new}' instead.",
            DeprecationWarning,
            stacklevel=3,
        )

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_name(name: str, domain: str) -> str:
    """
    Resolve a single column name to its canonical form.

    This function accepts either a canonical name (returned unchanged) or a
    legacy alias (translated), optionally emitting a :class:`DeprecationWarning`.
    In strict mode, it raises :class:`KeyError` for names outside the canonical
    set (except those prefixed with ``pred`` or ``extra``).

    Parameters
    ----------
    name : str
        User-provided column name (canonical or legacy).
    domain : {'conv', 'rad'}
        Diagnostic domain that determines which alias table is consulted.

    Returns
    -------
    str
        The canonical column name.

    Raises
    ------
    KeyError
        If ``STRICT_CANON_NAMES`` is ``True`` and the resolved name is not
        recognized as part of :data:`CANON_CORE` and does not start with
        ``pred`` or ``extra``.
    """
    # Choose mapping based on the domain
    if domain == "conv":
        new = ALIASES_CONV.get(name, name)
    elif domain == "rad":
        new = ALIASES_RAD.get(name, name)
    else:
        # Defensive: we keep the original behavior (no domain validation) out of scope,
        # but providing this guard helps catch user mistakes early.
        raise ValueError("domain must be 'conv' or 'rad'")

    # Warn if we actually translated a legacy name
    if new != name:
        _maybe_warn_deprecated(name, new)

    # Enforce strict canonical usage if requested
    if STRICT_CANON_NAMES and new not in CANON_CORE and not new.startswith(("pred", "extra")):
        raise KeyError(f"Column '{name}'→'{new}' is not recognized canonical name.")

    return new


def resolve_names(names: Sequence[str], domain: str) -> List[str]:
    """
    Resolve multiple column names to their canonical forms.

    This is a convenience wrapper around :func:`resolve_name` that preserves
    order and multiplicity.

    Parameters
    ----------
    names : sequence of str
        Iterable of user-provided names (canonical or legacy).
    domain : {'conv', 'rad'}
        Diagnostic domain.

    Returns
    -------
    list of str
        Canonical names, in the same order as provided.

    See Also
    --------
    resolve_name : Single-name resolution.
    """
    # List comprehension keeps this fast and simple
    return [resolve_name(n, domain=domain) for n in names]


def is_canonical(name: str) -> bool:
    """
    Check whether a given name is canonical (according to :data:`CANON_CORE`).

    Parameters
    ----------
    name : str
        Name to check.

    Returns
    -------
    bool
        ``True`` if the name is in :data:`CANON_CORE`, ``False`` otherwise.

    Notes
    -----
    This function does not consider the ``pred*`` / ``extra*`` escape hatch.
    """
    return name in CANON_CORE


@contextmanager
def set_canonical_policy(*, strict: bool | None = None, deprecations: bool | None = None):
    """
    Temporarily set canonical enforcement and deprecation warning policies.

    This context manager is useful inside unit tests or short code blocks that
    require a different policy without globally changing module flags.

    Parameters
    ----------
    strict : bool, optional
        If provided, temporarily sets :data:`STRICT_CANON_NAMES`.
    deprecations : bool, optional
        If provided, temporarily sets :data:`DEPRECATION_WARNINGS`.

    Yields
    ------
    None
        Context manager with side effects on module-level flags.

    Examples
    --------
    >>> with set_canonical_policy(strict=True, deprecations=True):
    ...     resolve_name("kx", "conv")   # maps to 'obs_type_code' (warns)
    ...     # any unknown names would raise KeyError here
    """
    # Save current state
    old_strict = STRICT_CANON_NAMES
    old_depr = DEPRECATION_WARNINGS
    try:
        if strict is not None:
            globals()["STRICT_CANON_NAMES"] = strict
        if deprecations is not None:
            globals()["DEPRECATION_WARNINGS"] = deprecations
        yield
    finally:
        # Restore previous state even if an exception occurs inside the block
        globals()["STRICT_CANON_NAMES"] = old_strict
        globals()["DEPRECATION_WARNINGS"] = old_depr

