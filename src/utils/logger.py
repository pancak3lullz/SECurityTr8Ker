import os
import logging
import colorlog
from typing import Optional
from datetime import datetime

# Default log directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE_PATH = os.path.join(LOG_DIR, 'debug.log')

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Define log level based on environment variable (default: INFO)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL_NUM = getattr(logging, LOG_LEVEL, logging.INFO)

# Configure color formatter for console
color_formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)

# Configure standard formatter for file
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Cache for loggers to avoid creating duplicates
_loggers = {}

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    If the logger already exists, return the existing logger.
    Otherwise, create a new logger with both console and file handlers.
    
    Args:
        name: Name of the logger (default: 'SECurityTr8Ker')
        
    Returns:
        Configured logger instance
    """
    global _loggers
    
    # Default logger name if none provided
    if name is None:
        name = 'SECurityTr8Ker'
    
    # Return cached logger if it exists
    if name in _loggers:
        return _loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL_NUM)
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)
    console_handler.setLevel(LOG_LEVEL_NUM)
    
    # Create file handler
    # Use a file name based on the logger name
    module_name = name.split('.')[-1] if '.' in name else name
    log_filename = f"{datetime.now().strftime('%Y%m%d')}_{module_name}.log"
    log_filepath = os.path.join(LOG_DIR, log_filename)
    
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Cache the logger
    _loggers[name] = logger
    
    return logger
    
# Root logger for backwards compatibility
logger = get_logger('SECurityTr8Ker') 