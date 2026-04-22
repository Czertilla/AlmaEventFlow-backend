import json
import os
from uvicorn import run


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
