"""Stage 2: Run tab view for SSD.

Contains a pre-flight review panel and (for lexicon mode) a lexicon builder.
Analysis type, mode, and column selection are configured in the Setup tab.
"""

from typing import Optional, Set
import numpy as np
import pandas as pd

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QMessageBox,
    QInputDialog,
    QSplitter,
    QHeaderView,
    QFrame,
)
from PySide6.QtCore import Qt, Signal, QSettings, QEvent, QTimer

from ..models.project import Project, ConceptConfig
from .widgets.info_button import InfoButton


class Stage2Widget(QWidget):
    """Stage 2: Run - Pre-flight review + lexicon builder."""

    run_requested = Signal(object)  # ConceptConfig

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.lexicon: Set[str] = set()
        self._settings = QSettings("SSD", "SSD")

        self._overlay_info_buttons: list = []
        self._setup_ui()

    # -- overlay info glyphs on QGroupBoxes ----------------------------

    def _add_overlay_info(self, widget, tooltip_html: str):
        """Pin an InfoButton to the top-right corner of *widget*."""
        btn = InfoButton(tooltip_html, parent=widget)
        widget.installEventFilter(self)
        self._overlay_info_buttons.append((widget, btn))
        QTimer.singleShot(0, lambda w=widget, b=btn: self._reposition_info(w, b))

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.LayoutRequest):
            for widget, btn in self._overlay_info_buttons:
                if obj is widget:
                    self._reposition_info(widget, btn)
                    break
        return super().eventFilter(obj, event)

    @staticmethod
    def _reposition_info(widget, btn):
        x = widget.width() - btn.width() - 4
        btn.move(x, 18)
        btn.raise_()

    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 16)
        main_layout.setSpacing(12)

        # Header
        title = QLabel("Run Analysis")
        title.setObjectName("label_title")
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Review your configuration and build a lexicon (if applicable), then run."
        )
        subtitle.setObjectName("label_muted")
        main_layout.addWidget(subtitle)

        # Main splitter: review panel (left) | lexicon builder (right)
        self.main_splitter = QSplitter(Qt.Horizontal)

        # --- Left: Pre-flight review panel ---
        review_group = QGroupBox("Details")
        review_group_layout = QVBoxLayout()

        self.review_panel = QTextEdit()
        self.review_panel.setReadOnly(True)
        self.review_panel.setObjectName("preflight_review")
        review_group_layout.addWidget(self.review_panel)

        review_group.setLayout(review_group_layout)
        self._review_group = review_group
        self._add_overlay_info(review_group,
            "<b>Run Details</b><br><br>"
            "A read-only summary of all your project settings: dataset, "
            "preprocessing stats, embedding coverage, analysis type/mode, "
            "and hyperparameters.<br><br>"
            "Review this before running to make sure everything looks correct.",
        )
        self.main_splitter.addWidget(review_group)

        # --- Right: Lexicon builder panel ---
        self.lexicon_panel = QWidget()
        self._create_lexicon_panel()
        self.main_splitter.addWidget(self.lexicon_panel)

        self.main_splitter.setSizes([400, 600])
        main_layout.addWidget(self.main_splitter, stretch=1)

        # Bottom: Run section
        self._create_run_section(main_layout)

        # Restore splitter state
        self._restore_splitter_states()

    def _create_lexicon_panel(self):
        """Create the lexicon builder panel (right side)."""
        layout = QVBoxLayout(self.lexicon_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._add_overlay_info(self.lexicon_panel,
            "<b>Lexicon Builder</b><br><br>"
            "Build the word list that defines your concept.<br>"
            "<b>Add Tokens</b> — type or paste seed words.<br>"
            "<b>Current Lexicon</b> — your selected words; remove any "
            "that don't fit.<br>"
            "<b>Coverage</b> — see how many corpus sentences contain "
            "at least one lexicon word.<br>"
            "<b>Suggestions</b> — nearest-neighbour words from the "
            "embedding space to help you expand the lexicon.",
        )

        self.lexicon_splitter = QSplitter(Qt.Horizontal)

        # Left: Token input and lexicon list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        input_group = QGroupBox("Add Tokens")
        input_layout = QVBoxLayout()

        token_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter a keyword...")
        self.token_input.returnPressed.connect(self._add_token)
        token_row.addWidget(self.token_input, stretch=1)

        add_btn = QPushButton("Add")
        add_btn.setMinimumWidth(60)
        add_btn.clicked.connect(self._add_token)
        token_row.addWidget(add_btn)

        input_layout.addLayout(token_row)

        paste_btn = QPushButton("Paste Token List...")
        paste_btn.clicked.connect(self._paste_tokens)
        input_layout.addWidget(paste_btn)

        input_group.setLayout(input_layout)
        left_layout.addWidget(input_group)

        list_group = QGroupBox("Current Lexicon")
        list_layout = QVBoxLayout()

        self.lexicon_list = QListWidget()
        self.lexicon_list.setSelectionMode(QListWidget.ExtendedSelection)
        list_layout.addWidget(self.lexicon_list)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected_tokens)
        list_layout.addWidget(remove_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("btn_secondary")
        clear_btn.clicked.connect(self._clear_lexicon)
        list_layout.addWidget(clear_btn)

        self.lexicon_count_label = QLabel("0 tokens")
        self.lexicon_count_label.setObjectName("label_muted")
        list_layout.addWidget(self.lexicon_count_label)

        list_group.setLayout(list_layout)
        left_layout.addWidget(list_group, stretch=1)

        self.lexicon_splitter.addWidget(left_panel)

        # Right: Coverage and suggestions (vertical splitter)
        self.coverage_splitter = QSplitter(Qt.Vertical)

        coverage_group = QGroupBox("Lexicon Coverage")
        coverage_layout = QVBoxLayout()

        self.coverage_stats = QLabel("Add tokens to see coverage statistics")
        self.coverage_stats.setWordWrap(True)
        coverage_layout.addWidget(self.coverage_stats)

        self.coverage_warnings = QLabel("")
        self.coverage_warnings.setWordWrap(True)
        coverage_layout.addWidget(self.coverage_warnings)

        self.coverage_table = QTableWidget()
        self.coverage_table.setColumnCount(6)
        self.coverage_table.setHorizontalHeaderLabels([
            "Word", "Docs", "Cov%", "Q1%", "Q4%", "Corr",
        ])
        self.coverage_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        for col in range(1, 6):
            self.coverage_table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeToContents
            )
        self.coverage_table.setAlternatingRowColors(True)
        self.coverage_table.setEditTriggers(QTableWidget.NoEditTriggers)
        coverage_layout.addWidget(self.coverage_table)

        coverage_group.setLayout(coverage_layout)
        self.coverage_splitter.addWidget(coverage_group)

        suggestions_group = QGroupBox("Lexicon Suggestions")
        suggestions_layout = QVBoxLayout()

        suggestions_desc = QLabel(
            "Double-click a row to add it to your lexicon."
        )
        suggestions_desc.setObjectName("label_muted")
        suggestions_layout.addWidget(suggestions_desc)

        self.suggestions_table = QTableWidget()
        self.suggestions_table.setColumnCount(5)
        self.suggestions_table.setHorizontalHeaderLabels([
            "Token", "Docs", "Cov%", "Corr", "Rank",
        ])
        self.suggestions_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        for col in range(1, 5):
            self.suggestions_table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeToContents
            )
        self.suggestions_table.setAlternatingRowColors(True)
        self.suggestions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.suggestions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.suggestions_table.cellDoubleClicked.connect(self._add_suggestion)
        suggestions_layout.addWidget(self.suggestions_table)

        refresh_suggestions_btn = QPushButton("Get Suggestions")
        refresh_suggestions_btn.clicked.connect(self._update_suggestions)
        suggestions_layout.addWidget(refresh_suggestions_btn)

        suggestions_group.setLayout(suggestions_layout)
        self.coverage_splitter.addWidget(suggestions_group)

        self.coverage_splitter.setSizes([300, 300])
        self.lexicon_splitter.addWidget(self.coverage_splitter)

        self.lexicon_splitter.setSizes([300, 500])

        layout.addWidget(self.lexicon_splitter)

    def _create_run_section(self, parent_layout):
        """Create the run analysis section."""
        bottom_splitter = QSplitter(Qt.Horizontal)

        self.checks_frame = QFrame()
        self.checks_frame.setObjectName("frame_ready_pending")
        self.checks_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.checks_frame.setLineWidth(2)
        checks_layout = QVBoxLayout()

        self.checks_title = QLabel("Pre-Run Checks")
        self.checks_title.setObjectName("label_title")
        checks_layout.addWidget(self.checks_title)

        self.sanity_checks_label = QLabel("")
        self.sanity_checks_label.setWordWrap(True)
        checks_layout.addWidget(self.sanity_checks_label)

        self.checks_frame.setLayout(checks_layout)
        bottom_splitter.addWidget(self.checks_frame)

        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(8, 8, 0, 8)

        self.run_btn = QPushButton("Run SSD Analysis")
        self.run_btn.setMinimumHeight(48)
        self.run_btn.setObjectName("btn_run_analysis")
        self.run_btn.setEnabled(False)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._on_run_clicked)
        nav_layout.addWidget(self.run_btn)

        nav_layout.addStretch()

        nav_buttons_layout = QHBoxLayout()

        back_btn = QPushButton("\u2039  Back to Setup")
        back_btn.setObjectName("btn_secondary")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self._go_back)
        nav_buttons_layout.addWidget(back_btn)

        self.view_results_btn = QPushButton("View Results")
        self.view_results_btn.setObjectName("btn_ghost")
        self.view_results_btn.setEnabled(False)
        self.view_results_btn.setCursor(Qt.PointingHandCursor)
        self.view_results_btn.clicked.connect(self._go_to_results)
        nav_buttons_layout.addWidget(self.view_results_btn)

        nav_layout.addLayout(nav_buttons_layout)

        bottom_splitter.addWidget(nav_widget)
        bottom_splitter.setSizes([500, 300])

        parent_layout.addWidget(bottom_splitter)

    # ------------------------------------------------------------------ #
    #  Splitter persistence
    # ------------------------------------------------------------------ #

    def _save_splitter_states(self):
        """Save splitter sizes to QSettings."""
        self._settings.setValue("run_tab/main_splitter", self.main_splitter.saveState())
        self._settings.setValue("run_tab/lexicon_splitter", self.lexicon_splitter.saveState())
        self._settings.setValue("run_tab/coverage_splitter", self.coverage_splitter.saveState())

    def _restore_splitter_states(self):
        """Restore splitter sizes from QSettings."""
        try:
            state = self._settings.value("run_tab/main_splitter")
            if state is not None:
                self.main_splitter.restoreState(state)
        except Exception:
            pass

        try:
            state = self._settings.value("run_tab/lexicon_splitter")
            if state is not None:
                self.lexicon_splitter.restoreState(state)
        except Exception:
            pass

        try:
            state = self._settings.value("run_tab/coverage_splitter")
            if state is not None:
                self.coverage_splitter.restoreState(state)
        except Exception:
            pass

    def hideEvent(self, event):
        """Save splitter state when tab is hidden."""
        self._save_splitter_states()
        super().hideEvent(event)

    # ------------------------------------------------------------------ #
    #  Pre-flight review panel
    # ------------------------------------------------------------------ #

    @staticmethod
    def _html_palette():
        """Return the current theme palette for HTML content styling."""
        from ..theme import build_current_palette
        return build_current_palette()

    def _build_review_html(self) -> str:
        """Build HTML content for the pre-flight review panel."""
        if not self.project:
            return "<p>No project loaded.</p>"

        pal = self._html_palette()
        proj = self.project
        dc = proj.dataset_config
        sc = proj.spacy_config
        ec = proj.embedding_config
        hp = proj.hyperparameters

        is_crossgroup = dc.analysis_type == "crossgroup"
        is_lexicon = dc.concept_mode == "lexicon"

        label_style = (
            f"color: {pal.text_secondary}; font-size: {pal.font_size_sm}; "
            f"text-transform: uppercase;"
        )
        value_style = f"font-size: {pal.font_size_base}; padding-left: 8px;"
        section_style = (
            f"color: {pal.accent}; font-size: 12px; font-weight: 600; "
            f"border-bottom: 1px solid {pal.border}; padding-bottom: 4px; "
            f"margin: 12px 0 8px 0;"
        )

        html = []

        # --- Analysis Type ---
        html.append(f'<div style="{section_style}">Analysis Type</div>')
        html.append('<table cellspacing="6" style="width: 100%;">')
        html.append(
            f'<tr><td style="{label_style}">Type</td>'
            f'<td style="{value_style}">{"Group Comparison" if is_crossgroup else "Continuous Outcome"}</td></tr>'
        )
        html.append(
            f'<tr><td style="{label_style}">Mode</td>'
            f'<td style="{value_style}">{"Lexicon" if is_lexicon else "Full Document"}</td></tr>'
        )

        if is_crossgroup:
            col = dc.group_column or "(not set)"
            html.append(
                f'<tr><td style="{label_style}">Group Column</td>'
                f'<td style="{value_style}">{col}</td></tr>'
            )
            if proj._cached_groups is not None and len(proj._cached_groups) > 0:
                unique = np.unique(proj._cached_groups)
                html.append(
                    f'<tr><td style="{label_style}">Groups</td>'
                    f'<td style="{value_style}">{len(unique)} groups, n={len(proj._cached_groups):,}</td></tr>'
                )
            html.append(
                f'<tr><td style="{label_style}">Permutations</td>'
                f'<td style="{value_style}">{dc.n_perm:,}</td></tr>'
            )
        else:
            col = dc.outcome_column or "(not set)"
            html.append(
                f'<tr><td style="{label_style}">Outcome Column</td>'
                f'<td style="{value_style}">{col}</td></tr>'
            )
            if proj._cached_y is not None:
                y = proj._cached_y
                html.append(
                    f'<tr><td style="{label_style}">Samples</td>'
                    f'<td style="{value_style}">n={len(y):,}, '
                    f'mean={y.mean():.3f}, std={y.std():.3f}</td></tr>'
                )
        html.append("</table>")

        # --- Dataset ---
        n_docs = len(proj._cached_docs) if proj._cached_docs else 0
        mean_words = sc.mean_words_before_stopwords
        html.append(f'<div style="{section_style}">Dataset</div>')
        html.append('<table cellspacing="6" style="width: 100%;">')
        if dc.csv_path:
            html.append(
                f'<tr><td style="{label_style}">File</td>'
                f'<td style="{value_style}; word-break: break-all;">{dc.csv_path.name}</td></tr>'
            )
        if dc.text_column:
            html.append(
                f'<tr><td style="{label_style}">Text Column</td>'
                f'<td style="{value_style}">{dc.text_column}</td></tr>'
            )
        html.append(
            f'<tr><td style="{label_style}">Documents</td>'
            f'<td style="{value_style}">{n_docs:,}</td></tr>'
        )
        if mean_words > 0:
            html.append(
                f'<tr><td style="{label_style}">Mean Words / Doc</td>'
                f'<td style="{value_style}">~{mean_words:.0f} (pre-stopword)</td></tr>'
            )
        html.append("</table>")

        # --- Text Processing ---
        html.append(f'<div style="{section_style}">Text Processing (spaCy)</div>')
        html.append('<table cellspacing="6" style="width: 100%;">')
        html.append(
            f'<tr><td style="{label_style}">Model</td>'
            f'<td style="{value_style}">{sc.model}</td></tr>'
        )
        html.append(
            f'<tr><td style="{label_style}">Language</td>'
            f'<td style="{value_style}">{sc.language}</td></tr>'
        )
        html.append(
            f'<tr><td style="{label_style}">Lemmatize</td>'
            f'<td style="{value_style}">{"Yes" if sc.lemmatize else "No"}</td></tr>'
        )
        html.append(
            f'<tr><td style="{label_style}">Remove Stopwords</td>'
            f'<td style="{value_style}">{"Yes" if sc.remove_stopwords else "No"}</td></tr>'
        )
        html.append("</table>")

        # --- Embeddings ---
        html.append(f'<div style="{section_style}">Embeddings</div>')
        html.append('<table cellspacing="6" style="width: 100%;">')
        if ec.loaded:
            html.append(
                f'<tr><td style="{label_style}">Vocabulary</td>'
                f'<td style="{value_style}">{ec.vocab_size:,} words, {ec.embedding_dim}d</td></tr>'
            )
            if ec.model_path:
                html.append(
                    f'<tr><td style="{label_style}">File</td>'
                    f'<td style="{value_style}; word-break: break-all;">{ec.model_path.name}</td></tr>'
                )
            if ec.coverage_pct > 0:
                cov_str = f"{ec.coverage_pct:.1f}%"
                if ec.n_oov > 0:
                    cov_str += f" ({ec.n_oov:,} OOV)"
                html.append(
                    f'<tr><td style="{label_style}">Coverage</td>'
                    f'<td style="{value_style}">{cov_str}</td></tr>'
                )
            html.append(
                f'<tr><td style="{label_style}">L2 Normalize</td>'
                f'<td style="{value_style}">{"Yes" if ec.l2_normalize else "No"}</td></tr>'
            )
            html.append(
                f'<tr><td style="{label_style}">ABTT</td>'
                f'<td style="{value_style}">{"Yes" if ec.abtt_enabled else "No"}'
                f'{f" (m={ec.abtt_m})" if ec.abtt_enabled else ""}</td></tr>'
            )
        else:
            html.append(
                f'<tr><td style="{label_style}">Status</td>'
                f'<td style="{value_style}; color: {pal.error};">Not loaded</td></tr>'
            )
        html.append("</table>")

        # --- Hyperparameters ---
        html.append(f'<div style="{section_style}">Hyperparameters</div>')
        html.append('<table cellspacing="6" style="width: 100%;">')
        if is_lexicon:
            html.append(
                f'<tr><td style="{label_style}">Context Window</td>'
                f'<td style="{value_style}">\u00b1{hp.context_window_size}</td></tr>'
            )
        html.append(
            f'<tr><td style="{label_style}">SIF Parameter</td>'
            f'<td style="{value_style}">{hp.sif_a:.5f}</td></tr>'
        )
        if not is_crossgroup:
            pca_mode = hp.n_pca_mode
            if pca_mode == "auto":
                html.append(
                    f'<tr><td style="{label_style}">PCA</td>'
                    f'<td style="{value_style}">Auto sweep ({hp.sweep_k_min}\u2013{hp.sweep_k_max}, '
                    f'step {hp.sweep_k_step})</td></tr>'
                )
                html.append(
                    f'<tr><td style="{label_style}">AUCK Radius</td>'
                    f'<td style="{value_style}">{hp.auck_radius}</td></tr>'
                )
                html.append(
                    f'<tr><td style="{label_style}">Beta Smoothing</td>'
                    f'<td style="{value_style}">{hp.beta_smooth_kind}, '
                    f'window={hp.beta_smooth_win}</td></tr>'
                )
                html.append(
                    f'<tr><td style="{label_style}">Weight by Size</td>'
                    f'<td style="{value_style}">{"Yes" if hp.weight_by_size else "No"}</td></tr>'
                )
            else:
                html.append(
                    f'<tr><td style="{label_style}">PCA</td>'
                    f'<td style="{value_style}">K={hp.n_pca_manual}</td></tr>'
                )
            html.append(
                f'<tr><td style="{label_style}">Unit Beta</td>'
                f'<td style="{value_style}">{"Yes" if hp.use_unit_beta else "No"}</td></tr>'
            )
        html.append(
            f'<tr><td style="{label_style}">L2 Normalize Docs</td>'
            f'<td style="{value_style}">{"Yes" if hp.l2_normalize_docs else "No"}</td></tr>'
        )
        if hp.clustering_k_auto:
            cluster_k_str = f"auto / silhouette ({hp.clustering_k_min}\u2013{hp.clustering_k_max})"
        else:
            cluster_k_str = f"{hp.clustering_k_min}\u2013{hp.clustering_k_max}"
        html.append(
            f'<tr><td style="{label_style}">Clustering</td>'
            f'<td style="{value_style}">Top {hp.clustering_topn}, '
            f'K={cluster_k_str}, '
            f'{hp.clustering_top_words} top words'
            f'</td></tr>'
        )
        html.append("</table>")

        return "".join(html)

    # ------------------------------------------------------------------ #
    #  Token management methods
    # ------------------------------------------------------------------ #

    def _add_token(self):
        """Add a token from the input field."""
        token = self.token_input.text().strip().lower()
        if not token:
            return
        self._add_token_to_lexicon(token)
        self.token_input.clear()

    def _add_token_to_lexicon(self, token: str) -> bool:
        """Add a single token to the lexicon."""
        token = token.strip().lower()
        if not token or token in self.lexicon:
            return False
        self.lexicon.add(token)
        self._update_lexicon_display()
        self._update_coverage()
        return True

    def _paste_tokens(self):
        """Paste multiple tokens from clipboard or dialog."""
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Paste Token List",
            "Enter tokens (comma, space, or newline separated):",
        )
        if not ok or not text:
            return

        import re
        tokens = re.split(r'[,\s\n]+', text)
        tokens = [t.strip().lower() for t in tokens if t.strip()]

        if not tokens:
            return

        added = 0
        for token in tokens:
            if token and token not in self.lexicon:
                self.lexicon.add(token)
                added += 1

        self._update_lexicon_display()
        self._update_coverage()

        QMessageBox.information(self, "Import Complete", f"Added {added} tokens.")

    def _remove_selected_tokens(self):
        """Remove selected tokens from lexicon."""
        for item in self.lexicon_list.selectedItems():
            token = item.text()
            self.lexicon.discard(token)
        self._update_lexicon_display()
        self._update_coverage()

    def _clear_lexicon(self):
        """Clear all tokens from lexicon."""
        if not self.lexicon:
            return

        reply = QMessageBox.question(
            self, "Clear Lexicon",
            f"Remove all {len(self.lexicon)} tokens?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.lexicon.clear()
            self._update_lexicon_display()
            self._update_coverage()

    def _add_suggestion(self, row: int, column: int):
        """Add a suggestion from the table to the lexicon."""
        item = self.suggestions_table.item(row, 0)
        if item:
            self._add_token_to_lexicon(item.text())

    def _update_lexicon_display(self):
        """Update the lexicon list display."""
        self.lexicon_list.clear()
        for token in sorted(self.lexicon):
            self.lexicon_list.addItem(token)
        self.lexicon_count_label.setText(f"{len(self.lexicon)} tokens")
        self._update_run_button()

    # ------------------------------------------------------------------ #
    #  Coverage & Suggestions — analysis-type aware
    # ------------------------------------------------------------------ #

    def _is_crossgroup(self) -> bool:
        if not self.project:
            return False
        return self.project.dataset_config.analysis_type == "crossgroup"

    def _get_coverage_data(self):
        """Return (docs, var, var_type) for coverage functions."""
        if not self.project:
            return None, None, None
        docs = self.project._cached_docs
        if not docs:
            return None, None, None

        if self._is_crossgroup():
            groups = self.project._cached_groups
            if groups is None or len(groups) == 0:
                return None, None, None
            return docs, groups, "categorical"
        else:
            y = self.project._cached_y
            if y is None:
                return None, None, None
            return docs, y, "continuous"

    def _update_coverage(self):
        """Update coverage statistics using ssdiff's coverage_by_lexicon."""
        if not self.project or not self.lexicon:
            self.coverage_stats.setText("Add tokens to see coverage statistics")
            self.coverage_warnings.setText("")
            self.coverage_table.setRowCount(0)
            self._update_run_button()
            return

        docs, var, var_type = self._get_coverage_data()
        if docs is None or var is None:
            self.coverage_stats.setText("Data not loaded or column not selected")
            self.coverage_table.setRowCount(0)
            self._update_run_button()
            return

        try:
            from ssdiff import coverage_by_lexicon
            summary, per_token = coverage_by_lexicon(
                (docs, var), lexicon=self.lexicon, var_type=var_type
            )
        except Exception as e:
            self.coverage_stats.setText(f"Coverage computation failed: {e}")
            self.coverage_table.setRowCount(0)
            self._update_run_button()
            return

        n_docs = len(docs)
        cov_pct = summary["cov_all"] * 100

        if var_type == "categorical":
            stats_text = (
                f"Documents with any hit: {summary['docs_any']:,} / {n_docs:,} "
                f"({cov_pct:.1f}%)\n"
                f"Min group coverage: {summary.get('q1', 0) * 100:.1f}%  |  "
                f"Max group coverage: {summary.get('q4', 0) * 100:.1f}%\n"
                f"Cram\u00e9r's V (any hit vs group): {summary.get('corr_any', 0):.4f}\n"
                f"Hits per doc \u2014 mean: {summary['hits_mean']:.2f}, "
                f"median: {summary['hits_median']:.1f}"
            )
            self.coverage_table.setHorizontalHeaderLabels([
                "Word", "Docs", "Cov%", "Min Grp%", "Max Grp%", "Cram\u00e9r's V",
            ])
        else:
            stats_text = (
                f"Documents with any hit: {summary['docs_any']:,} / {n_docs:,} "
                f"({cov_pct:.1f}%)\n"
                f"Q1 coverage: {summary['q1'] * 100:.1f}%  |  "
                f"Q4 coverage: {summary['q4'] * 100:.1f}%\n"
                f"Correlation (any hit vs outcome): {summary['corr_any']:.4f}\n"
                f"Hits per doc \u2014 mean: {summary['hits_mean']:.2f}, "
                f"median: {summary['hits_median']:.1f}\n"
                f"Types per doc \u2014 mean: {summary['types_mean']:.2f}, "
                f"median: {summary['types_median']:.1f}"
            )
            self.coverage_table.setHorizontalHeaderLabels([
                "Word", "Docs", "Cov%", "Q1%", "Q4%", "Corr",
            ])
        self.coverage_stats.setText(stats_text)

        # Warnings
        warnings = []
        if len(self.lexicon) < 5:
            warnings.append("Small lexicon (< 5 tokens)")
        if cov_pct < 30:
            warnings.append(f"Low coverage ({cov_pct:.1f}%)")
        zero_docs = per_token[per_token["docs"] == 0]
        if len(zero_docs) > 0:
            oov_words = ", ".join(zero_docs["word"].tolist()[:5])
            warnings.append(
                f"{len(zero_docs)} token(s) with 0 docs: {oov_words}"
            )

        if warnings:
            self.coverage_warnings.setText("\n".join(warnings))
            self.coverage_warnings.setObjectName("label_coverage_warn")
        else:
            self.coverage_warnings.setText("Coverage looks good")
            self.coverage_warnings.setObjectName("label_coverage_ok")
        self.coverage_warnings.style().unpolish(self.coverage_warnings)
        self.coverage_warnings.style().polish(self.coverage_warnings)

        # Per-token table
        self.coverage_table.setRowCount(len(per_token))
        for i, (_, row) in enumerate(per_token.iterrows()):
            self.coverage_table.setItem(
                i, 0, QTableWidgetItem(str(row["word"]))
            )
            self.coverage_table.setItem(
                i, 1, QTableWidgetItem(str(row["docs"]))
            )
            self.coverage_table.setItem(
                i, 2, QTableWidgetItem(f"{row['cov_all'] * 100:.1f}%")
            )
            self.coverage_table.setItem(
                i, 3, QTableWidgetItem(f"{row['q1'] * 100:.1f}%")
            )
            self.coverage_table.setItem(
                i, 4, QTableWidgetItem(f"{row['q4'] * 100:.1f}%")
            )
            self.coverage_table.setItem(
                i, 5, QTableWidgetItem(f"{row['corr']:.4f}")
            )

        self._update_run_button()

    def _update_suggestions(self):
        """Update the suggestions table using ssdiff's suggest_lexicon."""
        self.suggestions_table.setRowCount(0)

        if not self.project:
            return

        docs, var, var_type = self._get_coverage_data()
        if docs is None or var is None:
            return

        try:
            from ssdiff import suggest_lexicon
            df = suggest_lexicon((docs, var), var_type=var_type)
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"suggest_lexicon failed: {e}"
            )
            return

        # Filter out tokens already in the lexicon
        df = df[~df["token"].isin(self.lexicon)].head(50)

        if var_type == "categorical":
            self.suggestions_table.setHorizontalHeaderLabels([
                "Token", "Docs", "Cov%", "Cram\u00e9r's V", "Rank",
            ])
        else:
            self.suggestions_table.setHorizontalHeaderLabels([
                "Token", "Docs", "Cov%", "Corr", "Rank",
            ])

        self.suggestions_table.setRowCount(len(df))
        for i, (_, row) in enumerate(df.iterrows()):
            self.suggestions_table.setItem(
                i, 0, QTableWidgetItem(str(row["token"]))
            )
            self.suggestions_table.setItem(
                i, 1, QTableWidgetItem(str(row["docs"]))
            )
            self.suggestions_table.setItem(
                i, 2, QTableWidgetItem(f"{row['cov_all'] * 100:.1f}%")
            )
            self.suggestions_table.setItem(
                i, 3, QTableWidgetItem(f"{row['corr']:.4f}")
            )
            self.suggestions_table.setItem(
                i, 4, QTableWidgetItem(f"{row['rank']:.4f}")
            )

    # ------------------------------------------------------------------ #
    #  Sanity checks & run button
    # ------------------------------------------------------------------ #

    def _update_sanity_checks(self):
        """Update the pre-run sanity checks display."""
        if not self.project:
            self.sanity_checks_label.setText("No project loaded")
            return

        checks = []

        # Data checks
        if self.project._cached_docs:
            n_docs = len(self.project._cached_docs)
            if n_docs >= 200:
                checks.append(f"[OK] {n_docs:,} documents (sufficient)")
            elif n_docs >= 50:
                checks.append(f"[!] {n_docs:,} documents (small but workable)")
            else:
                checks.append(f"[X] {n_docs:,} documents (too few)")
        else:
            checks.append("[X] No documents loaded")

        # Analysis-type-specific checks
        if self._is_crossgroup():
            if self.project._cached_groups is not None and len(self.project._cached_groups) > 0:
                unique = np.unique(self.project._cached_groups)
                n_groups = len(unique)
                if n_groups >= 2:
                    checks.append(f"[OK] {n_groups} groups selected")
                else:
                    checks.append("[X] Need at least 2 groups")
            else:
                checks.append("[X] No group column selected")
        else:
            if self.project._cached_y is not None:
                y = self.project._cached_y
                y_std = np.std(y)
                if y_std > 0.1:
                    checks.append(f"[OK] Outcome variance: {y_std:.3f}")
                else:
                    checks.append(f"[!] Low outcome variance: {y_std:.3f}")
            else:
                checks.append("[X] No outcome column selected")

        # Embeddings check
        if self.project._cached_kv is not None:
            checks.append("[OK] Embeddings loaded")
        else:
            checks.append("[X] Embeddings not loaded")

        # Mode-specific checks
        is_lexicon = self.project.dataset_config.concept_mode == "lexicon"
        if is_lexicon:
            if len(self.lexicon) >= 3:
                checks.append(f"[OK] Lexicon: {len(self.lexicon)} tokens")
            elif len(self.lexicon) > 0:
                checks.append(f"[!] Small lexicon: {len(self.lexicon)} tokens")
            else:
                checks.append("[X] Empty lexicon")
        else:
            checks.append("[OK] Full document mode selected")

        all_ok = all("[X]" not in c for c in checks)

        if all_ok:
            self.checks_frame.setObjectName("frame_ready_ok")
            self.checks_title.setText("Ready to Run")
        else:
            self.checks_frame.setObjectName("frame_ready_pending")
            self.checks_title.setText("Pre-Run Checks")
        self.checks_frame.style().unpolish(self.checks_frame)
        self.checks_frame.style().polish(self.checks_frame)

        self.sanity_checks_label.setText("\n".join(checks))

    def _update_run_button(self):
        """Update the run button enabled state."""
        can_run = False

        if self.project and self.project._cached_docs:
            has_embeddings = self.project._cached_kv is not None

            has_var = False
            if self._is_crossgroup():
                has_var = (
                    self.project._cached_groups is not None
                    and len(self.project._cached_groups) > 0
                    and len(np.unique(self.project._cached_groups)) >= 2
                )
            else:
                has_var = self.project._cached_y is not None

            if has_var and has_embeddings:
                is_lexicon = self.project.dataset_config.concept_mode == "lexicon"
                if is_lexicon:
                    can_run = len(self.lexicon) > 0
                else:
                    can_run = True

        self.run_btn.setEnabled(can_run)
        self._update_sanity_checks()

    def _go_back(self):
        """Go back to Stage 1."""
        main_window = self.window()
        if hasattr(main_window, 'go_to_stage'):
            main_window.go_to_stage(1)

    def _go_to_results(self):
        """Navigate to Stage 3 to view saved results."""
        main_window = self.window()
        if hasattr(main_window, 'go_to_stage'):
            main_window.go_to_stage(3)

    def _on_run_clicked(self):
        """Handle run button click."""
        if not self.project:
            return

        dc = self.project.dataset_config
        config = ConceptConfig()

        # Mode from project config (set in Setup tab)
        if dc.concept_mode == "lexicon":
            config.mode = "lexicon"
            config.lexicon_tokens = self.lexicon.copy()
        else:
            config.mode = "fulldoc"
            config.lexicon_tokens = None

        # Analysis type from project config (set in Setup tab)
        if dc.analysis_type == "crossgroup":
            config.analysis_type = "crossgroup"
            config.group_column = dc.group_column
            config.n_perm = dc.n_perm
        else:
            config.analysis_type = "continuous"
            config.outcome_column = dc.outcome_column

        self.run_requested.emit(config)

    # ------------------------------------------------------------------ #
    #  Public methods
    # ------------------------------------------------------------------ #

    def load_project(self, project: Project):
        """Load a project into the UI."""
        self.project = project

        is_lexicon = project.dataset_config.concept_mode == "lexicon"

        # Show/hide lexicon panel based on mode
        self.lexicon_panel.setVisible(is_lexicon)

        # Restore lexicon from most recent run
        self.lexicon.clear()
        if project.runs:
            latest_run = project.runs[-1]
            cc = latest_run.concept_config
            if cc.mode == "lexicon" and cc.lexicon_tokens:
                self.lexicon = cc.lexicon_tokens.copy()

        self._update_lexicon_display()

        # Build review panel
        self.review_panel.setHtml(self._build_review_html())

        # Update coverage if in lexicon mode and we have tokens
        if is_lexicon and self.lexicon:
            self._update_coverage()

        self.view_results_btn.setEnabled(bool(project.runs))
        self._update_sanity_checks()
        self._update_run_button()
