import os
from typing import Dict, Any, Tuple, Optional, Generator, List
import numpy as np
from faster_whisper import WhisperModel
from app.utils.logger import logger

class TranscriptionEngine:
    """Manages local Whisper model loading and inference."""

    def __init__(self):
        self.model: Optional[WhisperModel] = None
        self.current_model_size: Optional[str] = None
        self.current_device: Optional[str] = None
        self.current_compute_type: Optional[str] = None

    @staticmethod
    def detect_hardware() -> Tuple[str, str]:
        """Detects whether CUDA is available and returns recommended (device, compute_type)."""
        try:
            # We can check via a dummy torch import if available, or using ctypes to see if nvrtc/cuda is loaded,
            # but faster-whisper checks CUDA support natively.
            # A robust way is to try initializing a light model or checking environment.
            # Since PyTorch isn't a direct dependency of faster-whisper (which uses ctranslate2),
            # we can check if cuda is supported by ctranslate2:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                logger.info(f"CUDA-capable GPU(s) detected: {ctranslate2.get_cuda_device_count()} device(s) found.")
                return "cuda", "float16"
        except Exception as e:
            logger.debug(f"ctranslate2 CUDA check failed/ignored: {e}")
        
        logger.info("No CUDA GPU detected or ctranslate2 GPU check failed. Using CPU fallback.")
        return "cpu", "int8"

    def load_model(self, model_size: str, device: str = "cpu", compute_type: str = "int8") -> bool:
        """Lazily loads the Whisper model. If already loaded with same parameters, reuse it."""
        if (self.model is not None and 
            self.current_model_size == model_size and 
            self.current_device == device and 
            self.current_compute_type == compute_type):
            logger.info("Requested model is already loaded. Reusing current instance.")
            return True

        # Clean up old model if any to free memory
        if self.model is not None:
            logger.info("Deallocating old WhisperModel instance to reclaim GPU/RAM resources...")
            del self.model
            self.model = None
            import gc
            gc.collect()
            
        self.current_model_size = None
        self.current_device = None
        self.current_compute_type = None

        logger.info(f"Loading Whisper model '{model_size}' on '{device}' with quantization '{compute_type}'...")
        
        try:
            # Load WhisperModel. Will download from HF hub offline-ready on first run.
            self.model = WhisperModel(
                model_size_or_path=model_size,
                device=device,
                compute_type=compute_type,
                download_root=os.path.expanduser("~/.cache/huggingface/hub")
            )
            self.current_model_size = model_size
            self.current_device = device
            self.current_compute_type = compute_type
            logger.info(f"Whisper model '{model_size}' loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Whisper model '{model_size}' on '{device}': {e}", exc_info=True)
            # Fallback to CPU if CUDA failed
            if device == "cuda":
                logger.warning("Retrying model load with CPU fallback...")
                return self.load_model(model_size, device="cpu", compute_type="int8")
            return False

    def unload_model(self) -> None:
        """Explicitly unloads the Whisper model to free memory resources."""
        if self.model is not None:
            logger.info("Unloading WhisperModel instance to free memory...")
            del self.model
            self.model = None
            import gc
            gc.collect()
        self.current_model_size = None
        self.current_device = None
        self.current_compute_type = None

    def transcribe(
        self, 
        audio_data: np.ndarray, 
        language: str = "auto",
        vad_threshold: float = 0.5,
        initial_prompt: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """Transcribes a raw audio buffer and returns full text, segment details, and metadata."""
        if not self.model:
            raise RuntimeError("Model is not loaded. Call load_model() first.")

        # Match auto language
        lang_code = None if language == "auto" else language
        
        # Whisper expects float32 between -1.0 and 1.0. Ensure sounddevice inputs are ready.
        # sounddevice records in float32 in that range natively.
        
        logger.debug(f"Transcribing buffer size: {len(audio_data)} samples (~{len(audio_data)/16000:.1f}s)")
        
        try:
            # Run model transcription. vad_filter removes silent spaces.
            segments, info = self.model.transcribe(
                audio_data,
                language=lang_code,
                beam_size=5,
                initial_prompt=initial_prompt,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=vad_threshold,
                    min_silence_duration_ms=1000,
                    speech_pad_ms=400
                )
            )
            
            # segments is a generator, we must evaluate it
            segment_list = []
            full_text_parts = []
            
            for segment in segments:
                segment_list.append({
                    "start_time": segment.start,
                    "end_time": segment.end,
                    "text": segment.text,
                    "confidence": getattr(segment, "avg_logprob", 0.0)
                })
                full_text_parts.append(segment.text)
                
            full_text = " ".join(full_text_parts).strip()
            
            metadata = {
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration
            }
            
            return full_text, segment_list, metadata
            
        except Exception as e:
            logger.error(f"Error during transcription inference: {e}", exc_info=True)
            raise
