"""Creates a key file for `KEY_PROVIDER=local`.

    python -m profile.crypto.keygen <dir> --version 1 [--passphrase-file FILE]

Writes `<dir>/kek.v<version>` (32 random bytes, mode 0400) and refuses to
overwrite one. Keep a copy apart from the database backups: without it the
personal data is lost."""

import argparse
import os
import sys
from pathlib import Path

from .local import KEK_SIZE, read_passphrase, seal_kek


def create(directory: Path, version: int, passphrase_file: Path | None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"kek.v{version}"
    kek = os.urandom(KEK_SIZE)
    if passphrase_file is not None:
        kek = seal_kek(kek, read_passphrase(passphrase_file))
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descriptor, "wb") as file:
        file.write(kek)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m profile.crypto.keygen")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--passphrase-file", type=Path)
    args = parser.parse_args(argv)
    version: int = args.version
    if version < 1:
        parser.error("--version starts at 1")
    try:
        path = create(args.directory, version, args.passphrase_file)
    except FileExistsError as exc:
        print(f"{exc.filename} already exists", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
