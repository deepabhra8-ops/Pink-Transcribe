"""Top Toolbar — persistent header bar with session info, feature toggles, and export CTA.

Single Responsibility: displays and edits session-level metadata and global feature switches.
Coupling:             emits signals for every user action; receives data via public setters.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit,
)
from PySide6.QtCore import Signal


class TopToolbar(QWidget):
    """Persistent top bar: editable title, date badge, feature toggles, model badges, export."""

    # ── Public signals ────────────────────────────────────────────────
    title_edited        = Signal(str)   # new title text
    export_requested    = Signal()
    settings_requested  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addLayout(self._build_title_group())
        layout.addStretch()
        layout.addWidget(self._build_speakers_toggle())
        layout.addWidget(self._build_model_badge())
        layout.addWidget(self._build_lang_badge())
        layout.addWidget(self._build_export_btn())
        layout.addWidget(self._build_settings_btn())

    def _build_title_group(self) -> QVBoxLayout:
        group = QVBoxLayout()
        group.setSpacing(2)

        self.title_input = QLineEdit("New Transcription Session")
        self.title_input.setPlaceholderText("Untitled Session")
        self.title_input.setStyleSheet("""
            QLineEdit {
                font-size: 18px; font-weight: bold; color: #111827;
                background: transparent; border: none; padding: 2px;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #0F7A75; background-color: #FFFFFF;
            }
        """)
        self.title_input.editingFinished.connect(
            lambda: self.title_edited.emit(self.title_input.text().strip())
        )
        group.addWidget(self.title_input)

        self.date_label = QLabel("—")
        self.date_label.setStyleSheet("font-size: 11px; color: #6B7280;")
        group.addWidget(self.date_label)

        return group

    def _toggle_style(self) -> str:
        return """
            QPushButton { font-size: 11px; padding: 4px 8px; }
            QPushButton:checked {
                background-color: #0F7A75; color: #FFFFFF; border-color: #0F7A75;
            }
        """

    def _build_speakers_toggle(self) -> QPushButton:
        self.speakers_btn = QPushButton("👥 Auto-detect Speakers")
        self.speakers_btn.setCheckable(True)
        self.speakers_btn.setChecked(True)
        self.speakers_btn.setStyleSheet(self._toggle_style())
        self.speakers_btn.setFixedHeight(30)
        return self.speakers_btn

    def _badge_style(self) -> str:
        return """
            QLabel {
                background-color: #F6F7F9; border: 1px solid #E5E7EB;
                border-radius: 4px; padding: 4px 8px;
                font-size: 11px; color: #111827; font-weight: 600;
            }
        """

    def _build_model_badge(self) -> QLabel:
        self.model_badge = QLabel("Model: —")
        self.model_badge.setStyleSheet(self._badge_style())
        self.model_badge.setFixedHeight(30)
        return self.model_badge

    def _build_lang_badge(self) -> QLabel:
        self.lang_badge = QLabel("Lang: —")
        self.lang_badge.setStyleSheet(self._badge_style())
        self.lang_badge.setFixedHeight(30)
        return self.lang_badge

    def _build_export_btn(self) -> QPushButton:
        self.export_btn = QPushButton("EXPORT")
        self.export_btn.setObjectName("primaryAction")
        self.export_btn.setFixedHeight(30)
        self.export_btn.setStyleSheet("font-size: 11px; font-weight: bold; padding: 4px 12px;")
        self.export_btn.clicked.connect(self.export_requested.emit)
        return self.export_btn

    def _build_settings_btn(self) -> QPushButton:
        self.settings_btn = QPushButton()
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setFixedSize(32, 30)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #E5E7EB;
                border-radius: 6px; padding: 0;
            }
            QPushButton:hover {
                border-color: #FF6FA3; background-color: #FFE4E6;
            }
        """)

        # Draw gear icon dynamically
        from PySide6.QtGui import QPainter, QIcon, QPixmap, QColor
        from PySide6.QtCore import Qt, QPointF, QSize

        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        center = size / 2.0
        r_outer = size * 0.32
        r_inner = size * 0.15
        tooth_w = size * 0.10
        tooth_h = size * 0.13

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#4B5563"))

        for i in range(8):
            painter.save()
            painter.translate(center, center)
            painter.rotate(i * 45)
            painter.drawRect(-tooth_w/2, -r_outer - tooth_h, tooth_w, tooth_h + 2)
            painter.restore()

        painter.drawEllipse(QPointF(center, center), r_outer, r_outer)

        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.drawEllipse(QPointF(center, center), r_inner, r_inner)
        painter.end()

        self.settings_btn.setIcon(QIcon(pixmap))
        self.settings_btn.setIconSize(QSize(18, 18))
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        return self.settings_btn

    # ── Public API ────────────────────────────────────────────────────

    @property
    def auto_detect_speakers(self) -> bool:
        return self.speakers_btn.isChecked()


    def set_session_info(self, title: str, timestamp: str) -> None:
        """Update the session title and date label."""
        self.title_input.setText(title)
        self.date_label.setText(timestamp)

    def set_badges(self, model: str, device: str, language: str) -> None:
        """Set full-length model and language badge text."""
        lang_str = language.upper() if language != "auto" else "Auto Detect"
        self.model_badge.setText(f"Model: {model} ({device})")
        self.lang_badge.setText(f"Lang: {lang_str}")

    def apply_compact(self, narrow: bool, very_narrow: bool) -> None:
        """Compact or restore button/label text based on available width."""
        self.date_label.setVisible(not very_narrow)
        if narrow:
            self.speakers_btn.setText("👥 Speakers")
        else:
            self.speakers_btn.setText("👥 Auto-detect Speakers")

    def set_compact_badges(self, model: str, lang: str, narrow: bool) -> None:
        """Set compact or full badge text depending on the narrow flag."""
        if narrow:
            self.model_badge.setText(f"M: {model}")
            self.lang_badge.setText(f"L: {lang}")
        else:
            self.model_badge.setText(f"Model: {model}")
            self.lang_badge.setText(f"Lang: {lang}")
