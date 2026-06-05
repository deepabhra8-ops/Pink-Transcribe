import os
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.expanduser("~/.pink_transcribe/logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """Configures and returns the application logger."""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger("PinkTranscribe")
    logger.setLevel(level)
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Console formatter
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [%(filename)s:%(lineno)d] | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # File formatter (more detailed)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [%(threadName)s] | %(filename)s:%(lineno)d | %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Rotating file handler (max 5MB per file, keep 3 backup files)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to initialize rotating file logger: {e}")
        
    return logger

# Create pre-configured root-like logger for simplicity
logger = setup_logger()
