from pathlib import Path


def get_dir(path: Path) -> list[str]:
    """Filenames (not full paths) of every file directly inside ``path``."""
    return sorted(entry.name for entry in path.iterdir() if entry.is_file())
