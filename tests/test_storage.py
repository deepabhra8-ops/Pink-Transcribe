import os
import tempfile
import pytest
from app.storage.database import DatabaseManager
from app.storage.exporter import TranscriptExporter

@pytest.fixture
def temp_db():
    """Fixture creating an in-memory or temp-file DatabaseManager for tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(db_path=path)
    yield db
    try:
        os.remove(path)
    except OSError:
        pass

def test_database_session_creation(temp_db):
    """Test creating sessions and retrieval."""
    sess_id = temp_db.create_session(
        title="Test Recording",
        model_size="base",
        language="en",
        audio_device="Mic Test"
    )
    assert sess_id == 1
    
    sessions = temp_db.get_all_sessions()
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Test Recording"
    assert sessions[0]["model_size"] == "base"
    assert sessions[0]["language"] == "en"

def test_database_segments_cascade(temp_db):
    """Test adding segments and cascading deletion on session removal."""
    sess_id = temp_db.create_session(
        title="Cascade Session",
        model_size="tiny",
        language="auto",
        audio_device=None
    )
    
    segments = [
        {"start_time": 0.0, "end_time": 2.5, "text": "Hello world", "finalized": 1},
        {"start_time": 2.5, "end_time": 5.0, "text": "This is a test", "finalized": 1}
    ]
    temp_db.add_segments(sess_id, segments)
    
    loaded_segs = temp_db.get_session_segments(sess_id)
    assert len(loaded_segs) == 2
    assert loaded_segs[0]["text"] == "Hello world"
    
    # Delete session
    temp_db.delete_session(sess_id)
    
    # Verify segments table is empty for this session
    assert len(temp_db.get_session_segments(sess_id)) == 0
    assert len(temp_db.get_all_sessions()) == 0

def test_exporter_formats():
    """Test exporting formatting outputs."""
    segments = [
        {"start_time": 1.25, "end_time": 3.75, "text": "First segment.", "confidence": -0.1},
        {"start_time": 4.10, "end_time": 6.80, "text": "Second segment.", "confidence": -0.2}
    ]
    
    # 1. TXT export
    txt = TranscriptExporter.to_txt(segments)
    assert txt == "First segment. Second segment."
    
    # 2. SRT timestamp checks
    time_str = TranscriptExporter.format_srt_timestamp(1.25)
    assert time_str == "00:00:01,250"
    
    time_str_hour = TranscriptExporter.format_srt_timestamp(3725.68)
    # 3725.68s = 1 hour, 2 minutes, 5 seconds, 680ms
    assert time_str_hour == "01:02:05,680"
    
    # 3. SRT export layout check
    srt = TranscriptExporter.to_srt(segments)
    assert "1" in srt
    assert "00:00:01,250 --> 00:00:03,750" in srt
    assert "First segment." in srt
    assert "00:00:04,100 --> 00:00:06,800" in srt
    assert "Second segment." in srt
