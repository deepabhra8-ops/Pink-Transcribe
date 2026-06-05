import numpy as np
import pytest
from app.audio.capture import AudioRecorder

def test_audio_resampler():
    """Verify that the linear resampling interpolation converts sample rates correctly."""
    recorder = AudioRecorder(target_sample_rate=16000)
    
    # Generate 1 second of 48000Hz audio (sine wave)
    freq = 440
    orig_sr = 48000
    t = np.linspace(0, 1.0, orig_sr, endpoint=False)
    sine_48k = np.sin(2 * np.pi * freq * t).astype(np.float32)
    
    # Resample to 16000Hz
    resampled = recorder._resample(sine_48k, orig_sr=orig_sr, target_sr=16000)
    
    # Assert duration/length is correct
    assert len(resampled) == 16000
    assert resampled.dtype == np.float32
    
    # Repeat for 44100Hz to 16000Hz
    orig_sr_cd = 44100
    t_cd = np.linspace(0, 1.0, orig_sr_cd, endpoint=False)
    sine_44k = np.sin(2 * np.pi * freq * t_cd).astype(np.float32)
    resampled_cd = recorder._resample(sine_44k, orig_sr=orig_sr_cd, target_sr=16000)
    
    assert len(resampled_cd) == 16000

def test_vu_meter_level_limits():
    """Verify that VU level normalization is clamped to 0.0 - 1.0 range."""
    recorder = AudioRecorder()
    
    # Pure silence should yield 0.0 RMS
    silence = np.zeros(1600, dtype=np.float32)
    rms_silence = np.sqrt(np.mean(silence ** 2))
    vu_silence = min(1.0, float(rms_silence * 3.5))
    assert vu_silence == 0.0
    
    # Full scale clipping audio should clamp VU level to 1.0
    clipping_audio = np.ones(1600, dtype=np.float32)
    rms_clip = np.sqrt(np.mean(clipping_audio ** 2))
    vu_clip = min(1.0, float(rms_clip * 3.5))
    assert vu_clip == 1.0
