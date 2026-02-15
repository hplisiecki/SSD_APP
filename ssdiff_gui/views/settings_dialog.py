"""Application settings dialog for SSD."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QGroupBox,
    QFileDialog,
)
from PySide6.QtCore import QSettings


# QSettings keys
_KEY_PROJECTS_DIR = "projects_directory"
_KEY_AUTOLOAD_EMBEDDINGS = "autoload_embeddings"


def get_autoload_embeddings() -> bool:
    """Return the persisted auto-load-embeddings preference (default False)."""
    s = QSettings("SSD", "SSD")
    return s.value(_KEY_AUTOLOAD_EMBEDDINGS, False, type=bool)


class SettingsDialog(QDialog):
    """Dialog for general application settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)

        self._settings = QSettings("SSD", "SSD")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # --- Projects directory ---
        dir_group = QGroupBox("Projects Directory")
        dir_layout = QVBoxLayout()

        dir_desc = QLabel(
            "Default location used when creating or opening projects."
        )
        dir_desc.setObjectName("label_muted")
        dir_desc.setWordWrap(True)
        dir_layout.addWidget(dir_desc)

        row = QHBoxLayout()
        self._dir_edit = QLineEdit()
        self._dir_edit.setReadOnly(True)
        self._dir_edit.setPlaceholderText("Not set")
        self._dir_edit.setText(
            self._settings.value(_KEY_PROJECTS_DIR, "")
        )
        row.addWidget(self._dir_edit, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        row.addWidget(browse_btn)

        dir_layout.addLayout(row)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # --- Project loading ---
        load_group = QGroupBox("Project Loading")
        load_layout = QVBoxLayout()

        self._autoload_check = QCheckBox(
            "Automatically load embeddings when opening a project"
        )
        self._autoload_check.setChecked(
            self._settings.value(_KEY_AUTOLOAD_EMBEDDINGS, False, type=bool)
        )
        load_layout.addWidget(self._autoload_check)

        load_hint = QLabel(
            "When disabled, projects open faster and embeddings can be "
            "loaded manually from Stage 1.  Enable this if you always want "
            "to jump straight into analysis."
        )
        load_hint.setObjectName("label_muted")
        load_hint.setWordWrap(True)
        load_layout.addWidget(load_hint)

        load_group.setLayout(load_layout)
        layout.addWidget(load_group)

        layout.addStretch()

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _browse_directory(self):
        current = self._dir_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self, "Select Default Projects Directory", current
        )
        if directory:
            self._dir_edit.setText(directory)

    def _save(self):
        self._settings.setValue(_KEY_PROJECTS_DIR, self._dir_edit.text())
        self._settings.setValue(
            _KEY_AUTOLOAD_EMBEDDINGS, self._autoload_check.isChecked()
        )
        self.accept()
