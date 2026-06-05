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

        layout.addWidget(self._build_record_btn(), stretch=0)
        layout.addWidget(self._build_stop_btn(), stretch=0)
        layout.addWidget(self._build_punctuation_btn(), stretch=0)
        layout.addWidget(self._build_vu_meter(), stretch=1)
        layout.addWidget(self._build_timer_label(), stretch=0)

    def _build_record_btn(self) -> QPushButton:
        self.record_btn = QPushButton()
        self.record_btn.setObjectName("recordButton")
        self.record_btn.setFixedSize(48, 48)
        self.record_btn.setToolTip("Start Recording")
        
        # Load custom record icon
        import os
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize
        components_dir = os.path.dirname(__file__)
        root_dir = os.path.abspath(os.path.join(components_dir, "..", "..", ".."))
        icon_path = os.path.join(root_dir, "Icons", "4181205.png")
        if os.path.exists(icon_path):
            self.record_btn.setIcon(QIcon(icon_path))
            self.record_btn.setIconSize(QSize(36, 36))
            
        self.record_btn.setStyleSheet("""
            QPushButton#recordButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton#recordButton:hover {
                background-color: rgba(224, 36, 36, 0.1);
                border-radius: 24px;
            }
        """)
        self.record_btn.clicked.connect(self.record_toggled.emit)
        return self.record_btn

    def _build_stop_btn(self) -> QPushButton:
        self.stop_btn = QPushButton()
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setFixedSize(48, 48)
        self.stop_btn.setToolTip("Stop Recording and flush remaining audio")
        
        # Load custom stop icon
        import os
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize
        components_dir = os.path.dirname(__file__)
        root_dir = os.path.abspath(os.path.join(components_dir, "..", "..", ".."))
        icon_path = os.path.join(root_dir, "Icons", "90-902933_to-stop-recording-press-the-stop-button-red.png")
        if os.path.exists(icon_path):
            self.stop_btn.setIcon(QIcon(icon_path))
            self.stop_btn.setIconSize(QSize(36, 36))
            
        self.stop_btn.setStyleSheet("""
            QPushButton#stopButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton#stopButton:hover {
                background-color: rgba(224, 36, 36, 0.1);
                border-radius: 24px;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        return self.stop_btn

    def _build_punctuation_btn(self) -> QPushButton:
        self.punctuation_btn = QPushButton()
        self.punctuation_btn.setObjectName("punctuationButton")
        self.punctuation_btn.setFixedSize(40, 40)
        self.punctuation_btn.setCheckable(True)
        self.punctuation_btn.setChecked(True)
        self.punctuation_btn.setToolTip("Auto-punctuation")
        
        # Resolve path to Icons/Gemini_Generated_Image_foyfezfoyfezfoyf.png
        import os
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize
        components_dir = os.path.dirname(__file__)
        root_dir = os.path.abspath(os.path.join(components_dir, "..", "..", ".."))
        icon_path = os.path.join(root_dir, "Icons", "Gemini_Generated_Image_foyfezfoyfezfoyf.png")
        if os.path.exists(icon_path):
            self.punctuation_btn.setIcon(QIcon(icon_path))
            self.punctuation_btn.setIconSize(QSize(28, 28))
            
        self.punctuation_btn.setStyleSheet("""
            QPushButton#punctuationButton {
                background-color: #FFFFFF;
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                padding: 0px;
            }
            QPushButton#punctuationButton:hover {
                border-color: #FF6FA3;
                background-color: #FFE4E6;
            }
            QPushButton#punctuationButton:checked {
                background-color: #FFE4E6;
                border-color: #FF6FA3;
            }
            QPushButton#punctuationButton:checked:hover {
                background-color: #FFCCD5;
                border-color: #FF4A8B;
            }
        """)
        return self.punctuation_btn

    def _build_vu_meter(self) -> VUMeter:
        self.vu_meter = VUMeter()
        return self.vu_meter

    def _build_timer_label(self) -> QLabel:
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet(
            "font-family: monospace; font-size: 14px; font-weight: bold; color: #FF6FA3; margin: 0; padding: 0 4px;"
        )
        from PySide6.QtWidgets import QSizePolicy
        self.timer_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        return self.timer_label



    # ── Public API ────────────────────────────────────────────────────

    @property
    def auto_punctuation(self) -> bool:
        """Expose the auto punctuation toggle state."""
        return self.punctuation_btn.isChecked()

    def set_recording(self, is_recording: bool) -> None:
        """Reflect the current recording state on the record button."""
        import os
        from PySide6.QtGui import QIcon, QPixmap, QColor
        from PySide6.QtCore import Qt, QSize
        
        components_dir = os.path.dirname(__file__)
        root_dir = os.path.abspath(os.path.join(components_dir, "..", "..", ".."))
        
        if is_recording:
            # Draw a custom pause icon: two white bars in a red circle
            size = 48
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            
            from PySide6.QtGui import QPainter
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#E02424"))
            painter.drawEllipse(2, 2, size - 4, size - 4)
            
            # White pause lines
            painter.setBrush(QColor("#FFFFFF"))
            w = 4
            h = 16
            gap = 5
            x1 = size / 2 - w - gap / 2
            x2 = size / 2 + gap / 2
            y = size / 2 - h / 2
            painter.drawRect(x1, y, w, h)
            painter.drawRect(x2, y, w, h)
            painter.end()
            
            self.record_btn.setIcon(QIcon(pixmap))
            self.record_btn.setIconSize(QSize(36, 36))
            self.record_btn.setToolTip("Pause / Stop Recording")
        else:
            icon_path = os.path.join(root_dir, "Icons", "4181205.png")
            if os.path.exists(icon_path):
                self.record_btn.setIcon(QIcon(icon_path))
                self.record_btn.setIconSize(QSize(36, 36))
            self.record_btn.setToolTip("Start Recording")

    def set_timer(self, label: str) -> None:
        """Update the elapsed-time display."""
        self.timer_label.setText(label)

    def set_vu_level(self, level: float) -> None:
        """Push a new audio level to the VU meter (0.0 – 1.0)."""
        self.vu_meter.set_level(level)

    def apply_compact(self, very_narrow: bool) -> None:
        """Shrink button text to icon-only at very narrow window widths."""
        pass
