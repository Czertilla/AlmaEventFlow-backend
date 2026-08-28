import json
import os
import sys
from pathlib import Path

from uvicorn import run

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def run_monolith():
    os.environ["MONOLITH"] = "true"

    with open("src/core/config/logger/config.json", "rb") as f:
        config = json.loads(f.read())
    config["handlers"]["file_json"]["filename"] = "logs/monolith/app.jsonl"
    config["handlers"]["file_debug"]["filename"] = "logs/monolith/app.log"
    run(
        "aef.main:app",
        host="localhost",
        port=8000,
        reload=True,
        lifespan="on",
        log_config=config,
    )


if __name__ == "__main__":
    run_monolith()
