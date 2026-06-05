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
        self.setWindowTitle("Export Transcript")
        self.setFixedWidth(380)
        self._build_layout(speakers)

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self, speakers: List[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.setStyleSheet("""
            QDialog        { background-color: #FFFFFF; }
            QLabel         { font-weight: 600; font-size: 13px; color: #111827; }
            QComboBox, QLineEdit {
                background-color: #F6F7F9;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 6px 12px;
                color: #111827;
            }
            QCheckBox      { font-size: 13px; color: #111827; }
        """)

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
        self.export_btn = QPushButton("Export Now")
        self.export_btn.setObjectName("successAction")
        self.export_btn.clicked.connect(self.accept)
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
