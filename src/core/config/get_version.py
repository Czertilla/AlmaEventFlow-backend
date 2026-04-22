import tomllib
from pathlib import Path


def find_pyproject_toml(start_path=None):
    if start_path is None:
        start_path = Path(__file__).resolve().parent
    current = start_path
    while True:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            return pyproject_path
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError("pyproject.toml not found in any parent directory.")


def get_version():
    pyproject_path = find_pyproject_toml()
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["version"]
