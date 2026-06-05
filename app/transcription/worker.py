import time
import queue
import numpy as np
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal, Slot
from app.utils.logger import logger
from app.transcription.engine import TranscriptionEngine

class TranscriptionWorker(QThread):
    """Background worker thread that runs local inference on captured audio stream."""
    
    # Qt Signals for thread-safe UI communication
    status_changed = Signal(str)         # Status message
    partial_transcript = Signal(str)     # Real-time unfinalized text
    segment_finalized = Signal(dict)     # Finalized text segment (dict with start, end, text)
    error_occurred = Signal(str)         # Error description
    finished_session = Signal()          # Emitted when processing is done
    
    def __init__(
        self, 
        engine: TranscriptionEngine, 
        audio_queue: queue.Queue,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "auto",
        vad_threshold: float = 0.5,
        auto_detect_speakers: bool = False
    ):
        super().__init__()
        self.engine = engine
        self.audio_queue = audio_queue
        
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.vad_threshold = vad_threshold
        self.auto_detect_speakers = auto_detect_speakers
        
        self._is_running = False
        self._is_paused = False
        
        # Audio accumulator buffers for rolling transcription
        self.audio_buffer: List[np.ndarray] = []
        self.time_offset = 0.0  # Time offset of the current active buffer (in seconds)

    def set_language(self, language: str) -> None:
        self.language = language

    def set_vad_threshold(self, threshold: float) -> None:
        self.vad_threshold = threshold

    def pause_transcription(self) -> None:
        self._is_paused = True
        self.status_changed.emit("Paused")

    def resume_transcription(self) -> None:
        self._is_paused = False
        self.status_changed.emit("Transcribing")

    def stop(self) -> None:
        """Stops the worker thread loop."""
        self._is_running = False

    def run(self) -> None:
        """Main loop executed in the background thread."""
        self._is_running = True
        self.status_changed.emit("Initializing Model...")
        
        # 1. Load ASR Model
        success = self.engine.load_model(self.model_size, self.device, self.compute_type)
        if not success:
            self.error_occurred.emit(f"Failed to load Whisper model: '{self.model_size}'")
            self.status_changed.emit("Error")
            return
            
        self.status_changed.emit("Ready")
        logger.info("Transcription worker initialized and running.")
        
        last_inference_time = time.time()
        sample_rate = 16000

        while self._is_running:
            # 2. Consume from Queue
            try:
                # Polling queue with a short timeout to prevent blocking thread exit
                chunk = self.audio_queue.get(timeout=0.1)
                if not self._is_paused:
                    self.audio_buffer.append(chunk)
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Error reading audio queue in worker: {e}")
                
            # Sleep slightly to prevent burning CPU cycles in loop
            time.sleep(0.01)

        # 4. Final Flush when loop exits (run full speech batch transcription)
        self._flush_remaining_audio(sample_rate)
        self.finished_session.emit()
        self.status_changed.emit("Idle")
        logger.info("Transcription worker stopped.")

    def _flush_remaining_audio(self, sample_rate: int) -> None:
        """Processes and transcribes the entire accumulated audio buffer at once."""
        if not self.audio_buffer:
            return
        
        full_audio = np.concatenate(self.audio_buffer)
        audio_len = len(full_audio) / sample_rate
        if audio_len < 0.3:
            return
            
        self.status_changed.emit("Transcribing full recording...")
        logger.info(f"Running batch ASR transcription on complete audio buffer: {audio_len:.2f} seconds.")
        
        # Define prompt to guide recognition for Indian English accent
        prompt = None
        if self.language in ("en", "auto"):
            prompt = "Transcribing English speech with Indian accent, terminology, correct spelling and punctuation."
            
        try:
            # Transcribe the full consolidated audio array
            text, segments, _ = self.engine.transcribe(
                full_audio,
                language=self.language,
                vad_threshold=self.vad_threshold,
                initial_prompt=prompt
            )
            
            diarized_segments = []
            if self.auto_detect_speakers and len(segments) > 1:
                zcrs = []
                for seg in segments:
                    # Map segment time window to audio sample indices
                    start_idx = int(seg["start_time"] * sample_rate)
                    end_idx = int(seg["end_time"] * sample_rate)
                    seg_audio = full_audio[start_idx:end_idx]
                    
                    if len(seg_audio) > 100:
                        # Compute zero crossing rate with a small threshold to filter low-amplitude noise
                        zero_crossings = np.sum(np.abs(np.diff(np.sign(seg_audio))) > 0.5)
                        zcr = zero_crossings / len(seg_audio)
                    else:
                        zcr = 0.0
                    zcrs.append(zcr)
                
                # Perform threshold partitioning based on median ZCR (pitch proxy separation)
                median_zcr = np.median(zcrs) if zcrs else 0.0
                
                for i, seg in enumerate(segments):
                    speaker = "Speaker 1" if zcrs[i] >= median_zcr else "Speaker 2"
                    diarized_segments.append({
                        "start_time": self.time_offset + seg["start_time"],
                        "end_time": self.time_offset + seg["end_time"],
                        "text": seg["text"],
                        "confidence": seg["confidence"],
                        "speaker": speaker
                    })
            else:
                for seg in segments:
                    diarized_segments.append({
                        "start_time": self.time_offset + seg["start_time"],
                        "end_time": self.time_offset + seg["end_time"],
                        "text": seg["text"],
                        "confidence": seg["confidence"],
                        "speaker": "Speaker 1"
                    })
            
            for seg in diarized_segments:
                self.segment_finalized.emit(seg)
        except Exception as e:
            logger.error(f"Failed to transcribe audio buffer: {e}", exc_info=True)
            self.error_occurred.emit(f"Transcription failed: {str(e)}")
        finally:
            self.audio_buffer = []
            self.time_offset = 0.0
