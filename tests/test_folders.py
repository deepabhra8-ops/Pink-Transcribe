import os
import tempfile
import pytest
from app.storage.database import DatabaseManager

@pytest.fixture
def temp_db():
    """Fixture creating a temporary DatabaseManager for testing folder structures."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(db_path=path)
    yield db
    try:
        os.remove(path)
    except OSError:
        pass

def test_folder_creation_and_listing(temp_db):
    """Test folder insertion and alphabetical listing."""
    fid1 = temp_db.create_folder("Work")
    fid2 = temp_db.create_folder("Personal")
    
    assert fid1 == 1
    assert fid2 == 2
    
    folders = temp_db.get_all_folders()
    assert len(folders) == 2
    # Alphabetically sorted: "Personal" then "Work"
    assert folders[0]["name"] == "Personal"
    assert folders[1]["name"] == "Work"

def test_session_moving_between_folders(temp_db):
    """Test linking sessions to folders and moving them."""
    fid = temp_db.create_folder("Work Meetings")
    
    sid = temp_db.create_session(
        title="Dailys",
        model_size="base",
        language="en",
        audio_device=None
    )
    
    # Check that session starts ungrouped (folder_id is None)
    sessions = temp_db.get_all_sessions()
    assert sessions[0]["folder_id"] is None
    
    # Move session to the folder
    temp_db.move_session_to_folder(sid, fid)
    
    sessions = temp_db.get_all_sessions()
    assert sessions[0]["folder_id"] == fid
    
    # Remove session from folder (move to ungrouped)
    temp_db.move_session_to_folder(sid, None)
    
    sessions = temp_db.get_all_sessions()
    assert sessions[0]["folder_id"] is None

def test_folder_deletion_cascade_safety(temp_db):
    """Test that deleting a folder does NOT delete sessions inside it, but sets folder_id to None."""
    fid = temp_db.create_folder("Archive")
    
    sid = temp_db.create_session(
        title="Old Session",
        model_size="tiny",
        language="en",
        audio_device=None
    )
    
    # Move to folder
    temp_db.move_session_to_folder(sid, fid)
    
    # Delete folder
    temp_db.delete_folder(fid)
    
    # Folder should be gone
    folders = temp_db.get_all_folders()
    assert len(folders) == 0
    
    # Session should still exist, but folder_id must be None
    sessions = temp_db.get_all_sessions()
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Old Session"
    assert sessions[0]["folder_id"] is None
