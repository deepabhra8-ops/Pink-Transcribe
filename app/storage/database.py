import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from app.utils.logger import logger

DB_DIR = os.path.expanduser("~/.pink_transcribe/db")
DB_FILE = os.path.join(DB_DIR, "sessions.db")

class DatabaseManager:
    """Manages SQLite database connections and operations for sessions and transcripts."""
    
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        os.makedirs(DB_DIR, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection to the database. Thread-safe when opened per request."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable Foreign Key support in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Initializes tables if they do not exist."""
        try:
            with self._get_connection() as conn:
                # Folders table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS folders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        created_at TEXT NOT NULL
                    )
                """)
                # Sessions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        model_size TEXT NOT NULL,
                        language TEXT NOT NULL,
                        audio_device TEXT,
                        duration_sec REAL DEFAULT 0.0,
                        folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL
                    )
                """)
                # Transcript segments table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS segments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        start_time REAL NOT NULL,
                        end_time REAL NOT NULL,
                        text TEXT NOT NULL,
                        finalized INTEGER DEFAULT 1,
                        confidence REAL,
                        speaker TEXT DEFAULT 'Speaker 1',
                        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                    )
                """)
                # Auto-migration: Check if edited_html exists, and if not, add it
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(sessions)")
                columns = [row[1] for row in cursor.fetchall()]
                if "edited_html" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN edited_html TEXT")
                    conn.commit()
                    logger.info("Migrated sessions table: added edited_html column.")
                
                if "edited_notes" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN edited_notes TEXT")
                    conn.commit()
                    logger.info("Migrated sessions table: added edited_notes column.")
                
                if "folder_id" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL")
                    conn.commit()
                    logger.info("Migrated sessions table: added folder_id column.")
                
                if "transcription_mode" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN transcription_mode TEXT DEFAULT 'Conversation'")
                    conn.commit()
                    logger.info("Migrated sessions table: added transcription_mode column.")
                
                # Check if speaker exists in segments table, and if not, add it
                cursor.execute("PRAGMA table_info(segments)")
                seg_columns = [row[1] for row in cursor.fetchall()]
                if "speaker" not in seg_columns:
                    conn.execute("ALTER TABLE segments ADD COLUMN speaker TEXT DEFAULT 'Speaker 1'")
                    conn.commit()
                    logger.info("Migrated segments table: added speaker column.")
                    
                conn.commit()
                logger.info("SQLite database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}", exc_info=True)

    def create_session(self, title: str, model_size: str, language: str, audio_device: Optional[str], folder_id: Optional[int] = None, transcription_mode: str = "Conversation") -> int:
        """Creates a new transcription session and returns its ID."""
        created_at = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions (title, created_at, model_size, language, audio_device, folder_id, transcription_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, created_at, model_size, language, audio_device, folder_id, transcription_mode))
                conn.commit()
                session_id = cursor.lastrowid
                logger.info(f"Created new session {session_id}: '{title}' (folder: {folder_id}, mode: {transcription_mode})")
                return session_id
        except Exception as e:
            logger.error(f"Failed to create session in DB: {e}", exc_info=True)
            raise

    def update_session_duration(self, session_id: int, duration_sec: float) -> None:
        """Updates the total audio duration for a session."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE sessions SET duration_sec = ? WHERE id = ?
                """, (duration_sec, session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update session {session_id} duration: {e}", exc_info=True)

    def update_session_title(self, session_id: int, title: str) -> None:
        """Updates the user-customizable session title."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE sessions SET title = ? WHERE id = ?
                """, (title, session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update session {session_id} title: {e}", exc_info=True)

    def update_session_html(self, session_id: int, html: str) -> None:
        """Saves the edited HTML (rich text) content of a session."""
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE sessions SET edited_html = ? WHERE id = ?", (html, session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update session {session_id} html: {e}", exc_info=True)

    def get_session_html(self, session_id: int) -> Optional[str]:
        """Retrieves the saved edited HTML of a session."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT edited_html FROM sessions WHERE id = ?", (session_id,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to fetch session {session_id} html: {e}", exc_info=True)
            return None

    def update_session_notes(self, session_id: int, notes: str) -> None:
        """Saves the manual notes of a session."""
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE sessions SET edited_notes = ? WHERE id = ?", (notes, session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update session {session_id} notes: {e}", exc_info=True)

    def get_session_notes(self, session_id: int) -> Optional[str]:
        """Retrieves the saved notes of a session."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT edited_notes FROM sessions WHERE id = ?", (session_id,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to fetch session {session_id} notes: {e}", exc_info=True)
            return None

    def add_segments(self, session_id: int, segments: List[Dict[str, Any]]) -> None:
        """Inserts multiple segments for a session. Designed for bulk updates."""
        if not segments:
            return
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Remove any existing unfinalized (partial) segments for this session
                # so that we do not write duplicates
                cursor.execute("DELETE FROM segments WHERE session_id = ? AND finalized = 0", (session_id,))
                
                # Bulk insert segments
                cursor.executemany("""
                    INSERT INTO segments (session_id, start_time, end_time, text, finalized, confidence, speaker)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    (
                        session_id,
                        s["start_time"],
                        s["end_time"],
                        s["text"],
                        s.get("finalized", 1),
                        s.get("confidence", None),
                        s.get("speaker", "Speaker 1")
                    )
                    for s in segments
                ])
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to add segments for session {session_id}: {e}", exc_info=True)

    def get_session_segments(self, session_id: int) -> List[Dict[str, Any]]:
        """Retrieves all segments for a given session, ordered by start time."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT start_time, end_time, text, finalized, confidence, speaker
                    FROM segments
                    WHERE session_id = ?
                    ORDER BY start_time ASC
                """, (session_id,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to fetch segments for session {session_id}: {e}", exc_info=True)
            return []

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Retrieves history of all sessions, ordered by date desc."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, created_at, model_size, language, audio_device, duration_sec, folder_id, transcription_mode
                    FROM sessions
                    ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to fetch sessions list: {e}", exc_info=True)
            return []

    def delete_session(self, session_id: int) -> None:
        """Deletes a session and its associated segments."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                conn.commit()
                logger.info(f"Deleted session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
            raise

    # ── Folder CRUD operations ──────────────────────────────────────────

    def create_folder(self, name: str) -> int:
        """Creates a new folder for sessions and returns its ID."""
        created_at = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO folders (name, created_at)
                    VALUES (?, ?)
                """, (name, created_at))
                conn.commit()
                folder_id = cursor.lastrowid
                logger.info(f"Created new folder {folder_id}: '{name}'")
                return folder_id
        except Exception as e:
            logger.error(f"Failed to create folder in DB: {e}", exc_info=True)
            raise

    def delete_folder(self, folder_id: int) -> None:
        """Deletes a folder. Link in sessions table will fallback to NULL."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
                conn.commit()
                logger.info(f"Deleted folder {folder_id}")
        except Exception as e:
            logger.error(f"Failed to delete folder {folder_id}: {e}", exc_info=True)
            raise

    def update_folder_name(self, folder_id: int, name: str) -> None:
        """Updates the folder name in the database."""
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE folders SET name = ? WHERE id = ?", (name, folder_id))
                conn.commit()
                logger.info(f"Updated folder {folder_id} name to '{name}'")
        except Exception as e:
            logger.error(f"Failed to update folder {folder_id} name: {e}", exc_info=True)
            raise

    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Retrieves list of all folders, ordered alphabetically by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, created_at FROM folders ORDER BY name ASC")
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to fetch folders list: {e}", exc_info=True)
            return []

    def move_session_to_folder(self, session_id: int, folder_id: Optional[int]) -> None:
        """Assigns a session to a folder, or removes it from all folders (if folder_id is None)."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE sessions SET folder_id = ? WHERE id = ?
                """, (folder_id, session_id))
                conn.commit()
                logger.info(f"Moved session {session_id} to folder {folder_id}")
        except Exception as e:
            logger.error(f"Failed to move session {session_id} to folder {folder_id}: {e}", exc_info=True)
            raise

    def update_session_mode(self, session_id: int, mode: str) -> None:
        """Updates the transcription mode (Conversation / Narration) for a session."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE sessions SET transcription_mode = ? WHERE id = ?
                """, (mode, session_id))
                conn.commit()
                logger.info(f"Updated session {session_id} transcription mode to '{mode}'")
        except Exception as e:
            logger.error(f"Failed to update session {session_id} transcription mode: {e}", exc_info=True)
            raise
