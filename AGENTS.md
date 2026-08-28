# AGENTS.md

Instructions for AI coding agents (and human contributors skimming for conventions) working in
this repository. This file captures conventions this project actually follows — observed in its
code, migrations and git history — not generic defaults. Follow it over generic assumptions.

## Project shape

AlmaEventFlow (AEF) is a **multi-service backend** for a student-collective event-management
platform, managed with `uv` as a single workspace (`pyproject.toml` at repo root, one `uv.lock`).
There is no single "the backend" entrypoint — `src/` holds one directory per deployable service,
sharing one codebase and one dependency-resolution graph:

- `src/core/` — shared library every service imports (`from core.xxx import ...`). Config
  (`core/config/settings.py`, one `Settings` class read by every service — safe to add a
  service-specific field here even if only one service uses it), the SQLAlchemy/Beanie UoW and
  repository abstractions, the Kafka broker wrapper (`core/broker/kafka.py`), JWT verification
  (`core/utils/jwt/`), and the EDA message envelopes (`core/schema/message/`).
- `src/user/`, `src/profile/`, `src/org/`, `src/event/`, `src/geo/`, `src/mail/`, `src/notify/`,
  `src/bot/` — independent microservices. Each has its own Postgres database (`DB_NAME` env var),
  its own `Dockerfile`, `run.sh`, `main.py` (`from <service>.app.app import app`), and its own
  `api/`, `models/`, `service/`, `uow/`, `repository/`, `schema/`, `dependency/` subtree.
- `src/aef/` — the **monolith entrypoint**. `aef.app.app` builds one `FastAPI` app that mounts
  every service's HTTP routers (`aef/api/__init__.py`, each service's `include_routers(app)`) and
  aggregates lifespans that own background work (`AEFContextManager` wraps e.g.
  `NotifyContextManager` — without this, workers like the notify outbox publisher never start in
  the combined process). Toggled by `MONOLITH=true`. Not every service is necessarily wired into
  the monolith yet — check `aef/api/__init__.py` and `aef/app/contextmanager.py` before assuming
  a given service runs there.
