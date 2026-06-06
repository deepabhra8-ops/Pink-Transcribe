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
        # Warm light gradient — same family as the editor toolbar (#FFF5F7 → #F6F7F9),
        # so the action bar reads as part of the same design language.
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0   #FFF5F7,
                    stop:0.5 #FAF9FB,
                    stop:1   #F6F7F9
                );
                border: 1px solid rgba(255, 111, 163, 0.25);
                border-radius: 14px;
            }
        """)
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        from PySide6.QtWidgets import QFrame as _QFrame
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(6)

        # ── Button cluster (record / stop / punctuation) ───────────────
        layout.addWidget(self._build_record_btn(),      stretch=0)
        layout.addWidget(self._build_stop_btn(),        stretch=0)
        layout.addWidget(self._build_punctuation_btn(), stretch=0)

        # Thin vertical divider between button cluster and VU meter
        divider = _QFrame()
        divider.setFrameShape(_QFrame.VLine)
        divider.setFixedWidth(1)
        divider.setStyleSheet(
            "background-color: rgba(255, 111, 163, 0.20); margin: 8px 4px;"
        )
        layout.addWidget(divider, stretch=0)

        # ── VU meter fills remaining space ────────────────────────────
        layout.addWidget(self._build_vu_meter(),  stretch=1)

        # ── Timer badge ───────────────────────────────────────────────
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
                border-radius: 24px;
                padding: 0px;
            }
            QPushButton#recordButton:hover {
                background-color: rgba(255, 111, 163, 0.12);
            }
            QPushButton#recordButton:pressed {
                background-color: rgba(255, 111, 163, 0.22);
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
                border-radius: 24px;
                padding: 0px;
            }
            QPushButton#stopButton:hover {
                background-color: rgba(224, 36, 36, 0.10);
            }
            QPushButton#stopButton:pressed {
                background-color: rgba(224, 36, 36, 0.20);
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
                border: 1.5px solid #E9D8E4;
                border-radius: 10px;
                padding: 0px;
            }
            QPushButton#punctuationButton:hover {
                background-color: #FFE4E6;
                border-color: #FFADC5;
            }
            QPushButton#punctuationButton:checked {
                background-color: #FFE4E6;
                border: 1.5px solid #FF6FA3;
            }
            QPushButton#punctuationButton:checked:hover {
                background-color: #FFCCD8;
                border-color: #FF4A8B;
            }
            QPushButton#punctuationButton:pressed {
                background-color: #FFCCD8;
            }
        """)
        return self.punctuation_btn

    def _build_vu_meter(self) -> VUMeter:
        self.vu_meter = VUMeter()
        return self.vu_meter

    def _build_timer_label(self) -> QLabel:
        self.timer_label = QLabel("00:00")
        # Pill-shaped monospace badge — light pink tint, brand pink text
        self.timer_label.setStyleSheet("""
            QLabel {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                font-weight: bold;
                color: #FF6FA3;
                background-color: rgba(255, 111, 163, 0.10);
                border: 1px solid rgba(255, 111, 163, 0.25);
                border-radius: 8px;
                padding: 2px 10px;
                letter-spacing: 1px;
            }
        """)
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
