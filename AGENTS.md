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
  its own `Dockerfile`, `run.sh`, `main.py` (`from <service>.app.app import app  # noqa: F401  #
  pyright: ignore[reportUnusedImport]` — the import is the ASGI entrypoint `uvicorn
  <service>.main:app` points at, not dead code; both suppressions are required, one per linter, or
  `ruff --fix`/`basedpyright` strict mode will each independently "clean up" what looks like an
  unused import and silently break the entrypoint), and its own `api/`, `models/`, `service/`,
  `uow/`, `repository/`, `schema/`, `dependency/` subtree.
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

## API layer, DTOs and schema versioning

Every HTTP service follows this: `event`, `org`, `geo`, `profile`, `notify`, `bot` and `user`
(`mail` has no HTTP API). A new service copies the shape of `org` (simple CRUD) or `event`.

- A service's HTTP API lives in `<service>/api/v<N>/router/` + `<service>/api/v<N>/schema/`
  (horizontal split, same as everywhere else — not per-entity packages, so schemas can import
  each other freely). `api/v<N>/__init__.py` aggregates the routers with
  `load_common(f"{__name__}.router", ...)`. A released `v<N>` schema never changes shape: a
  breaking change is a new `v<N+1>` package (v2 may import v1 schemas, never the reverse).
- Shared schema building blocks are versioned the same way: `core/schema/v1/` holds `PageV1`,
  `PageParamV1`, `PaginationV1`, and the schema mixins in `core/schema/v1/mixin/`
  (`FromDTOMixinV1`, `ToDTOMixinV1` in `dto.py`; `PatchModelV1`, `UUIDMixinV1`, `TimestampMixinV1`,
  … in `model.py`). Class names carry the `V1` suffix; a breaking change is a `…V2` class in
  `core/schema/v2/`, never an edit to the V1 one.
- Services and repositories are **DTO-only**: `<service>/dto/*.py` are frozen/slots dataclasses
  (`core/dto/`: `FieldsSetDTOMixin`, `dto_dict`, `dto_from_orm`, `PageDTO`/`PageParamDTO`/
  `PaginationDTO`); they never import `<service>.api.*` or `core.schema.*`. The router converts at
  the edge: request `schema.to_dto()` (set `__dto_cls__`), response `Read.from_dto(dto)`, list
  `PageV1[Read].from_dto(page_dto)`, page query `page_param.to_dto()`.
- `Filter` classes (fastapi-filter) stay ORM-bound in `<service>/filter/`; the service takes a
  `…FilterDTO` and rebuilds the `Filter` with `Filter.from_dto` right before the repository call.
- List endpoints sort and filter through `core/filter/`: `OrderedFilter` accepts only the fields in
  `Constants.order_fields` (anything else is a 422, and the allowed fields are listed in the
  `order_by` description), `TimestampFilterMixin` adds `created_at__gte/lte`, `edited_at__gte/lte`
  and `edited_at__isnull`, `RelatedSearchFilter` extends `search` over one related row with an
  `EXISTS`. A sort key that is not a model column (event `status`/`level`/`type`, ordered by the
  lookup id) is mapped in the filter's own `sort()`. Every filter field must exist on its
  `…FilterDTO`. Routers import `FilterDepends` from `core.filter.depends`, not from
  `fastapi_filter`: the original drops field descriptions from the OpenAPI schema.
- Detail reads carry `created_at`/`edited_at` (`TimestampMixinV1`) wherever the ORM row has
  `TimestampMixin`. The mixin sets `eager_defaults`, so a flushed row already has its computed
  `edited_at`; the columns have no server default, so a raw SQL insert must pass `created_at`. Each
  service's `ModuleBase` carries the `BasePreference` type map, which makes `datetime` a
  `timestamptz` — without it a tz-aware filter value fails in asyncpg.
- `PatchModelV1.model_dump()` already drops unset fields; never pass `exclude_unset` to it (it
  raises). PATCH handlers build `…Patch(id=..., **body.model_dump())` and `to_dto()` it.
- SQLAlchemy async cannot lazy-load: a service converting an ORM row to a DTO must hold every
  relationship it reads (eager options on the repository, or re-read the row with `_read` after
  `add_n_return`/`update_one`/`upsert`). Convert to the DTO before `commit()` — the monolith
  session maker expires attributes on commit.
- `user` is the exception to "services know nothing about the API library": `UserService` is
  DTO-only and library-free, and `user/api/manager.py` (`UserManager`, a fastapi-users
  `BaseUserManager`) is the adapter. It turns fastapi-users schemas into DTOs, calls the service
  and maps the domain exceptions in `user/exceptions/account.py` back to fastapi-users' ones. Cookies
  and `Request`/`Response` handling live in `user/utils/auth_response.py` and the routers, never in
  the service.

