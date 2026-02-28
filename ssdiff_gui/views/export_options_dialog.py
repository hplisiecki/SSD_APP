"""Export Options dialog — controls which columns appear in exported tables."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QCheckBox,
    QPushButton,
)
from PySide6.QtCore import QSettings, Qt

from ..utils.export_settings import (
    KEY_TOP_WORDS,
    KEY_CLUSTER_COS_BETA,
    KEY_CLUSTER_COHERENCE,
    KEY_CLUSTER_EXCERPT,
    KEY_CONT_ADJ_R2,
    KEY_CONT_F,
    KEY_CONT_BETA_NORM,
    KEY_CONT_DELTA,
    KEY_CONT_IQR,
    KEY_CONT_R,
    KEY_CROSS_N_COUNTS,
    KEY_CROSS_P_CORR,
    KEY_CROSS_COHENS_D,
    KEY_CROSS_CONTRAST_NORM,
    get_export_setting,
)


def _required_tag(text: str) -> QLabel:
    """Small read-only label styled as a 'required' badge."""
    lbl = QLabel(text)
    lbl.setObjectName("export_required_tag")
    return lbl


class ExportOptionsDialog(QDialog):
    """Dialog for configuring how exported Word tables are structured."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Options")
        self.setMinimumWidth(520)
        self._setup_ui()
        self._load_settings()

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 18, 20, 18)

        layout.addWidget(self._build_top_words_group())
        layout.addWidget(self._build_cluster_group())
        layout.addWidget(self._build_continuous_group())
        layout.addWidget(self._build_crossgroup_group())
        layout.addStretch()
        layout.addLayout(self._build_buttons())

    def _build_top_words_group(self) -> QGroupBox:
        group = QGroupBox("Top Words per Cluster")
        row = QHBoxLayout()
        row.setContentsMargins(12, 10, 12, 10)

        self._topwords_spin = QSpinBox()
        self._topwords_spin.setRange(0, 100)
        self._topwords_spin.setSpecialValueText("All")
        self._topwords_spin.setSuffix(" words")
        self._topwords_spin.setFixedWidth(110)

        row.addWidget(QLabel("Show at most"))
        row.addWidget(self._topwords_spin)
        row.addWidget(QLabel("per cluster in the exported table  (0 = show all)"))
        row.addStretch()
        group.setLayout(row)
        return group

    def _build_cluster_group(self) -> QGroupBox:
        group = QGroupBox("Cluster Table Columns")
        col = QVBoxLayout()
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(6)

        # Always-included row
        always = QHBoxLayout()
        always.addWidget(QLabel("Always included:"))
        for lbl in ("No.", "Size", "Top Words"):
            always.addWidget(_required_tag(lbl))
        always.addStretch()
        col.addLayout(always)

        # Optional row
        opt = QHBoxLayout()
        opt.addWidget(QLabel("Optional:"))
        self._cb_cos_beta  = QCheckBox("Cos \u03b2")
        self._cb_coherence = QCheckBox("Coherence")
        self._cb_excerpt   = QCheckBox("Representative Excerpt")
        for cb in (self._cb_cos_beta, self._cb_coherence, self._cb_excerpt):
            opt.addWidget(cb)
        opt.addStretch()
        col.addLayout(opt)

        group.setLayout(col)
        return group

    def _build_continuous_group(self) -> QGroupBox:
        group = QGroupBox("Continuous Analysis Columns")
        col = QVBoxLayout()
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(6)

        always = QHBoxLayout()
        always.addWidget(QLabel("Always included:"))
        for lbl in ("DV", "p"):
            always.addWidget(_required_tag(lbl))
        always.addStretch()
        col.addLayout(always)

        opt = QHBoxLayout()
        opt.addWidget(QLabel("Optional:"))
        self._cb_adj_r2    = QCheckBox("Adj R\u00b2")
        self._cb_f         = QCheckBox("F")
        self._cb_beta_norm = QCheckBox("\u03b2\u0302 norm")
        self._cb_delta     = QCheckBox("\u0394 per 0.1")
        self._cb_iqr       = QCheckBox("IQR")
        self._cb_r         = QCheckBox("r")
        for cb in (self._cb_adj_r2, self._cb_f, self._cb_beta_norm,
                   self._cb_delta, self._cb_iqr, self._cb_r):
            opt.addWidget(cb)
        opt.addStretch()
        col.addLayout(opt)

        group.setLayout(col)
        return group

    def _build_crossgroup_group(self) -> QGroupBox:
        group = QGroupBox("Crossgroup Analysis Columns")
        col = QVBoxLayout()
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(6)

        always = QHBoxLayout()
        always.addWidget(QLabel("Always included:"))
        for lbl in ("Group A", "Group B", "Cos Distance", "p"):
            always.addWidget(_required_tag(lbl))
        always.addStretch()
        col.addLayout(always)

        opt = QHBoxLayout()
        opt.addWidget(QLabel("Optional:"))
        self._cb_n_counts      = QCheckBox("n\u2090 / n\u1d47")
        self._cb_p_corr        = QCheckBox("p (corr)")
        self._cb_cohens_d      = QCheckBox("Cohen\u2019s d")
        self._cb_contrast_norm = QCheckBox("\u2016Contrast\u2016")
        for cb in (self._cb_n_counts, self._cb_p_corr,
                   self._cb_cohens_d, self._cb_contrast_norm):
            opt.addWidget(cb)
        opt.addStretch()
        col.addLayout(opt)

        group.setLayout(col)
        return group

    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        row.addWidget(apply_btn)

        return row

    # ------------------------------------------------------------------ #
    #  Persistence
    # ------------------------------------------------------------------ #

    def _load_settings(self):
        self._topwords_spin.setValue(get_export_setting(KEY_TOP_WORDS))
        self._cb_cos_beta.setChecked(get_export_setting(KEY_CLUSTER_COS_BETA))
        self._cb_coherence.setChecked(get_export_setting(KEY_CLUSTER_COHERENCE))
        self._cb_excerpt.setChecked(get_export_setting(KEY_CLUSTER_EXCERPT))
        self._cb_adj_r2.setChecked(get_export_setting(KEY_CONT_ADJ_R2))
        self._cb_f.setChecked(get_export_setting(KEY_CONT_F))
        self._cb_beta_norm.setChecked(get_export_setting(KEY_CONT_BETA_NORM))
        self._cb_delta.setChecked(get_export_setting(KEY_CONT_DELTA))
        self._cb_iqr.setChecked(get_export_setting(KEY_CONT_IQR))
        self._cb_r.setChecked(get_export_setting(KEY_CONT_R))
        self._cb_n_counts.setChecked(get_export_setting(KEY_CROSS_N_COUNTS))
        self._cb_p_corr.setChecked(get_export_setting(KEY_CROSS_P_CORR))
        self._cb_cohens_d.setChecked(get_export_setting(KEY_CROSS_COHENS_D))
        self._cb_contrast_norm.setChecked(get_export_setting(KEY_CROSS_CONTRAST_NORM))

    def _apply(self):
        s = QSettings("SSD", "SSD")
        s.setValue(KEY_TOP_WORDS,           self._topwords_spin.value())
        s.setValue(KEY_CLUSTER_COS_BETA,    self._cb_cos_beta.isChecked())
        s.setValue(KEY_CLUSTER_COHERENCE,   self._cb_coherence.isChecked())
        s.setValue(KEY_CLUSTER_EXCERPT,     self._cb_excerpt.isChecked())
        s.setValue(KEY_CONT_ADJ_R2,         self._cb_adj_r2.isChecked())
        s.setValue(KEY_CONT_F,              self._cb_f.isChecked())
        s.setValue(KEY_CONT_BETA_NORM,      self._cb_beta_norm.isChecked())
        s.setValue(KEY_CONT_DELTA,          self._cb_delta.isChecked())
        s.setValue(KEY_CONT_IQR,            self._cb_iqr.isChecked())
        s.setValue(KEY_CONT_R,              self._cb_r.isChecked())
        s.setValue(KEY_CROSS_N_COUNTS,      self._cb_n_counts.isChecked())
        s.setValue(KEY_CROSS_P_CORR,        self._cb_p_corr.isChecked())
        s.setValue(KEY_CROSS_COHENS_D,      self._cb_cohens_d.isChecked())
        s.setValue(KEY_CROSS_CONTRAST_NORM, self._cb_contrast_norm.isChecked())
        self.accept()
