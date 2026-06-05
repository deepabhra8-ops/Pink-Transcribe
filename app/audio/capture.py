import queue
import threading
import time
from typing import List, Tuple, Optional, Any
import numpy as np
import sounddevice as sd
from app.utils.logger import logger

class AudioRecorder:
    """Manages audio capture from input devices in a background thread."""

    def __init__(self, target_sample_rate: int = 16000):
        self.target_sample_rate = target_sample_rate
        self.raw_queue: queue.Queue = queue.Queue()
        self.output_queue: queue.Queue = queue.Queue()
        
        self.stream: Optional[sd.InputStream] = None
        self.current_device_name: Optional[str] = None
        self.selected_device_id: Optional[int] = None
        
        self._is_recording = False
        self._processing_thread: Optional[threading.Thread] = None
        self._vu_level = 0.0  # Normalized between 0.0 and 1.0
        self._error_callback = None

    @staticmethod
    def list_devices() -> Tuple[List[str], Optional[str]]:
        """Queries and returns a list of microphone names and the default device name."""
        devices = sd.query_devices()
        mic_names = []
        default_idx = sd.default.device[0]  # Default input device index
        default_name = None
        
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                mic_names.append(dev['name'])
                if idx == default_idx:
                    default_name = dev['name']
                    
        return mic_names, default_name

    def _get_device_id_by_name(self, name: str) -> Optional[int]:
        """Resolves a device name string to a sounddevice device ID."""
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and dev['name'] == name:
                return idx
        return None

    def set_error_callback(self, callback) -> None:
        """Sets a callback to be executed in case of device failure."""
        self._error_callback = callback

    def get_vu_level(self) -> float:
        """Returns the current RMS volume level (0.0 to 1.0)."""
        return self._vu_level

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
        """Callback from sounddevice inside a high-priority C-level thread."""
        if status:
            logger.warning(f"Audio callback status check: {status}")
        
        # Copy audio chunk and put in queue
        self.raw_queue.put(indata.copy())

    def start(self, device_name: Optional[str] = None) -> bool:
        """Starts recording audio from the specified device."""
        if self._is_recording:
            return True

        self.current_device_name = device_name
        self.raw_queue = queue.Queue()
        self.output_queue = queue.Queue()  # Clear and recreate output queue to prevent memory leak/stale chunks
        
        # Determine device ID
        if device_name:
            device_id = self._get_device_id_by_name(device_name)
            if device_id is None:
                logger.error(f"Selected device '{device_name}' not found. Falling back to default.")
                device_id = sd.default.device[0]
        else:
            device_id = sd.default.device[0]

        if device_id == -1 or device_id is None:
            logger.error("No valid audio input devices found.")
            return False

        self.selected_device_id = device_id
        
        # Get native sample rate of device
        try:
            device_info = sd.query_devices(device_id)
            native_sr = int(device_info['default_samplerate'])
            logger.info(f"Using input device: {device_info['name']} (Native SR: {native_sr}Hz)")
        except Exception as e:
            logger.error(f"Error querying audio device: {e}", exc_info=True)
            return False

        # Start stream
        try:
            self.stream = sd.InputStream(
                device=device_id,
                channels=1,
                samplerate=native_sr,
                dtype='float32',
                blocksize=int(native_sr * 0.1),  # 100ms blocks
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as e:
            logger.error(f"Failed to open audio input stream: {e}", exc_info=True)
            return False

        self._is_recording = True
        
        # Start background processing thread (resampling, VU calculation)
        self._processing_thread = threading.Thread(
            target=self._process_audio_loop,
            args=(native_sr,),
            name="AudioProcessingThread",
            daemon=True
        )
        self._processing_thread.start()
        logger.info("Audio recording thread started successfully.")
        return True

    def stop(self) -> None:
        """Stops the audio recording and streams."""
        if not self._is_recording:
            return

        self._is_recording = False
        
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")
            self.stream = None

        if self._processing_thread:
            self._processing_thread.join(timeout=1.0)
            self._processing_thread = None

        self._vu_level = 0.0
        logger.info("Audio recording stopped.")

    def _process_audio_loop(self, source_sample_rate: int) -> None:
        """Reads raw audio blocks, resamples to 16kHz, computes RMS for VU, and pushes output."""
        while self._is_recording:
            try:
                # Blocks with timeout to check _is_recording flag
                raw_chunk = self.raw_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Exception in raw audio queue read: {e}")
                break

            try:
                # Calculate VU meter level (Root Mean Square)
                rms = np.sqrt(np.mean(raw_chunk ** 2)) if len(raw_chunk) > 0 else 0.0
                # Scale VU level for visualization (using logarithmic scaling or simple multiplier)
                # Max typical amplitude for normal speech is ~0.1-0.3, so scaling by 3.0 gives good visual feedback
                self._vu_level = min(1.0, float(rms * 3.5))

                # Flatten to 1D and resample to 16kHz if needed
                audio_data = raw_chunk.flatten()
                if source_sample_rate != self.target_sample_rate:
                    audio_data = self._resample(audio_data, source_sample_rate, self.target_sample_rate)

                # Push to transcription-ready output queue
                self.output_queue.put(audio_data)
            except Exception as e:
                logger.error(f"Error processing audio block: {e}", exc_info=True)
                if self._error_callback:
                    self._error_callback(str(e))
                break

    def _resample(self, audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resamples floating-point audio data to target sample rate using numpy interpolation."""
        duration = len(audio_data) / orig_sr
        num_target_samples = int(duration * target_sr)
        return np.interp(
            np.linspace(0, duration, num_target_samples, endpoint=False),
            np.linspace(0, duration, len(audio_data), endpoint=False),
            audio_data
        ).astype(np.float32)
