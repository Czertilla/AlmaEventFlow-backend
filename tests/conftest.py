import os
import sys
from pathlib import Path

os.environ.setdefault("DB_DBMS", "sqlite")
os.environ.setdefault("MONOLITH", "false")
os.environ.setdefault("IN_MEMORY_BROKER", "true")

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
