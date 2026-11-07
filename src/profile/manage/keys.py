"""Jobs over the keys of personal data. Run them where profile runs, with its
settings (the database and the key providers):

    python -m profile.manage.keys status [--retired local:kek:1]
    python -m profile.manage.keys rewrap --to vault [--dry-run]
    python -m profile.manage.keys rotate-dek [--person ID ...] [--older-than-days N]
    python -m profile.manage.keys destroy --person ID --reason TEXT --yes

`rewrap` and `rotate-dek` work in batches (MIGRATION_BATCH_SIZE, a pause of
MIGRATION_SLEEP_MS between them) and are resumed by running them again.
"""

import argparse
import asyncio
import sys
from datetime import timedelta
from logging import basicConfig, getLogger
from profile.crypto import DecryptionError, KeyProviderError, KeyRing, build_keyring
from profile.crypto.keyring import build_provider
from profile.dependency._uow import profile_sessionmaker
from profile.dto.key_maintenance import DestroyKeyDTO
from profile.service.key_maintenance import KeyMaintenanceService
from profile.uow.person_key import PersonalDataUOW
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config.settings import Settings, settings
from core.utils.exc.http import VancedHTTPException

logger = getLogger("profile.keys")


def ring_for(target: str, config: Settings = settings) -> KeyRing:
    """The target wraps; every other configured provider only unwraps."""
    readers = [
        name
        for name in dict.fromkeys([config.KEY_PROVIDER, *config.KEY_PROVIDERS_READ])
        if name and name != target
    ]
    return KeyRing(
        build_provider(target, config),
        [build_provider(name, config) for name in readers],
    )


def _progress(done: int, total: int) -> None:
    logger.info("%d of %d", done, total)


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m profile.manage.keys",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="count the data keys")
    status.add_argument(
        "--retired", help="fail while any data key is still wrapped by this key_ref"
    )
    rewrap = commands.add_parser(
        "rewrap", help="wrap every data key again with the current key of --to"
    )
    rewrap.add_argument("--to", required=True, help="the provider to move keys to")
    rotate = commands.add_parser(
        "rotate-dek", help="give persons new data keys and seal their values again"
    )
    for command in (rewrap, rotate):
        command.add_argument("--dry-run", action="store_true", help="only count")
        command.add_argument("--batch-size", type=int)
        command.add_argument("--sleep-ms", type=int)
    rotate.add_argument("--person", type=UUID, action="append", dest="persons")
    rotate.add_argument("--older-than-days", type=int)
    destroy = commands.add_parser(
        "destroy", help="destroy a person's data key and the data it encrypts"
    )
    destroy.add_argument("--person", type=UUID, required=True)
    destroy.add_argument("--reason", required=True)
    destroy.add_argument("--yes", action="store_true", help="really destroy")
    return parser


async def run(
    args: argparse.Namespace,
    maker: async_sessionmaker[AsyncSession] | None = None,
    ring: KeyRing | None = None,
) -> int:
    uow = PersonalDataUOW(maker or profile_sessionmaker())
    match args.command:
        case "status":
            status = await KeyMaintenanceService(uow).status()
            for key_ref, count in sorted(status.by_key_ref.items()):
                logger.info("wrapped by %s: %d", key_ref, count)
            for version, count in sorted(status.by_dek_version.items()):
                logger.info("data key version %d: %d", version, count)
            logger.info("destroyed: %d", status.destroyed)
            if args.retired and status.by_key_ref.get(args.retired):
                logger.error("%s still wraps data keys", args.retired)
                return 1
            return 0
        case "rewrap":
            ring = ring or ring_for(args.to)
            try:
                report = await KeyMaintenanceService(uow, ring=ring).rewrap(
                    batch_size=args.batch_size,
                    pause_ms=args.sleep_ms,
                    dry_run=args.dry_run,
                    progress=_progress,
                )
            finally:
                await ring.close()
            logger.info(
                "%d data key(s) not on %s, %d rewrapped%s",
                report.found,
                report.target,
                report.rewrapped,
                ", nothing written" if report.dry_run else "",
            )
            return 0
        case "rotate-dek":
            ring = ring or build_keyring()
            try:
                rotated = await KeyMaintenanceService(uow, ring=ring).rotate(
                    args.persons,
                    timedelta(days=args.older_than_days)
                    if args.older_than_days is not None
                    else None,
                    batch_size=args.batch_size,
                    pause_ms=args.sleep_ms,
                    dry_run=args.dry_run,
                    progress=_progress,
                )
            finally:
                await ring.close()
            logger.info(
                "%d person(s) due, %d rotated%s",
                rotated.found,
                rotated.rotated,
                ", nothing written" if rotated.dry_run else "",
            )
            return 0
        case _:
            if not args.yes:
                logger.error("destroying cannot be undone: add --yes")
                return 1
            destroyed = await KeyMaintenanceService(uow).destroy(
                args.person, DestroyKeyDTO(args.person, args.reason), None
            )
            logger.info(
                "destroyed: %d row(s) deleted, %d cleared",
                destroyed.rows_deleted,
                destroyed.rows_cleared,
            )
            return 0


def main(argv: list[str] | None = None) -> int:
    basicConfig(level="INFO", format="%(asctime)s %(message)s")
    args = parser().parse_args(argv)
    try:
        return asyncio.run(run(args))
    except (KeyProviderError, DecryptionError) as exc:
        logger.error("stopped: %s", exc.code)
        return 1
    except VancedHTTPException as exc:
        logger.error("refused: %s", exc.detail)
        return 1


if __name__ == "__main__":
    sys.exit(main())
