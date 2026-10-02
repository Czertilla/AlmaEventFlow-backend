import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from _openapi import HERE, PINNED_ENV, ROOT
from _registry import RESPONSES, SCHEMA_PACKAGES


def _run(args: list[str]) -> Any:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "behavior.json"
        subprocess.run(
            [
                sys.executable,
                str(HERE / "_dump_behavior.py"),
                args[0],
                args[1],
                str(out),
                *args[2:],
            ],
            check=True,
            cwd=ROOT,
            env={**os.environ, **PINNED_ENV},
            capture_output=True,
        )
        return json.loads(out.read_text(encoding="utf-8"))


def generate_behavior() -> dict[str, dict[str, Any]]:
    jobs: dict[tuple[str, str], list[str]] = {
        ("characterize", name): ["characterize", package]
        for name, package in SCHEMA_PACKAGES.items()
    }
    for name, (package, pairs) in RESPONSES.items():
        jobs[("responses", name)] = ["responses", package, json.dumps(pairs)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(_run, jobs.values()))
    grouped: dict[str, dict[str, Any]] = {"characterize": {}, "responses": {}}
    for (kind, name), result in zip(jobs, results, strict=True):
        grouped[kind][name] = result
    return grouped