### Contract tests (`tests/contract/`)

They pin the API of every released version and the isolation between the service layer and the
schemas. No DB or Docker needed; `uv run pytest tests/contract` takes ~2min (each service's OpenAPI
is generated in its own subprocess with a pinned env, so a local `.env` cannot change a snapshot).

- `snapshots/<service>/<vN>.json` — the OpenAPI paths and reachable components of each service
  version. `test_every_api_version_has_a_snapshot` fails for a new version without a snapshot or a
  snapshot whose version is gone.
- `golden/<package>.json` — schema characterization: a deterministic sample payload per schema
  class (`required` and `full` variants) → validated → dumped → mapped to its DTO (`mapped`/
  `dropped` fields). Catches what OpenAPI cannot show: custom validators, aliases, defaults,
  `fields_set` semantics, a schema field silently not reaching the DTO.
- `golden/<package>_from_dto.json` — a sample service DTO rendered through its response schema
  (`RESPONSES` in `test_service_schema_isolation.py`). A new schema with `from_dto` must be
  registered there or the pairing test fails.
- `test_service_layer_does_not_depend_on_api_schemas` — AST scan: the layers listed in
  `MIGRATED_LAYERS` never import `<service>.api` or `core.schema.v<N>`. Add a service there when
  it is migrated.
- Router behaviour is not covered by the OpenAPI snapshot, so each service also has
  `tests/<service>/test_<service>_api.py` (real JWTs and the real routers through
  `tests/support/http.py`: `api_client`, `principal`, `bound_sessionmaker`) and
  `test_<service>_filters.py` (`exercise_filter` runs every filter field against the database,
  `assert_dto_parity` and `assert_ordering_documented` guard the filter↔DTO and `order_by`
  contracts). Add an API test for every new endpoint or PATCH/PUT conversion. Test module
  basenames must be unique across `tests/`, hence the service prefix.
- A service-layer change (new DTO field with a default, refactored service, renamed internals)
  must leave every contract test green **without regenerating anything** — if one fails, the
  change leaked into the API. Renaming or removing a DTO field a schema reads, or adding a
  required DTO field a request schema cannot fill, fails by design.
- A released version is frozen: never "fix" a failing contract test by regenerating its snapshot.
  A deliberate change is a new `v<N+1>`; only pilot/pre-release work may regenerate with
  `UPDATE_CONTRACTS=1 uv run pytest tests/contract` and must review the resulting file diff.

## Frontend design code (`frontend/`)

The UI has one design language and agents extend it instead of reinventing it. Before writing
markup or CSS, find the piece that already exists; a screen that looks different from its neighbours
is a defect, not a style choice.

- **Tokens** — `frontend/src/theme/variables.css`: brand and surface colours (Ionic variables, light
  and `.ion-palette-dark`), the type scale `--fs-2xs … --fs-2xl` (11/12/13/14/16/18/22px), weights
  `--fw-regular|medium|semibold|bold` (400/500/600/700), icon sizes `--icon-xl` (28px) and
  `--icon-hero` (40px, empty and error states), radii `--radius-sm|md|lg|xl|pill`
  (10/12/16/20/999px), `--border-w` (1.5px) and `--font-mono`; for fields `--field-h` (48px),
  `--field-pad-x` (14px) and `--field-border` (a step stronger in the dark theme). The font is
  `Inter Variable`, bundled from `@fontsource-variable/inter` and loaded in `main.ts`.
- **Primitives** — `frontend/src/theme/components.css`, loaded once from `main.ts`: the field
  (`ui-field` and its parts: `ui-field-box`, `ui-field-label`, `ui-field-outline`, `ui-field-control`
  for the native `input`/`textarea`/`select`/`ion-select` inside it, `ui-field-value` for a value that
  is not typed, `ui-field-foot`; `ui-field-title` for the heading of a group of controls and
  `ui-toggle-row` for a switch), `ui-menu` and `ui-menu-item` (a list of options under a field),
  `ui-icon-btn` (+ `--primary`, `--danger`, `--active`), `ui-chips` and `ui-chip` (+ `--active`),
  `ui-btn` (+ `--primary`, `--ghost`); the dialog parts `ui-sheet`, `ui-sheet-head`, `ui-sheet-title`,
  `ui-sheet-body` (scrolls) and `ui-sheet-actions` (buttons pinned under the body); the thin 6px
  scrollbar for every scroll area, including the one inside `ion-content`; and the reset that makes
  `button`, `input`, `select` and `textarea` inherit the page font.
