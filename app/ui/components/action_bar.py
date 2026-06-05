"""Action Bar — floating bottom control strip for recording, flagging, and settings.

Single Responsibility: owns all recording-control UI; translates button presses into signals.
Coupling:             zero knowledge of business logic; exposes set_* methods for state updates.
"""
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtCore import Signal

from app.ui.components.vu_meter import VUMeter


class ActionBar(QFrame):
    """Floating bottom-right bar: record, stop, VU meter, timer, and shortcut buttons."""

    # ── Public signals ────────────────────────────────────────────────
    record_toggled    = Signal()
    stop_requested    = Signal()
    flag_requested    = Signal()
    timestamp_requested = Signal()
    settings_requested  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        layout.addWidget(self._build_record_btn())
        layout.addWidget(self._build_stop_btn())
        layout.addWidget(self._build_vu_meter())
        layout.addWidget(self._build_timer_label())
        layout.addWidget(self._build_flag_btn())
        layout.addWidget(self._build_stamp_btn())
        layout.addWidget(self._build_settings_btn())

    def _build_record_btn(self) -> QPushButton:
        self.record_btn = QPushButton("🎙️")
        self.record_btn.setObjectName("recordButton")
        self.record_btn.setFixedSize(48, 48)
        self.record_btn.setToolTip("Start Recording")
        self.record_btn.clicked.connect(self.record_toggled.emit)
        return self.record_btn

    def _build_stop_btn(self) -> QPushButton:
        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setFixedSize(72, 40)
        self.stop_btn.setToolTip("Stop Recording and flush remaining audio")
        self.stop_btn.setStyleSheet("""
            QPushButton#stopButton {
                background-color: #FFFFFF;
                border: 2px solid #E02424;
                color: #E02424;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 6px;
                letter-spacing: 0.5px;
            }
            QPushButton#stopButton:hover {
                background-color: #E02424;
                color: #FFFFFF;
                border-color: #C81E1E;
            }
            QPushButton#stopButton:pressed {
                background-color: #C81E1E;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        return self.stop_btn

    def _build_vu_meter(self) -> VUMeter:
        self.vu_meter = VUMeter()
        return self.vu_meter

    def _build_timer_label(self) -> QLabel:
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet(
            "font-family: monospace; font-size: 14px; font-weight: bold; color: #FF6FA3;"
        )
        return self.timer_label

    def _build_flag_btn(self) -> QPushButton:
        self.flag_btn = QPushButton("🚩 Key")
        self.flag_btn.setToolTip("Mark current segment as Key Point")
        self.flag_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.flag_btn.clicked.connect(self.flag_requested.emit)
        return self.flag_btn

    def _build_stamp_btn(self) -> QPushButton:
        self.stamp_btn = QPushButton("🕒 Stamp")
        self.stamp_btn.setToolTip("Insert timestamp at cursor (Ctrl+K)")
        self.stamp_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.stamp_btn.clicked.connect(self.timestamp_requested.emit)
        return self.stamp_btn

    def _build_settings_btn(self) -> QPushButton:
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        return self.settings_btn

    # ── Public API ────────────────────────────────────────────────────

    def set_recording(self, is_recording: bool) -> None:
        """Reflect the current recording state on the record button."""
        if is_recording:
            self.record_btn.setText("⏸️")
            self.record_btn.setToolTip("Pause / Stop Recording")
        else:
            self.record_btn.setText("🎙️")
            self.record_btn.setToolTip("Start Recording")

    def set_timer(self, label: str) -> None:
        """Update the elapsed-time display."""
        self.timer_label.setText(label)

    def set_vu_level(self, level: float) -> None:
        """Push a new audio level to the VU meter (0.0 – 1.0)."""
        self.vu_meter.set_level(level)

    def apply_compact(self, very_narrow: bool) -> None:
        """Shrink button text to icon-only at very narrow window widths."""
        if very_narrow:
            self.flag_btn.setText("🚩")
            self.stamp_btn.setText("🕒")
            self.settings_btn.setText("⚙️")
        else:
            self.flag_btn.setText("🚩 Key")
            self.stamp_btn.setText("🕒 Stamp")
            self.settings_btn.setText("⚙️ Settings")
