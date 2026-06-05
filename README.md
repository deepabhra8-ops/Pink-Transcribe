# Pink Transcribe

Pink Transcribe is a production-ready, offline-first desktop transcription application built in Python. It captures audio from any microphone connected to the system, transcribes speech locally using a background `faster-whisper` AI engine, and displays the transcript inside a beautiful, futuristic "cyberpunk" dark-themed PySide6 user interface.

---

## Key Features

- **Offline Inference**: Works 100% offline using local Whisper models (downloaded dynamically on first run).
- **Relational History Explorer**: Features a session list sidebar. Previous recordings, timestamps, and transcripts are persisted in a local SQLite database.
- **Neon VU Meter**: Visualizes active audio capture volume using a custom-painted segmented indicator.
- **Smart Formatting Editor**: Displays completed segments with precise timestamps next to text inside an interactive document editor.
- **Multi-Format Exports**: Export transcripts with a single click to plain text (`.txt`), metadata JSON (`.json`), or SubRip Subtitles (`.srt`).
- **Defensive Error Handling**: Catch and log hardware device errors (e.g. mic disconnects) or OOM instances (falls back from GPU to CPU model mode dynamically).
- **Crash Recovery**: Periodically checkpoints segments to SQLite, preventing loss of transcripts on power-loss or app crash.

---

## Technology Stack

- **Core**: Python 3.10+
- **UI Framework**: PySide6 (official Qt 6 Python bindings)
- **Audio Capture**: `sounddevice` + `numpy` (PortAudio C-bindings)
- **Transcription**: `faster-whisper` (CTranslate2 Whisper engine)
- **Database**: `sqlite3`
- **Testing**: `pytest`
- **Packaging**: `PyInstaller`

---

## File Structure

```
Pink Transcribe/
├── app/
│   ├── __init__.py
│   ├── main.py                    # App entry point, global exception hook, main loop
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # JSON-backed configuration schema
│   ├── audio/
│   │   ├── __init__.py
│   │   └── capture.py             # sounddevice interface, device discovery, resampling
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── engine.py              # local Whisper model loader and runner
│   │   └── worker.py              # Threaded transcription pipeline QThread coordinator
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLite session storage and recovery
│   │   └── exporter.py            # TXT, JSON, SRT format exporters
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py         # Main UI layout and controller
│   │   ├── styles.qss             # CSS-like styling sheet
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── vu_meter.py        # Custom painted audio level widget
│   │       ├── settings_dialog.py # Model / device settings window
│   │       └── text_editor.py     # Rich text editor with auto-scroll and timestamps
│   └── utils/
│       ├── __init__.py
│       └── logger.py              # Centralized logging configurations
├── tests/
│   ├── __init__.py
│   ├── test_audio.py              # Resampler and VU meter level unit tests
│   ├── test_config.py             # Configuration schema unit tests
│   └── test_storage.py            # SQLite transactions and exporter unit tests
├── requirements.txt               # Dependencies
├── build_exe.py                   # PyInstaller builder script
└── README.md                      # Documentation
```

---

## Setup & Running Instructions

### 1. Requirements & Prerequisites
Ensure you have Python 3.10+ installed on your system.

### 2. Set Up Virtual Environment & Dependencies
Open your terminal in the project directory and run:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Run Unit Tests
```bash
pytest
```

### 4. Launch the App
```bash
python -m app.main
```

### 5. Packaging into Standalone Executable
To bundle the application into a distribution folder for sharing (containing the `.exe` and required runtime dynamic libraries):
```bash
python build_exe.py
```
After completion, open `./dist/PinkTranscribe` and double-click `PinkTranscribe.exe`.

---

## System Design & Concurrency Details

### Concurrency
Pink Transcribe leverages a multithreaded architecture to ensure the PySide6 UI loop remains fully responsive (60 FPS) and lag-free, even during heavy machine learning workloads:
1. **Audio Callback Thread**: PortAudio handles audio device callbacks inside a high-priority C-thread, pushing raw 100ms chunks into a thread-safe Queue.
2. **Audio Processing Thread**: Reads from the raw Queue, computes RMS level for the VU Meter, and pushes frames to an audio buffer.
3. **Inference Worker QThread**: Runs the `faster-whisper` engine in a separate background thread context. Once recording is stopped, it transcribes the accumulated audio buffer in a single batch and emits the finalized text segments via Qt Signals.
4. **Main Thread**: Receives Qt Signals and displays the transcript segments with speaker labels and timestamps safely.

### Memory & Disk Optimization
To ensure the application can run efficiently:
- Efficient memory usage by releasing resources immediately after batch transcription is complete.
- Transcription segments are persisted to the SQLite database, guaranteeing permanent offline storage of transcription history.
