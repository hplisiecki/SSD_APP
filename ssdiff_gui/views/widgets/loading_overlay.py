"""Reusable loading overlay widget with animated spinner."""

import math

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt, QPointF, QElapsedTimer
from PySide6.QtGui import QPainter, QColor


class LoadingOverlay(QWidget):
    """Opaque overlay with a fading-dots spinner.

    Parent it to any widget; call ``start()`` to show and ``stop()`` to hide.
    The overlay always fills its parent via ``resizeEvent``.

    The spinner is a ring of small dots whose brightness rotates around the
    circle based on wall-clock time.  Because nothing moves spatially (only
    opacity changes), the animation looks smooth even when the event loop can
    only repaint a few times per second during synchronous work.
    """

    _DOT_COUNT = 12
    _RING_RADIUS = 18  # distance from centre to each dot centre
    _DOT_RADIUS = 3  # radius of each dot
    _TIMER_MS = 16  # ~60 fps target
    _CYCLE_MS = 1000  # one full brightness revolution per second

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(self._TIMER_MS)
        self._timer.timeout.connect(self._tick)

        self._bg_color = QColor("#14151f")
        self._accent_color = QColor("#6c9ce6")

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.hide()

    # ------------------------------------------------------------------ #
    #  Theme integration
    # ------------------------------------------------------------------ #

    def _resolve_theme_colors(self):
        """Pick up the current palette from saved preferences."""
        try:
            from ssdiff_gui.theme import build_current_palette

            palette = build_current_palette()
            self._bg_color = QColor(palette.bg_base)
            self._accent_color = QColor(palette.accent)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def start(self):
        """Show the overlay and start the spinner animation."""
        self._resolve_theme_colors()
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self._elapsed.start()
        self._timer.start()
        self.repaint()

    def stop(self):
        """Stop the spinner and hide the overlay."""
        self._timer.stop()
        self.hide()

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    def _tick(self):
        self.repaint()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fully opaque backdrop
        painter.fillRect(self.rect(), self._bg_color)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Progress through the cycle: 0.0 .. 1.0
        ms = self._elapsed.elapsed() if self._elapsed.isValid() else 0
        phase = (ms % self._CYCLE_MS) / self._CYCLE_MS  # 0..1

        painter.setPen(Qt.NoPen)

        for i in range(self._DOT_COUNT):
            # Angular position of this dot (0 = top, clockwise)
            dot_frac = i / self._DOT_COUNT
            angle_rad = 2.0 * math.pi * dot_frac - math.pi / 2.0
            x = cx + self._RING_RADIUS * math.cos(angle_rad)
            y = cy + self._RING_RADIUS * math.sin(angle_rad)

            # Distance from the "bright head" in cycle-space (0..1 wrapping)
            dist = (phase - dot_frac) % 1.0
            # Linear ramp: head (dist=0) → full brightness,
            # tail (dist≈1) → near-invisible.  The tail trails
            # counter-clockwise so the spin appears clockwise.
            opacity = 0.08 + 0.92 * (1.0 - dist)

            color = QColor(self._accent_color)
            color.setAlphaF(opacity)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), self._DOT_RADIUS, self._DOT_RADIUS)

        painter.end()
