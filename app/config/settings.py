import os
import json
from dataclasses import dataclass, asdict, field
from typing import Optional

DEFAULT_SETTINGS_PATH = os.path.expanduser("~/.pink_transcribe/settings.json")

# Detect default hardware once at module load
DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE = "cpu", "int8"
try:
    import ctranslate2
    if ctranslate2.get_cuda_device_count() > 0:
        DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE = "cuda", "float16"
except Exception:
    pass

@dataclass
class AppSettings:
    audio_device: Optional[str] = None  # None means system default
    model_size: str = "base"            # tiny, base, small, medium, large-v3
    device: str = DEFAULT_DEVICE        # cpu, cuda (auto-detected, but configurable)
    compute_type: str = DEFAULT_COMPUTE_TYPE # int8, float16, float32, default to int8 for wide CPU compatibility
    language: str = "auto"              # 'auto' or ISO 639-1 language code (e.g., 'en', 'es')
    autosave_interval_sec: int = 10
    save_audio_enabled: bool = False
    vad_threshold: float = 0.5
    theme: str = "dark_cyberpunk"

    def save(self, path: str = DEFAULT_SETTINGS_PATH) -> None:
        """Saves current settings to a JSON file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            # We don't want a settings save failure to crash the app, but it should be reported.
            print(f"Error saving settings to {path}: {e}")

    @classmethod
    def load(cls, path: str = DEFAULT_SETTINGS_PATH) -> "AppSettings":
        """Loads settings from a JSON file. Falls back to defaults on error/absence."""
        if not os.path.exists(path):
            settings = cls()
            settings.save(path)
            return settings

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Filter out any keys in JSON that are not fields in our dataclass
            import dataclasses
            valid_fields = {f.name: f.type for f in dataclasses.fields(cls)}
            
            filtered_data = {}
            for k, v in data.items():
                if k in valid_fields:
                    filtered_data[k] = v
            
            return cls(**filtered_data)
        except Exception as e:
            print(f"Error loading settings from {path}, using defaults: {e}")
            return cls()
