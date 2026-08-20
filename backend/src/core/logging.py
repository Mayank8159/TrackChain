# Structured logging setup for the API.

import logging
import sys
from src.config import get_settings


def setup_logging():
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("trackchain")
    logger.setLevel(log_level)
    return logger
