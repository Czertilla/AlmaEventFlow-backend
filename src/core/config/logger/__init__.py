from logging import setLoggerClass

from .formatter import setup
from .logger import IDLogger

setLoggerClass(IDLogger)

__all__ = ["setup"]
