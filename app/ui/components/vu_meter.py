from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QPainterPath
from PySide6.QtCore import Qt, QTimer, QRectF


class VUMeter(QWidget):
    """Premium VU meter — segmented bars with rounded caps, gradient fill, and peak indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0.0   # 0.0 – 1.0
        self.peak  = 0.0
        self.decay_rate = 0.04

        self.setMinimumHeight(28)
        self.setMinimumWidth(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # ~60 FPS for smooth animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    # ── Public API ────────────────────────────────────────────────────

    def set_level(self, level: float) -> None:
        level = max(0.0, min(1.0, level))
        self.level = level
        if level > self.peak:
            self.peak = level
        self.update()

    # ── Internal ──────────────────────────────────────────────────────

    def _tick(self) -> None:
        changed = False
        if self.level > 0.0:
            self.level = max(0.0, self.level - 0.06)
            changed = True
        if self.peak > 0.0:
            self.peak = max(0.0, self.peak - self.decay_rate)
            changed = True
        if changed:
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # ── Background: soft warm-pink pill — matches app light theme ─
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(0, 0, w, h), 10, 10)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFF0F4")))
        painter.drawPath(bg_path)

        # Subtle border — same pink glow family as the rest of the app
        pen = QPen(QColor(255, 111, 163, 80))   # #FF6FA3 at ~31% opacity
        pen.setWidth(1)
        painter.setPen(pen)
        border_path = QPainterPath()
        border_path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 9.5, 9.5)
        painter.drawPath(border_path)
        painter.setPen(Qt.NoPen)

        # ── Bar geometry ──────────────────────────────────────────────
        pad_x   = 10
        pad_y   = 6
        spacing = 3
        bar_w   = 5.0
        avail_w = w - 2 * pad_x
        num_bars = max(5, int((avail_w + spacing) / (bar_w + spacing)))

        # Recompute bar_w to fill available space perfectly
        bar_w    = (avail_w - spacing * (num_bars - 1)) / num_bars
        bar_max_h = h - 2 * pad_y

        # ── Colour stops ──────────────────────────────────────────────
        # Three zones matching the app palette:
        #  0 – 50 %  →  soft rose   #FF85A1
        # 50 – 80 %  →  brand pink  #FF6FA3
        # 80 – 100%  →  deep fuchsia #FF4A8B
        def _bar_color(ratio: float) -> QColor:
            if ratio < 0.50:
                return QColor("#FF85A1")
            elif ratio < 0.80:
                t = (ratio - 0.50) / 0.30
                r, g, b = 255, int(133 - t * (133 - 111)), int(161 - t * (161 - 163))
                return QColor(r, g, b)
            else:
                t = (ratio - 0.80) / 0.20
                r, g, b = 255, int(111 - t * (111 - 74)), int(163 - t * (163 - 139))
                return QColor(r, g, b)

        for i in range(num_bars):
            ratio    = i / num_bars
            x        = pad_x + i * (bar_w + spacing)
            is_active = ratio <= self.level
            is_peak   = (self.peak > 0.05 and
                         abs(ratio - self.peak) < (1.5 / num_bars))

            color = _bar_color(ratio)

            if is_active:
                # Height breathing: taller bars near the peak for a wave feel
                proximity = 1.0 - abs(ratio - self.level)
                bar_h = bar_max_h * (0.35 + 0.65 * proximity ** 0.4)
                bar_h = max(4.0, bar_h)
                y     = pad_y + (bar_max_h - bar_h)

                # Gradient fill: brighter top, richer bottom
                grad = QLinearGradient(x, y, x, y + bar_h)
                grad.setColorAt(0.0, color.lighter(130))
                grad.setColorAt(0.5, color)
                grad.setColorAt(1.0, color.darker(120))
                painter.setBrush(QBrush(grad))

                # Rounded-cap bar
                radius = min(bar_w / 2, 2.5)
                painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), radius, radius)

                # Soft inner highlight on top quarter
                glow = QColor(255, 255, 255, 90)
                painter.setBrush(QBrush(glow))
                painter.drawRoundedRect(
                    QRectF(x, y, bar_w, bar_h * 0.28), radius, radius
                )

            elif is_peak:
                # Sharp peak marker — thin bright line
                pk_y = pad_y + bar_max_h * (1.0 - self.peak) + bar_max_h * 0.04
                pk_y = max(pad_y, min(pk_y, pad_y + bar_max_h - 3))
                painter.setBrush(QBrush(color.lighter(115)))
                painter.drawRoundedRect(QRectF(x, pk_y, bar_w, 2.5), 1, 1)

            else:
                # Inactive slot: soft pink stub — never competes with active bars
                painter.setBrush(QBrush(QColor("#FFCCD5")))
                bar_h = bar_max_h * 0.28
                y     = pad_y + (bar_max_h - bar_h)
                painter.drawRoundedRect(
                    QRectF(x, y, bar_w, bar_h),
                    min(bar_w / 2, 2.0), min(bar_w / 2, 2.0)
                )

        painter.end()