- `docker-compose.yml` runs the monolith (`aef`, port 8000, Traefik at the bare API host) **and**
  most services as their own containers in parallel (`user`, `mail`, `profile`, `event`, `org`,
  `geo`, `notify`, ports 8001–8007+, Traefik `PathPrefix('/<service>')`). New services should get
  their own container block mirroring an existing one (`notify`'s is a good template) rather than
  only being wired into the monolith.
- `frontend/` is a **git submodule** (Ionic Vue) — treat it as a separate deployable; its API
  client (`frontend/src/api/generated/`) is Orval-generated from `frontend/api_schema/openapi.json`.
- `migrations/` is shared: one Alembic environment, but `alembic.ini` has a `[<service>]` section
  per service (`script_location`, `version_locations = migrations/versions/<service>`,
  `database_name`), and `migrations/env.py` picks the target service from `-n <service>` and does
  `__import__(f"{service}.models", fromlist=["*"])` — every service needs a `<service>/models/`
  package (not `model/`, singular, which is just where the ORM classes live) that re-exports every
  ORM class, or autogenerate/upgrade silently sees no tables. Run migrations with
  `alembic -n <service> upgrade head`; new revisions go under `migrations/versions/<service>/`.

## Event-driven sync between services (EDA)

- Kafka via `faststream` (`core/broker/kafka.py`); `IN_MEMORY_BROKER=true` swaps in an in-process
  broker for tests/local dev without a real Kafka.
- **Every EDA message's `data` field is a `list[T]`**, even for a single entity — created/updated/
  deleted events always carry a batch (`core/schema/message/core.py`'s `MQEvent`). Publishers wrap
  single entities in a one-element list; consumers iterate the list inside one UoW transaction.
  `core/database/sqlalchemy/mixins/repositories.py` has `upsert_many` if a per-item loop needs
  batching later.
- Cross-service identity is **`person_id`**, not any one service's own primary key. It's embedded
  directly in the user-facing JWT (`sub`/`per` claims, `core/utils/jwt/auth.py`) and is what
  authorization checks compare against locally-owned rows (e.g. `event`'s
  `verify_collective_principal`/`verify_member_person`, `event/dependency/principal.py`).
  Projections of upstream data (e.g. `notify`'s local `account` table, sourced from `user`'s
  `account.*` Kafka events) generally key on the owning service's id but also carry `person_id`
  for exactly this cross-service join.
- A read-model projection sourced from another service's events (e.g. `notify.account`,
  `user.person`) never has a DB-level FK to the source table — it's a different database. `user_id`/
  `person_id` columns on these projections are "raw" UUIDs by design; the row can legitimately
  arrive before, or never, or the local row can pre-date the projection (eventual consistency).

## Service-layer convention: `_`-helpers vs. public methods

Across `src/*/service/*.py`:

- **`_`-prefixed methods** (`_create`, `_read`, `_update`, `_upsert`, `_delete`, domain resolvers)
  are CRUD helpers decorated `@required_transaction` (`core/service/base.py`). They do **not** open
  or commit a transaction — they operate on `self.uow.<repo>`/`self.uow.session` so a parent
  service can compose them inside its own transaction (e.g. `event/service/event.py`'s
  `create_with_collective` calls `attendance_service._create(...)`).
- **Public methods** (`create`, `read`, `patch`, `put`, `delete`, `search`, composite ones) are the
  external interface: they open `async with self.uow`, delegate to `_`-helpers, `commit`, and
  publish EDA events **after** commit. They must not call `self.uow.<repo>.<crud>` directly.
- Every service extends `BaseService[ABCUnitOfWork]` (or a narrower bound) for `self.uow`; a
  mutating method not decorated `@required_transaction` and called outside `async with uow` raises
  `RequiredTransactionException` — this is a deliberate fail-loud mechanism, not a lint nit.
- `AbstractRepository.from_uow(cls, uow) -> Self` (`core/utils/abstract/repository.py`) is the
  single plugin point for how a UoW-managed repository gets constructed; a service never
  constructs a repository directly (`PartnerRepository(uow.session)`-style code is wrong) — it
  reads `self.uow.<name>` where the UoW class declares that attribute (e.g. `AppUnitOfWork`/
  per-service UoW composing repos via type hints scanned in `BaseUOW.__aenter__`).

## Code style

- Domain exceptions live in `<service>/exc/` (or the older `exceptions/` in `user`) as plain
  exception classes, translated to HTTP at the API boundary.
- Reference/lookup tables (event status, event type, ...) are small seeded tables
  (`SmallSerialMixin`, e.g. `EventStatusORM`) with an FK column on the owning row — **not** native
  Postgres `ENUM` types — because they're painful to extend via migration. `notify`'s
  `TransportTypeEnum` is a deliberate, documented exception (mapped to a real Postgres `ENUM`); if
  you're adding a new fixed vocabulary, default to the reference-table pattern unless you have as
  strong a reason as that one.
- Existing tables are generally not altered for a new cross-cutting concern; prefer a new table
  (see the calendar-subscription feature: new tables only, FKs added wherever the referenced table
  lives in the same DB, `ondelete="NO ACTION"`/`"SET NULL"` as appropriate, no FK across a service
  boundary — a projected/foreign id column stays a raw UUID).
- **No explanatory comment blocks.** Do not narrate the reasoning behind a change, the bug it
  fixes, or alternatives you considered — that belongs in the commit message or chat response, not
  the file. Default to zero comments. If something is genuinely non-obvious, one short line (not a
  paragraph, not a bulleted list) is the max — and only for the *why* (constraint, invariant), never
  the *what* the code already says.

## Commit conventions

- **Conventional Commits** (`type(scope): subject`, e.g. `fix(event): ...`, `feat(user): ...`,
  `chore(frontend): ...`) — confirmed by `git log`, this is the convention actually in use. Pick
  the type that matches what changed (bug fix → `fix`, new capability → `feat`, no-behavior-change
  reshuffle → `refactor`).
- Single-author repo; only commit when asked, or as the natural conclusion of a scoped, approved
  chunk of work. Group related changes into one coherent commit; split unrelated changes even if
  they landed in the same session.
- Never `--amend`, never force-push, never skip hooks (`--no-verify`) unless explicitly told to.

## Verification workflow

- **The FastAPI app cannot be imported standalone in a fresh interpreter across services** —
  importing `aef.main` (or two services' `models` together, e.g. `event.models` +
  `profile.models`) raises `sqlalchemy.exc.InvalidRequestError: Table '...' is already defined`
  (shared `Base.metadata`, import-order sensitive on tables like `person`/`organization`/
  `location` that multiple services declare). This is environmental, not a code bug. To smoke-test
  a single service without booting the whole app, import **one service tree per interpreter**,
  e.g. `cd src && ../.venv/Scripts/python.exe -c "import event.service.participation"`. Use
  `python -m py_compile <files>` for a pure syntax check.
- Backend checks: `uv run pytest`, `uv run ruff check .`, `uv run pyright` (config permitting).
  `tests/conftest.py` forces `DB_DBMS=sqlite`, `MONOLITH=false`, `IN_MEMORY_BROKER=true` before
  imports specifically to dodge the metadata collision above — new test modules should rely on
  that, not reintroduce a second workaround.
- After adding/changing a migration: `uv run alembic -n <service> upgrade head` against the local
  dev Postgres (`docker compose up -d pg`).
- Frontend (submodule): `npx vue-tsc --noEmit`, `npx eslint <files>`; regenerate the API client
  with `npm run generate` (fetches the schema from a running backend, then runs Orval) after a
  backend contract change — don't hand-edit the generated client as a substitute for regenerating
  it, only as a stopgap when the backend isn't runnable.

## Where things are documented

- Some services carry their own design docs worth reading before touching them, e.g.
  `src/notify/ROADMAP.md` and `src/notify/TECH_TASK.md` (notify's transport-plugin architecture
  and explicit scope boundaries — what notify does and deliberately does not own).
- This file: process and cross-service convention only, not what any single service does — check
  that service's own code/docs for its business logic.
