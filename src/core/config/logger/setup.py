
import json
import logging.config
from pathlib import Path
import sys

from core.config.logger.handler import handle_exception


LOG_CONFIG_FILE = Path(__file__).parent / "logger.json"

sys.excepthook = handle_exception

def setup():
    """Loads the logging configuration and creates necessary directories"""
    with open(LOG_CONFIG_FILE, "r", encoding="utf8") as f:
        config = json.load(f)

    # Extract log file paths and create directories if they don't exist
    log_dirs = set(
        Path(handler["filename"]).parent
        for handler in config.get("handlers", {}).values()
        if "filename" in handler
    )
    for log_dir in log_dirs:
        log_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config)