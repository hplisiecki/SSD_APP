"""Shared QSettings keys and helpers for export options."""

from __future__ import annotations

# ------------------------------------------------------------------ #
#  QSettings keys
# ------------------------------------------------------------------ #

KEY_TOP_WORDS      = "export/top_words_limit"   # int; 0 = unlimited

KEY_CLUSTER_COS_BETA  = "export/cluster_cos_beta"
KEY_CLUSTER_COHERENCE = "export/cluster_coherence"
KEY_CLUSTER_EXCERPT   = "export/cluster_excerpt"

KEY_CONT_ADJ_R2    = "export/cont_adj_r2"
KEY_CONT_F         = "export/cont_f"
KEY_CONT_BETA_NORM = "export/cont_beta_norm"
KEY_CONT_DELTA     = "export/cont_delta"
KEY_CONT_IQR       = "export/cont_iqr"
KEY_CONT_R         = "export/cont_r"

KEY_CROSS_N_COUNTS      = "export/cross_n_counts"
KEY_CROSS_P_CORR        = "export/cross_p_corr"
KEY_CROSS_COHENS_D      = "export/cross_cohens_d"
KEY_CROSS_CONTRAST_NORM = "export/cross_contrast_norm"

_DEFAULTS: dict[str, object] = {
    KEY_TOP_WORDS:           0,
    KEY_CLUSTER_COS_BETA:    True,
    KEY_CLUSTER_COHERENCE:   True,
    KEY_CLUSTER_EXCERPT:     True,
    KEY_CONT_ADJ_R2:         True,
    KEY_CONT_F:              True,
    KEY_CONT_BETA_NORM:      True,
    KEY_CONT_DELTA:          True,
    KEY_CONT_IQR:            True,
    KEY_CONT_R:              True,
    KEY_CROSS_N_COUNTS:      True,
    KEY_CROSS_P_CORR:        True,
    KEY_CROSS_COHENS_D:      True,
    KEY_CROSS_CONTRAST_NORM: True,
}


def get_export_setting(key: str):
    """Read a single export setting from QSettings, returning the typed default."""
    from PySide6.QtCore import QSettings
    s = QSettings("SSD", "SSD")
    default = _DEFAULTS.get(key)
    val = s.value(key, default)

    # QSettings may round-trip booleans as strings on some platforms
    if isinstance(default, bool):
        if isinstance(val, str):
            return val.lower() not in ("false", "0", "no")
        return bool(val)
    if isinstance(default, int):
        return int(val)
    return val
