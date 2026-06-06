"""Top Toolbar — persistent header bar with session info, feature toggles, and export CTA.

Single Responsibility: displays and edits session-level metadata and global feature switches.
Coupling:             emits signals for every user action; receives data via public setters.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QComboBox, QCheckBox
)
from PySide6.QtCore import Signal


class TopToolbar(QWidget):
    """Persistent top bar: editable title, date badge, feature toggles, model badges, export."""

    # ── Public signals ────────────────────────────────────────────────
    title_edited        = Signal(str)   # new title text
    export_requested    = Signal()
    settings_requested  = Signal()
    mode_changed        = Signal(str)   # conversation or narration

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
        layout.addWidget(self._build_mode_dropdown())
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
            QLineEdit:hover {
                background-color: #F9FAFB;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #0F7A75; background-color: #FFFFFF;
                border-radius: 0px;
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

    def _build_mode_dropdown(self) -> QComboBox:
        self.mode_dropdown = QComboBox()
        self.mode_dropdown.addItem("💬  Conversation")
        self.mode_dropdown.addItem("📖  Narration")
        self.mode_dropdown.setFixedHeight(30)
        self.mode_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 15px;
                padding: 4px 24px 4px 12px;
                font-size: 11px;
                font-weight: 600;
                color: #374151;
                min-width: 130px;
            }
            QComboBox:hover {
                border-color: #0F7A75;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
            }
            QComboBox::down-arrow {
                image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM2QjcyODAiIHN0cm9rZS13aWR0aD0iMi41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjYgOSAxMiAxNSAxOCA5Ij48L3BvbHlsaW5lPjwvc3ZnPg==");
                width: 10px;
                height: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #EAD8DD;
                border-radius: 8px;
                selection-background-color: #FFE4E6;
                selection-color: #FF6FA3;
                color: #111827;
                outline: none;
                padding: 4px;
            }
        """)
        self.mode_dropdown.currentIndexChanged.connect(self._on_mode_changed)
        return self.mode_dropdown

    def _build_speakers_toggle(self) -> QCheckBox:
        self.speakers_checkbox = QCheckBox("👥 Auto-detect Speakers")
        self.speakers_checkbox.setChecked(True)
        self.speakers_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 6px;
                font-size: 11px;
                font-weight: 600;
                color: #374151;
                background-color: #FFFFFF;
                border: 1px solid #EAD8DD;
                border-radius: 15px;
                padding: 4px 12px;
            }
            QCheckBox:hover {
                border-color: #0F7A75;
                background-color: #E6F4F2;
            }
            QCheckBox::indicator {
                width: 12px;
                height: 12px;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #0F7A75;
                border-color: #0F7A75;
            }
            QCheckBox:disabled {
                color: #9CA3AF;
                background-color: #F9FAFB;
                border-color: #F3F4F6;
            }
            QCheckBox::indicator:disabled {
                background-color: #E5E7EB;
                border-color: #E5E7EB;
            }
        """)
        self.speakers_checkbox.setFixedHeight(30)
        return self.speakers_checkbox

    def _on_mode_changed(self, index: int) -> None:
        mode = self.transcription_mode
        if mode == "Conversation":
            self.speakers_checkbox.setEnabled(True)
        else:
            self.speakers_checkbox.setEnabled(False)
        self.mode_changed.emit(mode)

    def _build_model_badge(self) -> QLabel:
        self.model_badge = QLabel("Model: —")
        self.model_badge.setStyleSheet("""
            QLabel {
                background-color: #FFF0F4;
                border: 1px solid rgba(255, 111, 163, 0.25);
                border-radius: 15px;
                padding: 4px 12px;
                font-size: 11px;
                color: #FF6FA3;
                font-weight: bold;
            }
        """)
        self.model_badge.setFixedHeight(30)
        return self.model_badge

    def _build_lang_badge(self) -> QLabel:
        self.lang_badge = QLabel("Lang: —")
        self.lang_badge.setStyleSheet("""
            QLabel {
                background-color: #E6F4F2;
                border: 1px solid rgba(15, 122, 117, 0.25);
                border-radius: 15px;
                padding: 4px 12px;
                font-size: 11px;
                color: #0F7A75;
                font-weight: bold;
            }
        """)
        self.lang_badge.setFixedHeight(30)
        return self.lang_badge

    def _build_export_btn(self) -> QPushButton:
        self.export_btn = QPushButton("EXPORT")
        self.export_btn.setObjectName("primaryAction")
        self.export_btn.setFixedHeight(30)
        self.export_btn.setStyleSheet("""
            QPushButton#primaryAction {
                background-color: #FF6FA3;
                border: 1px solid #FF6FA3;
                border-radius: 15px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 16px;
            }
            QPushButton#primaryAction:hover {
                background-color: #FF4A8B;
                border-color: #FF4A8B;
            }
            QPushButton#primaryAction:pressed {
                background-color: #E63C78;
                border-color: #E63C78;
            }
        """)
        self.export_btn.clicked.connect(self.export_requested.emit)
        return self.export_btn

    def _build_settings_btn(self) -> QPushButton:
        self.settings_btn = QPushButton()
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #EAD8DD;
                border-radius: 15px;
                padding: 0;
            }
            QPushButton:hover {
                border-color: #FF6FA3;
                background-color: #FFF5F7;
            }
            QPushButton:pressed {
                background-color: #FFE4E6;
            }
        """)

        # Draw gear icon dynamically
        from PySide6.QtGui import QPainter, QIcon, QPixmap, QColor
        from PySide6.QtCore import Qt, QPointF, QSize

        size = 30
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
        return self.speakers_checkbox.isChecked() and self.speakers_checkbox.isEnabled()

    @property
    def transcription_mode(self) -> str:
        text = self.mode_dropdown.currentText()
        if "Conversation" in text:
            return "Conversation"
        return "Narration"

    def set_transcription_mode(self, mode: str) -> None:
        """Set the current transcription mode in the dropdown."""
        self.mode_dropdown.blockSignals(True)
        for i in range(self.mode_dropdown.count()):
            if mode in self.mode_dropdown.itemText(i):
                self.mode_dropdown.setCurrentIndex(i)
                break
        # Manually trigger the state update
        if mode == "Conversation":
            self.speakers_checkbox.setEnabled(True)
        else:
            self.speakers_checkbox.setEnabled(False)
        self.mode_dropdown.blockSignals(False)

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
            self.speakers_checkbox.setText("👥 Speakers")
        else:
            self.speakers_checkbox.setText("👥 Auto-detect Speakers")

    def set_compact_badges(self, model: str, lang: str, narrow: bool) -> None:
        """Set compact or full badge text depending on the narrow flag."""
        if narrow:
            self.model_badge.setText(f"M: {model}")
            self.lang_badge.setText(f"L: {lang}")
        else:
            self.model_badge.setText(f"Model: {model}")
            self.lang_badge.setText(f"Lang: {lang}")
