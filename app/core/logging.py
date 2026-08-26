import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format=("%(asctime)s | %(levelname)s | %(name)s | %(message)s"),
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
