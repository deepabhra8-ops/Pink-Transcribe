"""Main Window — thin coordinator that wires UI panels to business logic.

Design principles applied
──────────────────────────
S – Single Responsibility : each panel owns its own UI; this class only coordinates.
O – Open / Closed         : new panels can be added without modifying existing ones.
I – Interface Segregation : panels expose narrow signal/method contracts, not full state.
D – Dependency Inversion  : panels depend on Qt abstractions (Signal); this class depends
                            on panel interfaces, not their internals.

Cohesion  : every method here is about coordinating the whole app, nothing else.
Coupling  : panels are wired together through signals—no panel has a direct reference to
            another panel or to this window.
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QDialog, QInputDialog,
)
from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QIcon

from app.config.settings import AppSettings
from app.audio.capture import AudioRecorder
from app.transcription.engine import TranscriptionEngine
from app.transcription.worker import TranscriptionWorker
from app.storage.database import DatabaseManager
from app.storage.exporter import TranscriptExporter
from app.utils.logger import logger

# UI panels & components
from app.ui.components.text_editor import TranscriptionEditor
from app.ui.components.settings_dialog import SettingsDialog
from app.ui.components.export_dialog import ExportDialog
from app.ui.components.sidebar_panel import SidebarPanel
from app.ui.components.top_toolbar import TopToolbar
from app.ui.components.action_bar import ActionBar
from app.ui.components.details_panel import DetailsPanel


class MainWindow(QMainWindow):
    """Top-level application window.  Owns no business logic itself — only wires panels."""

    def __init__(self):
        super().__init__()

        # ── Core services (injected, not created inline in methods) ──
        self.settings             = AppSettings.load()
        self.db                   = DatabaseManager()
        self.audio_recorder       = AudioRecorder()
        self.transcription_engine = TranscriptionEngine()
        self.audio_recorder.set_error_callback(self._on_audio_error)

        # ── Session state ─────────────────────────────────────────────
        self.current_session_id: Optional[int]      = None
        self.active_segments:    List[Dict[str, Any]] = []
        self.session_duration:   float               = 0.0
        self.worker:             Optional[TranscriptionWorker] = None
        self.running_workers:    set                 = set()

        # Track which panel visibility changes were automatic (not user-driven)
        self._auto_collapsed_sidebar    = False
        self._auto_hidden_right_panel   = False

        # ── Window chrome ─────────────────────────────────────────────
        self.setWindowTitle("Pink Transcribe")
        self.resize(1580, 860)
        self.setMinimumSize(600, 500)
        self._load_icon()
        self._load_stylesheet()

        # ── Build & wire ──────────────────────────────────────────────
        self._build_ui()
        self._connect_signals()

        # ── Timers ────────────────────────────────────────────────────
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._tick_session_timer)
        self._vu_timer = QTimer(self)
        self._vu_timer.timeout.connect(self._tick_vu_meter)

        # ── Initial state ─────────────────────────────────────────────
        self._refresh_sessions()
        self.statusBar().showMessage("Ready")

    # ═══════════════════════════════════════════════════════════════════
    # UI assembly  (each panel is its own concern)
    # ═══════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar       = SidebarPanel()
        self.details_panel = DetailsPanel()

        root.addWidget(self.sidebar)
        root.addWidget(self._build_workspace(), stretch=1)
        root.addWidget(self.details_panel)

    def _build_workspace(self) -> QWidget:
        """Centre column: top toolbar → transcript editor → floating action bar."""
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(16, 14, 16, 10)
        layout.setSpacing(8)

        self.toolbar    = TopToolbar()
        self.editor     = TranscriptionEditor()
        self.action_bar = ActionBar()

        self.editor.setReadOnly(False)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.editor)
        layout.addWidget(self.action_bar)
        return workspace

    def _connect_signals(self) -> None:
        """Single place that wires every panel signal to its handler.  No logic here."""

        # Sidebar → session management
        self.sidebar.new_session_requested.connect(self._create_new_session)
        self.sidebar.session_selected.connect(self._load_session)
        self.sidebar.delete_selected_requested.connect(self._delete_selected_session)
        self.sidebar.delete_all_requested.connect(self._delete_all_sessions)
        self.sidebar.create_folder_requested.connect(self._create_new_folder)
        self.sidebar.folder_deleted.connect(self._delete_folder)
        self.sidebar.session_moved.connect(self._move_session)
        self.sidebar.rename_folder_requested.connect(self._rename_folder)
        self.sidebar.rename_session_requested.connect(self._rename_session)
        self.sidebar.connect_search(self._refresh_sessions)

        # Top toolbar → UI / export
        self.toolbar.title_edited.connect(self._on_title_edited)
        self.toolbar.export_requested.connect(self._handle_export)
        self.toolbar.settings_requested.connect(self._open_settings)

        # Action bar → recording controls
        self.action_bar.record_toggled.connect(self._toggle_recording)
        self.action_bar.stop_requested.connect(self._stop_recording)

        # Editor → data / navigation
        self.editor.text_changed.connect(self._autosave_html)
        self.editor.seek_requested.connect(self._on_seek)
        self.editor.speaker_clicked.connect(self._on_speaker_clicked)
        self.editor.split_segment_requested.connect(self._on_split_segment)
        self.editor.tag_applied.connect(self._on_tag_applied)
        self.editor.text_edit.timestamp_shortcut_pressed.connect(self._insert_timestamp)
        self.editor.text_edit.speaker_shortcut_pressed.connect(self._on_speaker_shortcut)

        # Details panel → autosave / toggle
        self.details_panel.notes_changed.connect(self._autosave_notes)
        self.details_panel.collapsed_toggled.connect(self._on_right_panel_collapsed_toggled)

    # ═══════════════════════════════════════════════════════════════════
    # Window lifecycle
    # ═══════════════════════════════════════════════════════════════════

    def _load_icon(self) -> None:
        path = os.path.join(os.path.dirname(__file__), "app_icon.jpg")
        if os.path.exists(path):
            self.setWindowIcon(QIcon(path))

    def _load_stylesheet(self) -> None:
        path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout(event.size().width())

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Quit Application?",
                "Recording is active. Exiting will terminate the session. Proceed?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._stop_recording()
                self.worker.wait(3000)
                self.transcription_engine.unload_model()
                event.accept()
            else:
                event.ignore()
        else:
            self.transcription_engine.unload_model()
            event.accept()

    # ═══════════════════════════════════════════════════════════════════
    # Responsive layout  (width breakpoints)
    # ═══════════════════════════════════════════════════════════════════

    def _apply_responsive_layout(self, width: int) -> None:
        """Adapt panel visibility and button text to the current window width."""
        narrow, very_narrow = width < 900, width < 750

        # Sidebar: auto-collapse below 950 px
        if width < 950 and not self.sidebar.is_collapsed:
            self.sidebar.collapse()
            self._auto_collapsed_sidebar = True
        elif width >= 950 and self.sidebar.is_collapsed and self._auto_collapsed_sidebar:
            self.sidebar.expand()
            self._auto_collapsed_sidebar = False

        # Right panel: auto-collapse below 800 px
        if width < 800 and not self.details_panel.is_collapsed:
            self.details_panel.collapse()
            self._auto_hidden_right_panel = True
        elif width >= 800 and self.details_panel.is_collapsed and self._auto_hidden_right_panel:
            self.details_panel.expand()
            self._auto_hidden_right_panel = False

        # Compact toolbar & action bar text
        self.toolbar.apply_compact(narrow, very_narrow)
        self.action_bar.apply_compact(very_narrow)

        # Compact badge text
        lang = self.settings.language.upper() if self.settings.language != "auto" else "Auto"
        self.toolbar.set_compact_badges(
            model=self.settings.model_size,
            lang=lang,
            narrow=narrow,
        )

    def _on_right_panel_collapsed_toggled(self, collapsed: bool) -> None:
        if not collapsed:
            self._auto_hidden_right_panel = False

    # ═══════════════════════════════════════════════════════════════════
    # Session management
    # ═══════════════════════════════════════════════════════════════════

    def _refresh_sessions(self) -> None:
        """Reload all folders and sessions from the database and repopulate the sidebar."""
        try:
            folders = self.db.get_all_folders()
            sessions = self.db.get_all_sessions()
            self.sidebar.populate(folders, sessions)
        except Exception as e:
            logger.error(f"Failed to refresh sessions: {e}")

    def _create_new_folder(self) -> None:
        """Prompt user for a folder name and create it in the database."""
        name, ok = QInputDialog.getText(
            self, "New Folder", "Enter folder name:",
            text=""
        )
        if ok and name.strip():
            name = name.strip()
            try:
                self.db.create_folder(name)
                self._refresh_sessions()
            except Exception as e:
                QMessageBox.warning(self, "Folder Error", f"Could not create folder:\n{e}")

    def _delete_folder(self, folder_id: int) -> None:
        """Prompt confirmation and delete the folder, moving sessions to ungrouped."""
        sessions = self.db.get_all_sessions()
        folder_sessions = [s for s in sessions if s["folder_id"] == folder_id]
        
        if folder_sessions:
            reply = QMessageBox.question(
                self, "Delete Folder?",
                f"This folder contains {len(folder_sessions)} session(s).\n"
                "Are you sure you want to delete this folder?\n"
                "The sessions will be kept and moved to the root level (Ungrouped).",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        else:
            reply = QMessageBox.question(
                self, "Delete Folder?",
                "Are you sure you want to delete this empty folder?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        try:
            self.db.delete_folder(folder_id)
            self._refresh_sessions()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not delete folder:\n{e}")

    def _move_session(self, session_id: int, folder_id: Optional[int]) -> None:
        """Move a session to a folder, then refresh the sidebar."""
        try:
            self.db.move_session_to_folder(session_id, folder_id)
            self._refresh_sessions()
            self.sidebar.select_by_id(session_id)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not move session:\n{e}")

    def _rename_folder(self, folder_id: int) -> None:
        """Rename a folder in the database and refresh the sidebar."""
        folders = self.db.get_all_folders()
        folder = next((f for f in folders if f["id"] == folder_id), None)
        if not folder:
            return
            
        name, ok = QInputDialog.getText(
            self, "Rename Folder", "Enter new folder name:",
            text=folder["name"]
        )
        if ok and name.strip() and name.strip() != folder["name"]:
            try:
                self.db.update_folder_name(folder_id, name.strip())
                self._refresh_sessions()
            except Exception as e:
                QMessageBox.warning(self, "Folder Error", f"Could not rename folder:\n{e}")

    def _rename_session(self, session_id: int) -> None:
        """Rename a session in the database and refresh the sidebar."""
        sessions = self.db.get_all_sessions()
        sess = next((s for s in sessions if s["id"] == session_id), None)
        if not sess:
            return
            
        name, ok = QInputDialog.getText(
            self, "Rename Session", "Enter new session title:",
            text=sess["title"]
        )
        if ok and name.strip() and name.strip() != sess["title"]:
            try:
                self.db.update_session_title(session_id, name.strip())
                if session_id == self.current_session_id:
                    date_str = datetime.fromisoformat(sess["created_at"]).strftime("%B %d, %Y • %I:%M %p")
                    self.toolbar.set_session_info(name.strip(), date_str)
                self._refresh_sessions()
                self.sidebar.select_by_id(session_id)
            except Exception as e:
                QMessageBox.warning(self, "Session Error", f"Could not rename session:\n{e}")

    def _create_new_session(self) -> None:
        if self.worker and self.worker.isRunning():
            self._stop_recording()
        title = f"Session {datetime.now().strftime('%m-%d %H:%M')}"
        try:
            self.current_session_id = self.db.create_session(
                title=title,
                model_size=self.settings.model_size,
                language=self.settings.language,
                audio_device=self.settings.audio_device,
            )
            self.active_segments  = []
            self.session_duration = 0.0
            self.toolbar.set_session_info(title, datetime.now().strftime("%B %d, %Y • %I:%M %p"))
            self.action_bar.set_timer("00:00")
            self.editor.clear_editor()
            self._refresh_sessions()
            self.sidebar.select_by_id(self.current_session_id)
            self._sync_details_panel()
            logger.info(f"Created new session {self.current_session_id}.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not create session:\n{e}")

    def _load_session(self, session_id: int) -> None:
        """Load and display a session from history."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Stop Recording?",
                "Viewing history will stop active recording. Proceed?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._stop_recording()
            else:
                self.sidebar.select_by_id(self.current_session_id)
                return

        try:
            sessions = self.db.get_all_sessions()
            sess = next((s for s in sessions if s["id"] == session_id), None)
            if not sess:
                return

            self.current_session_id = session_id
            self.session_duration   = sess["duration_sec"]

            date_str = datetime.fromisoformat(sess["created_at"]).strftime("%B %d, %Y • %I:%M %p")
            self.toolbar.set_session_info(sess["title"], date_str)
            self.toolbar.model_badge.setText(f"Model: {sess['model_size']}")
            self.toolbar.lang_badge.setText(f"Lang: {sess['language'].upper()}")
            self.action_bar.set_timer(self._fmt_duration(self.session_duration))

            self.active_segments = self.db.get_session_segments(session_id)
            html = self.db.get_session_html(session_id)
            if html:
                self.editor.setHtml(html)
            else:
                self.editor.update_segments(self.active_segments)
            self.editor.update_partial("")
            self._sync_details_panel()
            logger.info(f"Loaded session {session_id}.")
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
            QMessageBox.warning(self, "Load Failed", f"Unable to retrieve session data:\n{e}")

    def _delete_selected_session(self) -> None:
        session_id = self.sidebar.current_session_id()
        if session_id is None:
            return
        if self.worker and self.worker.isRunning() and self.current_session_id == session_id:
            QMessageBox.warning(self, "Action Denied", "Cannot delete the session currently recording.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Permanently delete this session and all its transcripts?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_session(session_id)
                self._refresh_sessions()
                if self.current_session_id == session_id:
                    self._reset_workspace()
            except Exception as e:
                QMessageBox.critical(self, "Delete Failed", str(e))

    def _delete_all_sessions(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Action Denied", "Cannot delete sessions while recording.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete All",
            "Permanently delete ALL sessions? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                for s in self.db.get_all_sessions():
                    self.db.delete_session(s["id"])
                self._reset_workspace()
                self._refresh_sessions()
                logger.info("Deleted all sessions.")
            except Exception as e:
                QMessageBox.critical(self, "Delete All Failed", str(e))

    def _reset_workspace(self) -> None:
        """Return the UI to its blank 'no session' state."""
        self.current_session_id = None
        self.active_segments    = []
        self.session_duration   = 0.0
        self.toolbar.set_session_info("Select or Create Session", "")
        self.action_bar.set_timer("00:00")
        self.editor.clear_editor()
        self.details_panel.clear()

    # ═══════════════════════════════════════════════════════════════════
    # Recording
    # ═══════════════════════════════════════════════════════════════════

    def _toggle_recording(self) -> None:
        if self.worker and self.worker.isRunning():
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if self.current_session_id is None:
            self._create_new_session()

        self.statusBar().showMessage("Initializing Audio...")
        rec_device, comp_type = self.settings.device, self.settings.compute_type

        # GPU availability check
        det_device, _ = TranscriptionEngine.detect_hardware()
        if self.settings.device == "cuda" and det_device == "cpu":
            QMessageBox.warning(self, "GPU Fallback",
                "CUDA GPU not available. Falling back to CPU mode.")
            rec_device, comp_type = "cpu", "int8"

        if not self.audio_recorder.start(self.settings.audio_device):
            self.statusBar().showMessage("Audio Device Error")
            QMessageBox.critical(self, "Recording Failed",
                "Unable to open microphone. Verify connection and permissions.")
            return

        self.worker = TranscriptionWorker(
            engine=self.transcription_engine,
            audio_queue=self.audio_recorder.output_queue,
            model_size=self.settings.model_size,
            device=rec_device,
            compute_type=comp_type,
            language=self.settings.language,
            vad_threshold=self.settings.vad_threshold,
            auto_detect_speakers=self.toolbar.auto_detect_speakers,
        )
        self.running_workers.add(self.worker)

        # Worker → coordinator (narrow signal surface)
        self.worker.status_changed.connect(self.statusBar().showMessage)
        self.worker.partial_transcript.connect(self.editor.update_partial)
        self.worker.segment_finalized.connect(self._on_segment_finalized)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

        self._session_timer.start(1000)
        self._vu_timer.start(50)
        self.action_bar.set_recording(True)
        logger.info("Recording started.")

    def _stop_recording(self) -> None:
        if not self.worker or not self.worker.isRunning():
            return
        self.statusBar().showMessage("Stopping / flushing buffers…")
        self.audio_recorder.stop()
        self.worker.stop()
        self._session_timer.stop()
        self._vu_timer.stop()
        self.action_bar.set_vu_level(0.0)
        if self.current_session_id:
            self.db.update_session_duration(self.current_session_id, self.session_duration)
        self.action_bar.set_recording(False)
        self._refresh_sessions()
        self.sidebar.select_by_id(self.current_session_id)
        logger.info("Recording stopped.")

    # ── Worker callbacks ──────────────────────────────────────────────

    @Slot(dict)
    def _on_segment_finalized(self, segment: Dict[str, Any]) -> None:
        if (self.active_segments
                and self.active_segments[-1]["start_time"] == segment["start_time"]):
            self.active_segments[-1] = segment
        else:
            self.active_segments.append(segment)
        if self.current_session_id:
            try:
                self.db.add_segments(self.current_session_id, [segment])
            except Exception as e:
                logger.error(f"Autosave segment failed: {e}")
        self.editor.update_segments(self.active_segments)
        self._sync_details_panel()

    @Slot(str)
    def _on_worker_error(self, msg: str) -> None:
        QMessageBox.critical(self, "ASR Engine Failure", msg)
        self._stop_recording()

    @Slot()
    def _on_worker_finished(self) -> None:
        self.statusBar().showMessage("Ready")
        sender = self.sender()
        if sender:
            QTimer.singleShot(500, lambda: self._cleanup_worker(sender))
        if self.worker is sender:
            self.worker = None

    def _cleanup_worker(self, worker) -> None:
        try:
            self.running_workers.discard(worker)
            worker.deleteLater()
            logger.info("Worker cleaned up.")
        except Exception as e:
            logger.error(f"Worker cleanup error: {e}")

    @Slot(str)
    def _on_audio_error(self, msg: str) -> None:
        logger.error(f"Audio device error: {msg}")
        self._on_worker_error("Microphone hardware error. Input stream disconnected.")

    # ═══════════════════════════════════════════════════════════════════
    # Timers
    # ═══════════════════════════════════════════════════════════════════

    def _tick_session_timer(self) -> None:
        self.session_duration += 1.0
        self.action_bar.set_timer(self._fmt_duration(self.session_duration))

    def _tick_vu_meter(self) -> None:
        self.action_bar.set_vu_level(self.audio_recorder.get_vu_level())

    # ═══════════════════════════════════════════════════════════════════
    # Editor actions
    # ═══════════════════════════════════════════════════════════════════

    def _autosave_html(self) -> None:
        if self.current_session_id and not (self.worker and self.worker.isRunning()):
            self.db.update_session_html(self.current_session_id, self.editor.toHtml())

    def _autosave_notes(self, text: str) -> None:
        if self.current_session_id:
            self.db.update_session_notes(self.current_session_id, text)

    @Slot(str)
    def _on_title_edited(self, new_title: str) -> None:
        if new_title and self.current_session_id:
            try:
                self.db.update_session_title(self.current_session_id, new_title)
                self._refresh_sessions()
                self.sidebar.select_by_id(self.current_session_id)
            except Exception as e:
                logger.error(f"Title update failed: {e}")

    @Slot(float)
    def _on_seek(self, seconds: float) -> None:
        self.statusBar().showMessage(f"Seek: {seconds:.1f}s")

    @Slot(str)
    def _on_speaker_clicked(self, speaker: str) -> None:
        new_name, ok = QInputDialog.getText(
            self, "Rename Speaker", f"Rename '{speaker}' globally to:"
        )
        if ok and new_name.strip():
            new_name = new_name.strip()
            for seg in self.active_segments:
                if seg.get("speaker") == speaker:
                    seg["speaker"] = new_name
            if self.current_session_id:
                self.db.add_segments(self.current_session_id, self.active_segments)
            self.editor.update_segments(self.active_segments)
            self._sync_details_panel()
            self.statusBar().showMessage(f"Renamed '{speaker}' → '{new_name}'")

    def _on_speaker_shortcut(self) -> None:
        idx = self.editor.text_edit.textCursor().blockNumber()
        if 0 <= idx < len(self.active_segments):
            self._on_speaker_clicked(
                self.active_segments[idx].get("speaker", "Speaker 1")
            )

    @Slot(int, int)
    def _on_split_segment(self, block_idx: int, char_idx: int) -> None:
        if not self.current_session_id or block_idx >= len(self.active_segments):
            return
        seg   = self.active_segments[block_idx]
        text  = seg["text"]
        ratio = char_idx / len(text) if text else 0.5
        split_t = seg["start_time"] + ratio * (seg["end_time"] - seg["start_time"])

        new_seg = {
            "start_time": split_t,
            "end_time":   seg["end_time"],
            "text":       text[char_idx:].strip(),
            "confidence": seg.get("confidence", 1.0),
            "speaker":    seg.get("speaker", "Speaker 1"),
            "tag":        seg.get("tag"),
        }
        seg["end_time"] = split_t
        seg["text"]     = text[:char_idx].strip()
        self.active_segments.insert(block_idx + 1, new_seg)
        self.db.add_segments(self.current_session_id, self.active_segments)
        self.editor.update_segments(self.active_segments)
        self._sync_details_panel()

    @Slot(str, str)
    def _on_tag_applied(self, tag_name: str, _text: str) -> None:
        if self.current_session_id:
            self.db.add_segments(self.current_session_id, self.active_segments)
        self._sync_details_panel()
        self.statusBar().showMessage(f"Tagged as '{tag_name}'")

    def _insert_timestamp(self) -> None:
        mins = int(self.session_duration // 60)
        secs = int(self.session_duration % 60)
        self.editor.text_edit.textCursor().insertText(f" [{mins:02d}:{secs:02d}] ")

    def _mark_key_point(self) -> None:
        idx = self.editor.text_edit.textCursor().blockNumber()
        if 0 <= idx < len(self.active_segments):
            self.active_segments[idx]["tag"] = "Action Item"
            if self.current_session_id:
                self.db.add_segments(self.current_session_id, self.active_segments)
            self.editor.update_segments(self.active_segments)
            self._sync_details_panel()
            self.statusBar().showMessage("Flagged as Action Item Key Point.")

    # ═══════════════════════════════════════════════════════════════════
    # Dialogs
    # ═══════════════════════════════════════════════════════════════════

    def _open_settings(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Device Locked",
                "Settings cannot be modified during recording.")
            return
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.Accepted:
            self.settings = AppSettings.load()
            self.toolbar.set_badges(
                self.settings.model_size,
                self.settings.device,
                self.settings.language,
            )

    def _handle_export(self) -> None:
        if not self.active_segments:
            QMessageBox.warning(self, "Nothing to Export",
                "No transcription segments are available.")
            return

        speakers = list({
            seg.get("speaker", "Speaker 1")
            for seg in self.active_segments if seg.get("text")
        })
        dialog = ExportDialog(speakers, self)
        if dialog.exec() != QDialog.Accepted:
            return

        fmt     = dialog.chosen_format
        inc_spk = dialog.inc_speakers_cb.isChecked()
        inc_ts  = dialog.inc_timestamps_cb.isChecked()
        mapping = dialog.speaker_mapping

        ext_filter = {
            "txt":  "Plain Text (*.txt)",
            "srt":  "SubRip Subtitle (*.srt)",
            "vtt":  "WebVTT Subtitle (*.vtt)",
            "html": "MS Word HTML (*.html)",
        }.get(fmt, "All Files (*)")

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Transcript",
            f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}",
            ext_filter,
        )
        if not path:
            return

        try:
            self.statusBar().showMessage("Generating export file…")
            if fmt == "txt":
                content = TranscriptExporter.to_txt(self.active_segments, inc_spk, inc_ts, mapping)
            elif fmt == "srt":
                content = TranscriptExporter.to_srt(self.active_segments, inc_spk, mapping)
            elif fmt == "vtt":
                content = TranscriptExporter.to_vtt(self.active_segments, inc_spk, mapping)
            else:
                content = TranscriptExporter.to_docx_html(self.active_segments, mapping)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            self.statusBar().showMessage(f"Exported → {os.path.basename(path)}")
            QMessageBox.information(self, "Export Successful", f"Saved to:\n{path}")
        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Export Failed", str(e))

    # ═══════════════════════════════════════════════════════════════════
    # Details panel synchronisation
    # ═══════════════════════════════════════════════════════════════════

    def _sync_details_panel(self) -> None:
        """Push current session state into the right details panel."""
        if not self.current_session_id:
            self.details_panel.clear()
            return

        speakers = {
            seg.get("speaker", "Speaker 1")
            for seg in self.active_segments if seg.get("text")
        }
        self.details_panel.update_speakers(speakers)

        try:
            sessions = self.db.get_all_sessions()
            sess = next((s for s in sessions if s["id"] == self.current_session_id), None)
            if sess:
                self.details_panel.update_metadata(sess)
                self.toolbar.title_input.setText(sess["title"])
                notes = self.db.get_session_notes(self.current_session_id)
                self.details_panel.set_notes(notes)
        except Exception as e:
            logger.error(f"Details panel sync error: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        secs = int(seconds)
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
