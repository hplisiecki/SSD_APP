"""Dismissible update-available banner shown at the bottom of the main window."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices


class UpdateBanner(QFrame):
    """A thin info strip shown when a newer version of SSD is available.

    Layout:  [ℹ] [message — stretches]  [Download]  [✕]
    """

    def __init__(self, version: str, url: str, parent=None):
        super().__init__(parent)
        self.setObjectName("update_banner")
        self._url = url

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        icon_label = QLabel("ℹ")
        icon_label.setObjectName("update_banner_icon")
        icon_label.setAlignment(Qt.AlignVCenter)
        layout.addWidget(icon_label)

        text_label = QLabel(
            f"SSD v{version} is available.  "
            "Your projects are stored separately and will not be affected."
        )
        text_label.setObjectName("update_banner_text")
        text_label.setAlignment(Qt.AlignVCenter)
        layout.addWidget(text_label, stretch=1)

        download_btn = QPushButton("Download")
        download_btn.setObjectName("update_banner_download")
        download_btn.setCursor(Qt.PointingHandCursor)
        download_btn.clicked.connect(self._open_download)
        layout.addWidget(download_btn)

        dismiss_btn = QPushButton("✕")
        dismiss_btn.setObjectName("update_banner_dismiss")
        dismiss_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn.setFixedWidth(28)
        dismiss_btn.clicked.connect(self.hide)
        layout.addWidget(dismiss_btn)

    def _open_download(self):
        QDesktopServices.openUrl(QUrl(self._url))
