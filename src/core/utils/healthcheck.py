import sys
from urllib.request import urlopen

PORT = 8000
TIMEOUT = 3


def check(path: str, port: int = PORT) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}{path}", timeout=TIMEOUT) as response:
            return response.status == 200
    except OSError:
        return False


if __name__ == "__main__":
    sys.exit(0 if check(sys.argv[1]) else 1)