- **Dialogs** — `ion-modal` is styled once in `variables.css` (radius, shadow, width) and so are
  the header and close button of a modal built from `ion-header`/`ion-toolbar`, which therefore look
  like `ui-sheet-head`. A dialog with its own header uses the `ui-sheet-*` parts, with the close
  button as `ui-icon-btn` and the primary action in `ui-sheet-actions`, not inside the scrolling body.
- **Fields** — `common/UiField` draws the box, the border with the label on it (the label sits inside
  an empty field, floats onto the border with a gap cut in it on focus or when there is a value, and
  is always floated where something is always shown), the error, hint and counter lines and the
  `prefix`/`suffix` slots. On top of it: `UiInput`, `UiTextarea`, `UiSelect` (`ion-select` with the
  popover), `UiNativeSelect` (a native `select`, for compact filters), `PasswordField`,
  `DateTimeField`, `EntityPickerField` (search a reference, shows the pick as a value),
  `admin/SearchPicker`, `geo/LocationField` and `geo/AddressSearchSelect`.
- **Shared components** — `frontend/src/components/common/` and friends: `DateTimeField` (built on
  `TimeSpinner` and `TimeDrum`), `TimestampsMeta`, `event/StageFields` (one stage of an event, used
  by the create form and the event page), `admin/ResourceTable` and `admin/ResourceFormModal` for
  admin lists and forms. New screens compose these.

Rules:

- **Reuse first.** Search `theme/` and `components/common/` before writing a style. If a primitive
  almost fits, add a modifier class to it; do not copy it into a view.
- **No second copy.** A style that is needed in two places belongs in `components.css` or a shared
  component. A component's own `<style>` holds layout and positioning specific to it, not its
  buttons, chips, fields, headers, scrollbars or colours.
- **No raw values.** `font-size` and `font-weight`, radii and border widths come from the tokens,
  colours from the Ionic/brand variables (`--ion-color-primary-contrast` rather than `#fff`), and
  `font-family` is never declared (it is inherited; `--font-mono` is the only other face). A size
  that is not on the scale (15px, 17px, 10px, `rem`/`em`) is a defect: use the nearest step, 14px
  for field text, 16px for the main text of a list row, 18px for a title.
- **Overriding Ionic** needs a selector at least as specific as Ionic's own (its component rules are
  scoped with a class); chain `.button.button-clear` and `[slot="icon-only"]` as `variables.css`
  does, not `!important`.
- **Icon-only buttons** are transparent at rest and tint on hover (`ui-icon-btn`); a permanent
  fill is not part of the language.
- **Labels live on the border.** Every input has its label on the border of the field through the
  field components above, never in a `<label>` or a heading over it, and its placeholder is a hint
  that shows once the label has floated (do not repeat the label in it). Do not use `ion-input`,
  `ion-textarea` or `ion-item` as a form field: their Material highlight and scoped padding are what
  made the old fields crooked. A new kind of control goes inside `UiField` (give the control the
  `ui-field-control` class, or put its content in `ui-field-value`) instead of getting its own border.
  A heading over a group of controls (`План мероприятия`, `Роли`) is `ui-field-title`. A message about
  a field (error, hint, counter) goes in its `error`, `hint` and `counter`, not in a `<p>` next to it.
- **Dates and times** go through `DateTimeField` only: typeable, with the `ДД.ММ.ГГГГ ЧЧ:ММ`
  template always visible, and a picker with a calendar and the two-drum `TimeSpinner`. Never use
  `<input type="date|time|datetime-local">` and never give such a field a placeholder text. A field
  may be given `suggest` (a date or a datetime): on focus it prefills the date of the suggestion, and
  a time is never filled in on the user's behalf. A new stage's start suggests the previous stage or
  the event date, and its end suggests the start.
- **A new primitive** is added to `components.css` and to the list above in the same change.
- **Check what you built** in the light and the dark theme, at phone width (375px) and on a desktop,
  with `npx vue-tsc --noEmit`, `npx eslint <files>` and `npx vitest run`.

