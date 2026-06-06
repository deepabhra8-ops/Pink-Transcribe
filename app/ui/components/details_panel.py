"""Details Panel — right contextual drawer: speakers, session notes, and metadata.

Single Responsibility: displays and edits session-scoped detail data.
Coupling:             only emits notes_changed and close_requested; updated via setters.
"""
from typing import Optional, Set

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QWidget, QSizePolicy
)
from PySide6.QtCore import Signal, QSize, Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QRegion


class DetailsPanel(QFrame):
    """Right drawer showing active speakers, editable session notes, and metadata."""

    # ── Public signals ────────────────────────────────────────────────
    notes_changed   = Signal(str)   # emitted on every keystroke
    collapsed_toggled = Signal(bool)

    EXPANDED_WIDTH  = 360
    COLLAPSED_WIDTH = 56

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightPanel")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._collapsed = False
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header widget
        self.header_widget = self._build_header()
        layout.addWidget(self.header_widget)

        # Content widget
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)

        self.speakers_sec = self._build_speakers_section()
        content_layout.addWidget(self.speakers_sec)

        self.notes_container = QWidget()
        self.notes_container.setLayout(self._build_notes_section())
        content_layout.addWidget(self.notes_container)

        self.metadata_container = QWidget()
        self.metadata_container.setLayout(self._build_metadata_section())
        content_layout.addWidget(self.metadata_container)

        layout.addWidget(self.content_widget)

        # Add dynamic vertical spacer that is only visible when collapsed
        self.spacer_widget = QWidget()
        self.spacer_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.spacer_widget.setVisible(False)
        layout.addWidget(self.spacer_widget)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("detailsHeader")
        header.setStyleSheet("""
            QFrame#detailsHeader {
                background: transparent;
                border-bottom: 1px solid #EAD8DD;
            }
        """)
        
        row = QHBoxLayout(header)
        row.setContentsMargins(10, 12, 10, 12)
        row.setSpacing(6)

        self.title_label = QLabel("SESSION DETAILS")
        self.title_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 700;
            color: #0F7A75;
            letter-spacing: 1.2px;
            background: transparent;
        """)
        row.addWidget(self.title_label)

        self.header_spacer = QWidget()
        self.header_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self.header_spacer)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(36, 30)
        self.collapse_btn.setToolTip("Collapse")
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(255, 111, 163, 0.08);
                border-radius: 6px;
            }
            QPushButton:pressed {
                background-color: rgba(255, 111, 163, 0.15);
                border-radius: 6px;
            }
        """)
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "collapse_icon.png")
        if os.path.exists(icon_path):
            self.collapse_btn.setIcon(QIcon(icon_path))
            self.collapse_btn.setIconSize(QSize(20, 20))
        self.collapse_btn.clicked.connect(self._on_toggle_clicked)
        row.addWidget(self.collapse_btn)
        return header

    def _build_speakers_section(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        lbl = QLabel("Active Speakers:")
        lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #111827; letter-spacing: 0.5px;")
        v.addWidget(lbl)

        self.speakers_label = QLabel("No speakers detected.")
        self.speakers_label.setWordWrap(True)
        self.speakers_label.setStyleSheet("color: #4B5563; font-size: 14px; line-height: 1.4;")
        v.addWidget(self.speakers_label)
        return container

    def _build_notes_section(self) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        lbl = QLabel("Session Notes:")
        lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #111827; letter-spacing: 0.5px;")
        v.addWidget(lbl)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Type notes or action items here... (autosaved)")
        self.notes_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #EAD8DD;
                border-radius: 6px;
                padding: 8px;
                color: #111827;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #FF6FA3;
            }
        """)
        self.notes_edit.textChanged.connect(
            lambda: self.notes_changed.emit(self.notes_edit.toPlainText())
        )
        v.addWidget(self.notes_edit)
        return v

    def _build_metadata_section(self) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        lbl = QLabel("Session Metadata:")
        lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #111827; letter-spacing: 0.5px;")
        v.addWidget(lbl)

        self.meta_label = QLabel("Model: —\nLanguage: —\nCreated: —")
        self.meta_label.setWordWrap(True)
        self.meta_label.setStyleSheet("""
            QLabel {
                color: #4B5563;
                font-size: 13px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                line-height: 1.5;
                background-color: #FFFFFF;
                border: 1px solid #EAD8DD;
                border-radius: 8px;
                padding: 10px;
            }
        """)
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
        self.spacer_widget.setVisible(False)
        self.collapse_btn.setToolTip("Collapse")
        
        # Immediately show widgets
        self.title_label.setVisible(True)
        self.header_spacer.setVisible(True)
        self.content_widget.setVisible(True)
        
        # Fix inner widths during animation
        self.header_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        self.content_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        
        if hasattr(self, "_width_anim") and self._width_anim.state() == QVariantAnimation.Running:
            self._width_anim.stop()
            
        self._width_anim = QVariantAnimation(self)
        self._width_anim.setDuration(200)
        self._width_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(self.EXPANDED_WIDTH)
        
        def update_width(val):
            self.setFixedWidth(val)
            
        def on_finished():
            self.header_widget.setMinimumWidth(0)
            self.content_widget.setMinimumWidth(0)
            self.setFixedWidth(self.EXPANDED_WIDTH)
            self.collapsed_toggled.emit(False)
            
        self._width_anim.valueChanged.connect(update_width)
        self._width_anim.finished.connect(on_finished)
        self._width_anim.start()

    def collapse(self) -> None:
        """Shrink details panel to an icon-only rail showing only the expand button."""
        self._collapsed = True
        self.collapse_btn.setToolTip("Expand")
        
        # Fix inner widths during animation
        self.header_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        self.content_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        
        if hasattr(self, "_width_anim") and self._width_anim.state() == QVariantAnimation.Running:
            self._width_anim.stop()
            
        self._width_anim = QVariantAnimation(self)
        self._width_anim.setDuration(200)
        self._width_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(self.COLLAPSED_WIDTH)
        
        def update_width(val):
            self.setFixedWidth(val)
            
        def on_finished():
            # Hide widgets at the end
            self.title_label.setVisible(False)
            self.header_spacer.setVisible(False)
            self.content_widget.setVisible(False)
            self.header_widget.setMinimumWidth(0)
            self.content_widget.setMinimumWidth(0)
            self.spacer_widget.setVisible(True)
            self.setFixedWidth(self.COLLAPSED_WIDTH)
            self.collapsed_toggled.emit(True)
            
        self._width_anim.valueChanged.connect(update_width)
        self._width_anim.finished.connect(on_finished)
        self._width_anim.start()

    def _on_toggle_clicked(self) -> None:
        if self._collapsed:
            self.expand()
        else:
            self.collapse()

