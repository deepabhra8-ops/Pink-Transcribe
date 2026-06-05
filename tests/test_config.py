import os
import tempfile
import pytest
from app.config.settings import AppSettings, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE

def test_settings_default_values():
    """Verifies that default settings properties initialize correctly."""
    settings = AppSettings()
    assert settings.model_size == "base"
    assert settings.device == DEFAULT_DEVICE
    assert settings.compute_type == DEFAULT_COMPUTE_TYPE
    assert settings.language == "auto"
    assert settings.autosave_interval_sec == 10
    assert not settings.save_audio_enabled

def test_settings_save_and_load():
    """Verifies settings save to disk as JSON and read back properties accurately."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        settings_path = os.path.join(tmp_dir, "test_settings.json")
        
        settings = AppSettings(
            audio_device="Virtual Test Mic",
            model_size="tiny",
            device="cpu",
            language="es",
            autosave_interval_sec=15
        )
        settings.save(settings_path)
        
        assert os.path.exists(settings_path)
        
        # Load back
        loaded = AppSettings.load(settings_path)
        assert loaded.audio_device == "Virtual Test Mic"
        assert loaded.model_size == "tiny"
        assert loaded.device == "cpu"
        assert loaded.language == "es"
        assert loaded.autosave_interval_sec == 15
