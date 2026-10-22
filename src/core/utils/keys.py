from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)


class KeyMissingError(RuntimeError):
    """A key the configuration names is not there: the service must not start."""


def read_key(path: str, what: str) -> str:
    try:
        return Path(path).read_text()
    except OSError as exc:
        message = f"{what} is not readable at {path}"
        logger.critical(message)
        raise KeyMissingError(message) from exc
