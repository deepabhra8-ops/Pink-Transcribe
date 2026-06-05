from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QComboBox, QSlider, QCheckBox, QSpinBox, 
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from app.config.settings import AppSettings
from app.audio.capture import AudioRecorder
from app.transcription.engine import TranscriptionEngine

class SettingsDialog(QDialog):
    """Configuration dialog for app preferences and model options."""
    
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        
        self.setWindowTitle("Pink Transcribe Settings")
        self.setModal(True)
        self.resize(420, 360)
        self.setStyleSheet("background-color: #fff0f3; color: #2b2d42;")
        
        # Build UI layout
        self._init_ui()
        self._load_current_settings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("SYSTEM CONFIGURATION")
        title_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ff4a7d; letter-spacing: 2px;"
        )
        layout.addWidget(title_label)
        
        # Form Layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        # 1. Microphone Selection
        self.mic_combo = QComboBox()
        devices, default_mic = AudioRecorder.list_devices()
        self.mic_combo.addItems(devices)
        if default_mic:
            self.mic_combo.addItem(f"Default ({default_mic})", "")
        else:
            self.mic_combo.addItem("Default Device", "")
            
        form_layout.addRow("Microphone:", self.mic_combo)
        
        # 2. Model Selection
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        form_layout.addRow("Whisper Model:", self.model_combo)
        
        # 3. Hardware Acceleration
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda"])
        
        # Check CUDA availability to give hints
        rec_dev, _ = TranscriptionEngine.detect_hardware()
        self.gpu_label = QLabel()
        if rec_dev == "cuda":
            self.gpu_label.setText("GPU Acceleration Available")
            self.gpu_label.setStyleSheet("color: #2a9d8f; font-size: 10px; font-weight: bold;")
        else:
            self.gpu_label.setText("No CUDA GPU detected (CPU mode forced)")
            self.gpu_label.setStyleSheet("color: #e76f51; font-size: 10px; font-weight: bold;")
            
        device_layout = QVBoxLayout()
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.gpu_label)
        form_layout.addRow("Inference Device:", device_layout)
        
        # 4. Model Quantization
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "float16", "float32"])
        form_layout.addRow("Compute Precision:", self.compute_combo)
        
        # 5. Language Selection
        self.lang_combo = QComboBox()
        languages = [
            ("Auto Detect", "auto"),
            ("English", "en"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de"),
            ("Italian", "it"),
            ("Chinese", "zh"),
            ("Japanese", "ja"),
            ("Korean", "ko"),
            ("Portuguese", "pt"),
            ("Russian", "ru")
        ]
        for name, code in languages:
            self.lang_combo.addItem(name, code)
        form_layout.addRow("Language:", self.lang_combo)
        
        # 6. VAD Threshold
        self.vad_slider = QSlider(Qt.Horizontal)
        self.vad_slider.setRange(10, 90)
        self.vad_slider.setSingleStep(5)
        self.vad_label = QLabel("0.50")
        self.vad_label.setFixedWidth(30)
        self.vad_slider.valueChanged.connect(lambda v: self.vad_label.setText(f"{v/100:.2f}"))
        
        vad_layout = QHBoxLayout()
        vad_layout.addWidget(self.vad_slider)
        vad_layout.addWidget(self.vad_label)
        form_layout.addRow("VAD Sensitivity:", vad_layout)

        # 7. Autosave Interval
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(5, 120)
        self.autosave_spin.setSuffix(" sec")
        form_layout.addRow("Autosave Interval:", self.autosave_spin)

        # 8. Save Audio Checkbox
        self.save_audio_cb = QCheckBox("Save raw WAV audio")
        form_layout.addRow("Audio Storage:", self.save_audio_cb)
        
        layout.addLayout(form_layout)
        
        # Style all ComboBoxes and Inputs
        self.setStyleSheet("""
            QDialog {
                background-color: #fff0f3;
                border: 1px solid #ffe5ec;
            }
            QLabel {
                font-family: 'Inter', 'Segoe UI', Arial;
                font-size: 12px;
                color: #2b2d42;
            }
            QComboBox, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #ffe5ec;
                border-radius: 4px;
                padding: 4px 8px;
                color: #2b2d42;
                font-family: 'Inter', 'Segoe UI', Arial;
                min-width: 150px;
            }
            QComboBox:hover, QSpinBox:hover {
                border: 1px solid #ff477e;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #ffe5ec;
                selection-background-color: #ff477e;
                selection-color: #ffffff;
                color: #2b2d42;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #ffccd5;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ff477e;
                width: 14px;
                height: 14px;
                margin-top: -5px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff0055;
            }
            QCheckBox {
                color: #2b2d42;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #ffffff;
                border: 1px solid #ffe5ec;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff477e;
                border-color: #ff477e;
            }
        """)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #ffe5ec;
                color: #8d99ae;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ffe5ec;
                color: #2b2d42;
            }
        """)
        
        self.save_btn = QPushButton("SAVE CHANGES")
        self.save_btn.clicked.connect(self._save_settings)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff477e;
                border: none;
                color: #ffffff;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ff0055;
            }
            QPushButton:pressed {
                background-color: #c9184a;
            }
        """)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)

    def _load_current_settings(self) -> None:
        """Populates UI controls with the current configuration values."""
        # Mic Device
        if self.settings.audio_device:
            idx = self.mic_combo.findText(self.settings.audio_device)
            if idx >= 0:
                self.mic_combo.setCurrentIndex(idx)
        else:
            # Fallback to default
            self.mic_combo.setCurrentIndex(self.mic_combo.count() - 1)
            
        # Model
        idx = self.model_combo.findText(self.settings.model_size)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
            
        # Device
        idx = self.device_combo.findText(self.settings.device)
        if idx >= 0:
            self.device_combo.setCurrentIndex(idx)
            
        # Compute Type
        idx = self.compute_combo.findText(self.settings.compute_type)
        if idx >= 0:
            self.compute_combo.setCurrentIndex(idx)
            
        # Language
        lang_idx = -1
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == self.settings.language:
                lang_idx = i
                break
        if lang_idx >= 0:
            self.lang_combo.setCurrentIndex(lang_idx)
            
        # VAD Slider
        self.vad_slider.setValue(int(self.settings.vad_threshold * 100))
        self.vad_label.setText(f"{self.settings.vad_threshold:.2f}")
        
        # Spinbox
        self.autosave_spin.setValue(self.settings.autosave_interval_sec)
        
        # Audio WAV Checkbox
        self.save_audio_cb.setChecked(self.settings.save_audio_enabled)

    def _save_settings(self) -> None:
        """Reads user inputs and writes them to settings persistence."""
        # Extract mic
        current_mic_text = self.mic_combo.currentText()
        if "Default" in current_mic_text:
            self.settings.audio_device = None
        else:
            self.settings.audio_device = current_mic_text
            
        # Extract model and hardware parameters
        self.settings.model_size = self.model_combo.currentText()
        self.settings.device = self.device_combo.currentText()
        self.settings.compute_type = self.compute_combo.currentText()
        
        # Extract language
        self.settings.language = self.lang_combo.currentData()
        
        # VAD & options
        self.settings.vad_threshold = self.vad_slider.value() / 100.0
        self.settings.autosave_interval_sec = self.autosave_spin.value()
        self.settings.save_audio_enabled = self.save_audio_cb.isChecked()
        
        # Save to disk
        self.settings.save()
        
        # Notify user if they switched model sizes or computation engines
        # since it will take effect on the next session
        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings saved successfully!\nModel and hardware configuration changes will apply on the next recording session.",
            QMessageBox.Ok
        )
        self.accept()
