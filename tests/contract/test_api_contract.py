from typing import Any

import pytest
from _openapi import (
    generate_all,
    snapshot_files,
    snapshot_path,
    write_snapshots,
)
from _snapshot import REGENERATE_HINT, UPDATE, diff_message, dump_json


@pytest.fixture(scope="session")
def current_contracts() -> dict[str, dict[str, dict[str, Any]]]:
    contracts = generate_all()
    if UPDATE:
        write_snapshots(contracts)
    return contracts


def test_every_api_version_has_a_snapshot(
    current_contracts: dict[str, dict[str, dict[str, Any]]],
) -> None:
    produced = {
        (service, version)
        for service, versions in current_contracts.items()
        for version in versions
    }

    assert produced == set(snapshot_files()), (
        "API versions and contract snapshots diverged: a new version needs a "
        "snapshot, a removed one must have its snapshot deleted "
        f"({REGENERATE_HINT})"
    )


@pytest.mark.parametrize(
    ("service", "version"),
    snapshot_files(),
    ids=[f"{service}-{version}" for service, version in snapshot_files()],
)
def test_api_contract_is_unchanged(
    service: str,
    version: str,
    current_contracts: dict[str, dict[str, dict[str, Any]]],
) -> None:
    contract = current_contracts.get(service, {}).get(version)
    assert contract is not None, f"{service} {version} is no longer served"
    expected = snapshot_path(service, version).read_text(encoding="utf-8")
    actual = dump_json(contract)
    if actual != expected:
        pytest.fail(
            f"{service} {version} contract changed, but a released version "
            "must stay identical: add a new version, or regenerate with "
            f"{REGENERATE_HINT} and review the diff.\n"
            f"{diff_message(expected, actual)}"
        )
