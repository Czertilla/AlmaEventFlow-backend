import json
from multiprocessing import Process
from uvicorn import run
import os


def set_db_name(db_name: str):
    os.environ["DB_NAME"] = db_name


def log_dir(microservice_name: str):
    return f"logs/{microservice_name}/"


def run_microservice(app_name: str, port: int):
    set_db_name(app_name)
    with open("src/core/config/logger/config.json", "rb") as f:
        config = json.loads(f.read())
    config["handlers"]["file_json"]["filename"] = (
        f"{log_dir(app_name)}app.jsonl"
    )
    config["handlers"]["file_debug"]["filename"] = f"{log_dir(app_name)}app.log"
    run(
        f"{app_name}.main:app",
        host="localhost",
        port=port,
        reload=False,
        # reload_dirs=[f"src/{app_name}", "src/core"],
        lifespan="on",
        log_config=config,
    )


if __name__ == "__main__":
    microservices_args = (
        ("user", 8000),
        ("mail", 8001),
        ("profile", 8002),
        ("event", 8003),
        ("org", 8004),
        ("geo", 8005)
    )
    microservices = [
        Process(target=run_microservice, args=args, name=args[0])
        for args in microservices_args
    ]

    for microservice in microservices:
        microservice.start()

    for microservice in microservices[::-1]:
        microservice.join()
