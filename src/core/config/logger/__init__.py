from .formatter import setup
from logging import setLoggerClass
from .logger import IDLogger

setLoggerClass(IDLogger)

__all__ = ["setup"]
