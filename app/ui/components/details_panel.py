"""Details Panel — right contextual drawer: speakers, session notes, and metadata.

Single Responsibility: displays and edits session-scoped detail data.
Coupling:             only emits notes_changed and close_requested; updated via setters.
"""
from typing import Optional, Set

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QWidget, QSizePolicy
)
from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtGui import QIcon


class DetailsPanel(QFrame):
    """Right drawer showing active speakers, editable session notes, and metadata."""

    # ── Public signals ────────────────────────────────────────────────
    notes_changed   = Signal(str)   # emitted on every keystroke
    collapsed_toggled = Signal(bool)

    EXPANDED_WIDTH  = 360
    COLLAPSED_WIDTH = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightPanel")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._collapsed = False
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        layout.addLayout(self._build_header())
        
        self.speakers_sec = self._build_speakers_section()
        layout.addWidget(self.speakers_sec)

        self.notes_container = QWidget()
        self.notes_container.setLayout(self._build_notes_section())
        layout.addWidget(self.notes_container)

        self.metadata_container = QWidget()
        self.metadata_container.setLayout(self._build_metadata_section())
        layout.addWidget(self.metadata_container)

        # Add dynamic vertical spacer that is only visible when collapsed
        self.spacer_widget = QWidget()
        self.spacer_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.spacer_widget.setVisible(False)
        layout.addWidget(self.spacer_widget)

        layout.addStretch()

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)

        self.title_label = QLabel("SESSION DETAILS")
        self.title_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #0F7A75; letter-spacing: 1px;"
        )
        row.addWidget(self.title_label)

        self.header_spacer = QWidget()
        self.header_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self.header_spacer)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(56, 30)
        self.collapse_btn.setToolTip("Collapse")
        self.collapse_btn.setStyleSheet(
            "QPushButton { border-radius: 6px; }"
        )
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "collapse_icon.png")
        if os.path.exists(icon_path):
            self.collapse_btn.setIcon(QIcon(icon_path))
            self.collapse_btn.setIconSize(QSize(20, 20))
        self.collapse_btn.clicked.connect(self._on_toggle_clicked)
        row.addWidget(self.collapse_btn)
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
        v.setContentsMargins(0, 0, 0, 0)
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
        v.setContentsMargins(0, 0, 0, 0)
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

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    def expand(self) -> None:
        """Restore details panel to its full expanded width."""
        self._collapsed = False
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.layout().setContentsMargins(15, 15, 15, 15)
        self.title_label.setVisible(True)
        self.header_spacer.setVisible(True)
        self.speakers_sec.setVisible(True)
        self.notes_container.setVisible(True)
        self.metadata_container.setVisible(True)
        self.spacer_widget.setVisible(False)
        self.collapse_btn.setToolTip("Collapse")
        self.collapsed_toggled.emit(False)

    def collapse(self) -> None:
        """Shrink details panel to an icon-only rail showing only the expand button."""
        self._collapsed = True
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.layout().setContentsMargins(12, 12, 12, 12)
        self.title_label.setVisible(False)
        self.header_spacer.setVisible(False)
        self.speakers_sec.setVisible(False)
        self.notes_container.setVisible(False)
        self.metadata_container.setVisible(False)
        self.spacer_widget.setVisible(True)
        self.collapse_btn.setToolTip("Expand")
        self.collapsed_toggled.emit(True)

    def _on_toggle_clicked(self) -> None:
        if self._collapsed:
            self.expand()
        else:
            self.collapse()
