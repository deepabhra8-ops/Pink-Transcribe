"""Export Dialog — configuration modal for transcript format, speakers, and options."""
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QCheckBox, QLineEdit,
)


class ExportDialog(QDialog):
    """Configuration dialog for exporting a transcript in various formats."""

    def __init__(self, speakers: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.setFixedWidth(380)
        self._build_layout(speakers)

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self, speakers: List[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.setStyleSheet("""
            QDialog        { background-color: #FFFFFF; }
            QLabel         { font-weight: 600; font-size: 12px; color: #374151; }
            QComboBox, QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #EAD8DD;
                border-radius: 6px;
                padding: 6px 12px;
                color: #111827;
                font-size: 13px;
            }
            QComboBox:hover, QLineEdit:hover {
                border-color: #FF6FA3;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #FF6FA3;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
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
            QCheckBox      { font-size: 12px; color: #374151; }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #ffffff;
                border: 1.5px solid #EAD8DD;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #FF6FA3;
                border-color: #FF6FA3;
                image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNGRkZGRkYiIHN0cm9rZS13aWR0aD0iNCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSIyMCA2IDkgMTcgNCAxMiI+PC9wb2x5bGluZT48L3N2Zz4=");
            }
        """)

        # Title
        title_label = QLabel("EXPORT OPTIONS")
        title_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #0F7A75; letter-spacing: 1.5px; margin-bottom: 4px;"
        )
        layout.addWidget(title_label)

        # Format selector
        layout.addWidget(QLabel("File Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Plain Text (.txt)",
            "SubRip (.srt)",
            "WebVTT (.vtt)",
            "MS Word HTML (.docx/html)",
        ])
        layout.addWidget(self.format_combo)

        # Options
        layout.addWidget(QLabel("Options:"))
        self.inc_speakers_cb = QCheckBox("Include Speaker Labels")
        self.inc_speakers_cb.setChecked(True)
        self.inc_timestamps_cb = QCheckBox("Include Timestamps")
        self.inc_timestamps_cb.setChecked(True)
        layout.addWidget(self.inc_speakers_cb)
        layout.addWidget(self.inc_timestamps_cb)

        # Per-speaker rename fields
        self.mapping_inputs: dict[str, QLineEdit] = {}
        if speakers:
            layout.addWidget(QLabel("Speaker Mapping (rename for export):"))
            for spk in sorted(speakers):
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{spk}:"))
                inp = QLineEdit()
                inp.setPlaceholderText(spk)
                row.addWidget(inp)
                layout.addLayout(row)
                self.mapping_inputs[spk] = inp

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #EAD8DD;
                color: #6B7280;
                padding: 6px 18px;
                border-radius: 15px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F3F4F6;
                color: #374151;
            }
            QPushButton:pressed {
                background-color: #E5E7EB;
            }
        """)
        
        self.export_btn = QPushButton("Export Now")
        self.export_btn.clicked.connect(self.accept)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #0F7A75;
                border: 1px solid #0F7A75;
                color: #ffffff;
                padding: 6px 18px;
                border-radius: 15px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0C615D;
                border-color: #0C615D;
            }
            QPushButton:pressed {
                background-color: #084946;
                border-color: #084946;
            }
        """)
        
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.export_btn)
        layout.addLayout(btn_row)

    # ── Public helpers ────────────────────────────────────────────────

    @property
    def chosen_format(self) -> str:
        """Return a short format key: 'txt', 'srt', 'vtt', or 'html'."""
        text = self.format_combo.currentText().lower()
        for key in ("srt", "vtt", "docx"):
            if key in text:
                return "html" if key == "docx" else key
        return "txt"

    @property
    def speaker_mapping(self) -> dict[str, str]:
        """Return a name→display-name mapping from the rename fields."""
        return {
            spk: (inp.text().strip() or spk)
            for spk, inp in self.mapping_inputs.items()
        }