Known debt, to be paid when a view is touched and not as a drive-by: per-view copies of `.auth-btn`
(6 files), `.sort-btn` (3), `.lcf-btn` (the `ui-btn` look), `.icon-btn`, `.form-field` (now only a
wrapper of a group), the search boxes of the list toolbars (`.ev-search`, `.rt-search`, `.pm-search`,
three copies of one control) and raw radii and borders (`12px`, `999px`, `1.5px`) in the views.

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
- Do not run `ruff format` or `ruff check --select I --fix` over a package: the code is not
  format-clean, and it rewrites files unrelated to the change. Edit only the lines you change.
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
- Backend checks: `uv run pytest`, `uv run ruff check .`, `uv run basedpyright`.
  `tests/conftest.py` sets defaults (`os.environ.setdefault`, so a real env var wins) before any
  import: `DB_DBMS=postgres` on `localhost:5433`, `MONOLITH=true`, `IN_MEMORY_BROKER=true`,
  `GEO_LIVE_FETCH=false` and dummy S3 credentials. Only tests that request the session fixture
  `test_database` need Docker: it starts `docker-compose.test.yml` (PostGIS) and migrates every
  service database (geo, notify, bot and the event location test do; unit tests, `tests/core` and
  `tests/contract` do not). New tests should not need a database unless they exercise SQL.
- **Lint/type-check are strict by config, not by current codebase state.** `[tool.ruff.lint]`
  selects `E, F, I, UP, B, SIM, C4, RUF, ASYNC, N` (not just the bare `E, F, I` this repo started
  with); a full run has ~300 pre-existing, non-auto-fixable findings that are accepted debt, not
  something to silently "clean up" as a drive-by in an unrelated change. `[tool.basedpyright]` sets `typeCheckingMode = "strict"` — `basedpyright` (a pyright
  fork; replaced plain `pyright` specifically for this feature) supports a baseline file,
  `.basedpyright/baseline.json`, that grandfathers every finding that existed when it was
  generated (currently ~3800, covering the whole repo — `src/`, `tests/`, `migrations/`,
  `scripts/` — matching the bare `uv run basedpyright` command's own default scope, not just
  `src/`), so a clean `uv run basedpyright` run means **zero new findings**, not zero findings
  ever. Consequences for how you work:
  - A file you touch may still show pre-existing ruff/basedpyright findings outside the lines you
    changed — that's expected, not a regression to fix unless asked.
  - If your change introduces a genuinely new finding (in a new file, or a line the baseline
    doesn't cover), both tools report it normally — the baseline only suppresses what was already
    there, it does not go slack for new code.
  - If you fix something that happened to be in the baseline, regenerate it (`uv run basedpyright
    --writebaseline`, no path — matching the bare check command's scope) in the same change so the
    fix is actually reflected, rather than leaving a stale baseline entry pointing at code that no
    longer has the problem.
  - Regenerate the baseline against a fully-synced environment (`uv sync --all-groups`) — a
    partially-installed venv (e.g. missing one service's extras) produces spurious
    "type is unknown" findings from unresolved imports that have nothing to do with real type
    errors, and poisons the baseline with noise specific to that venv.
  - **`ruff --fix` is not blindly safe here, even for "safe" fixes** — two of its rules have
    already produced real regressions once, caught only by re-running `basedpyright` afterward:
    `N805` renames a `@declared_attr` method's first parameter `cls` → `self` (SQLAlchemy's
    declarative-attribute convention genuinely wants `cls` there — this isn't a real instance
    method; see `core/database/sqlalchemy/mixins/models.py` and `geo/models/spot.py`, both now
    `# noqa: N805`), and `UP046`/`UP047` (the PEP 695 `class Foo[T]`/`def f[T]` rewrite) can drop
    an existing `TypeVar` bound if the original bound lived on a *different* module-level
    `TypeVar` than the one actually substituted in (`core/broker/rpc.py`'s `rpc_respond` lost its
    implicit `bound=BaseModel` this way). After any `ruff check --fix` that touches rule categories
    beyond plain `E/F/I`, re-run `basedpyright` before trusting the result — ruff's lints don't
    know this codebase's SQLAlchemy/pydantic conventions, only Python's.
- After adding/changing a migration: `uv run alembic -n <service> upgrade head` against the local
  dev Postgres (`docker compose up -d pg`).
- Frontend (submodule): `npx vue-tsc --noEmit`, `npx eslint <files>`, `npx vitest run`; regenerate the API client
  with `npm run generate` (fetches the schema from a running backend, then runs Orval) after a
  backend contract change — don't hand-edit the generated client as a substitute for regenerating
  it, only as a stopgap when the backend isn't runnable.

## Where things are documented

- Some services carry their own design docs worth reading before touching them, e.g.
  `src/notify/ROADMAP.md` and `src/notify/TECH_TASK.md` (notify's transport-plugin architecture
  and explicit scope boundaries — what notify does and deliberately does not own).
- This file: process and cross-service convention only, not what any single service does — check
  that service's own code/docs for its business logic.
