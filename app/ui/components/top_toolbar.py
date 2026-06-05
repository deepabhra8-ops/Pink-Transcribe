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
    right_panel_toggled = Signal()

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
        layout.addWidget(self._build_punctuation_toggle())
        layout.addWidget(self._build_model_badge())
        layout.addWidget(self._build_lang_badge())
        layout.addWidget(self._build_export_btn())
        layout.addWidget(self._build_drawer_toggle())

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
        return self.speakers_btn

    def _build_punctuation_toggle(self) -> QPushButton:
        self.punctuation_btn = QPushButton("✍️ Auto-punctuation")
        self.punctuation_btn.setCheckable(True)
        self.punctuation_btn.setChecked(True)
        self.punctuation_btn.setStyleSheet(self._toggle_style())
        return self.punctuation_btn

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
        return self.model_badge

    def _build_lang_badge(self) -> QLabel:
        self.lang_badge = QLabel("Lang: —")
        self.lang_badge.setStyleSheet(self._badge_style())
        return self.lang_badge

    def _build_export_btn(self) -> QPushButton:
        self.export_btn = QPushButton("EXPORT")
        self.export_btn.setObjectName("primaryAction")
        self.export_btn.clicked.connect(self.export_requested.emit)
        return self.export_btn

    def _build_drawer_toggle(self) -> QPushButton:
        self.drawer_btn = QPushButton("📁")
        self.drawer_btn.setToolTip("Toggle Right Details Drawer")
        self.drawer_btn.setFixedSize(32, 32)
        self.drawer_btn.clicked.connect(self.right_panel_toggled.emit)
        return self.drawer_btn

    # ── Public API ────────────────────────────────────────────────────

    @property
    def auto_detect_speakers(self) -> bool:
        return self.speakers_btn.isChecked()

    @property
    def auto_punctuation(self) -> bool:
        return self.punctuation_btn.isChecked()

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
            self.punctuation_btn.setText("✍️ Punct.")
        else:
            self.speakers_btn.setText("👥 Auto-detect Speakers")
            self.punctuation_btn.setText("✍️ Auto-punctuation")

    def set_compact_badges(self, model: str, lang: str, narrow: bool) -> None:
        """Set compact or full badge text depending on the narrow flag."""
        if narrow:
            self.model_badge.setText(f"M: {model}")
            self.lang_badge.setText(f"L: {lang}")
        else:
            self.model_badge.setText(f"Model: {model}")
            self.lang_badge.setText(f"Lang: {lang}")
