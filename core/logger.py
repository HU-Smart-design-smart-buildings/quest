import logging
from pathlib import Path
from config.config import LOGS_DIR, LOG_FORMAT, LOG_LEVEL

def setup_logger(name, log_file=None):
    """
    Setup een logger met file en console handlers.
    
    Args:
        name: Logger naam (bv. __name__)
        log_file: Optionele log-filename (anders: auto-gegenereerd)
    
    Returns:
        Logger object
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file is None:
        from datetime import datetime
        log_file = f"quest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_path = LOGS_DIR / log_file
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger