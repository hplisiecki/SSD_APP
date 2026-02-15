"""Reusable info glyph widget for stage views."""

from PySide6.QtWidgets import QLabel, QToolTip
from PySide6.QtCore import Qt, QPoint


class InfoButton(QLabel):
    """A small info glyph that shows a tooltip on hover/click."""

    def __init__(self, tooltip_html: str, parent=None):
        super().__init__("\u24d8", parent)  # circled i
        self._tooltip_html = tooltip_html

        self.setFixedSize(14, 14)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.WhatsThisCursor)
        self.setContentsMargins(0, 0, 0, 0)

        self.setStyleSheet(
            "QLabel {"
            "  color: rgba(255,255,255,0.35);"
            "  font-size: 14px;"
            "  padding: 0px;"
            "  margin: 0px;"
            "}"
            "QLabel:hover {"
            "  color: rgba(255,255,255,0.75);"
            "}"
        )

    # -- tooltip -------------------------------------------------------

    def enterEvent(self, event):
        super().enterEvent(event)
        self._show_tooltip()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._show_tooltip()

    def _show_tooltip(self):
        pos = self.mapToGlobal(QPoint(0, self.height() + 4))
        QToolTip.showText(pos, self._tooltip_html, self)
