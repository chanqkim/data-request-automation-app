import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import (
    LOG_DIR,
    LOG_FILE_BACKUP_COUNT,
    LOG_FILE_NAME,
    LOG_FORMATER,
    LOG_LEVEL,
    LOG_MAX_BYTES,
)

# create logging directory if not exists
os.makedirs(LOG_DIR, exist_ok=True)

# logging configuration
logger = logging.getLogger("app_logger")
logger.setLevel(LOG_LEVEL)
formatter = logging.Formatter(LOG_FORMATER)

stream_handler = logging.StreamHandler()
# maximum 10MB, keep 30 backup log files(1 month)
file_handler = RotatingFileHandler(
    f"{LOG_DIR}/{LOG_FILE_NAME}",
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_FILE_BACKUP_COUNT,
    encoding="utf-8",
)

stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# prevent adding multiple handlers in case of multiple imports
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)  # also add console output
