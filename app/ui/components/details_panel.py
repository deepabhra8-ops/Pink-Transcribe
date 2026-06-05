"""Details Panel — right contextual drawer: speakers, session notes, and metadata.

Single Responsibility: displays and edits session-scoped detail data.
Coupling:             only emits notes_changed and close_requested; updated via setters.
"""
from typing import Optional, Set

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit,
)
from PySide6.QtCore import Signal


class DetailsPanel(QFrame):
    """Right drawer showing active speakers, editable session notes, and metadata."""

    # ── Public signals ────────────────────────────────────────────────
    notes_changed   = Signal(str)   # emitted on every keystroke
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightPanel")
        self.setFixedWidth(360)
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_speakers_section())
        layout.addLayout(self._build_notes_section())
        layout.addLayout(self._build_metadata_section())
        layout.addStretch()

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title = QLabel("SESSION DETAILS")
        title.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #0F7A75; letter-spacing: 1px;"
        )
        row.addWidget(title)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close_requested.emit)
        row.addWidget(close_btn)
        return row

    def _build_speakers_section(self) -> QLabel:
        # Section label is a sibling widget; add it separately via a helper
        # We keep the section title inline to avoid storing one-off QLabels.
        from PySide6.QtWidgets import QWidget
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        lbl = QLabel("Active Speakers:")
        lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #111827;")
        v.addWidget(lbl)

        self.speakers_label = QLabel("No speakers detected.")
        self.speakers_label.setWordWrap(True)
        self.speakers_label.setStyleSheet("color: #6B7280; font-size: 13px;")
        v.addWidget(self.speakers_label)
        return container

    def _build_notes_section(self) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(4)

        lbl = QLabel("Session Notes:")
        lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #111827;")
        v.addWidget(lbl)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Type notes or action items here... (autosaved)")
        self.notes_edit.setStyleSheet("font-size: 13px;")
        self.notes_edit.textChanged.connect(
            lambda: self.notes_changed.emit(self.notes_edit.toPlainText())
        )
        v.addWidget(self.notes_edit)
        return v

    def _build_metadata_section(self) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(4)

        lbl = QLabel("Session Metadata:")
        lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #111827;")
        v.addWidget(lbl)

        self.meta_label = QLabel("Model: —\nLanguage: —\nCreated: —")
        self.meta_label.setWordWrap(True)
        self.meta_label.setStyleSheet(
            "color: #6B7280; font-size: 12px; font-family: monospace;"
        )
        v.addWidget(self.meta_label)
        return v

    # ── Public API ────────────────────────────────────────────────────

    def update_speakers(self, speakers: Set[str]) -> None:
        """Display the set of detected speaker names."""
        self.speakers_label.setText(
            ", ".join(sorted(speakers)) if speakers else "No speakers detected."
        )

    def update_metadata(self, session: dict) -> None:
        """Render session metadata fields from a session dict."""
        self.meta_label.setText(
            f"ID: {session['id']}\n"
            f"Model: {session['model_size']}\n"
            f"Language: {session['language'].upper()}\n"
            f"Duration: {session['duration_sec']:.1f}s\n"
            f"Created: {session['created_at'][:16].replace('T', ' ')}"
        )

    def set_notes(self, text: Optional[str]) -> None:
        """Set the notes content without triggering the notes_changed signal."""
        self.notes_edit.blockSignals(True)
        self.notes_edit.setPlainText(text or "")
        self.notes_edit.blockSignals(False)

    def clear(self) -> None:
        """Reset all fields to their empty/placeholder state."""
        self.speakers_label.setText("No active session.")
        self.meta_label.setText("No active session.")
        self.notes_edit.blockSignals(True)
        self.notes_edit.clear()
        self.notes_edit.blockSignals(False)
