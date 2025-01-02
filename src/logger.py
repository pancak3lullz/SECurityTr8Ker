import logging
import colorlog
from src.config import LOG_FILE_PATH, LOG_DIR
import os

# Ensure the logs directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Initialize the root logger to capture DEBUG level logs
logger = colorlog.getLogger()
logger.setLevel(logging.DEBUG)  # Capture everything at DEBUG level and above

# Setting up colored logging for terminal
terminal_handler = colorlog.StreamHandler()
terminal_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }))
terminal_handler.setLevel(logging.INFO)  # Terminal to show INFO and above
logger.addHandler(terminal_handler)

# Setting up logging to file to capture DEBUG and above
file_handler = logging.FileHandler(LOG_FILE_PATH)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.DEBUG)  # File to capture everything at DEBUG level
logger.addHandler(file_handler)
