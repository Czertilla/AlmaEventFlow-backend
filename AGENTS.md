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
- `docker-compose.yml` runs **one deployment mode at a time**, a compose profile: `monolith` (`aef`
  at the bare API host) or `microservices` (`user`, `mail`, `profile`, `event`, `org`, `geo` and
  `notify`, Traefik `PathPrefix('/<service>')`). The choice is global:
  `COMPOSE_PROFILES=monolith|microservices` in `.env`, or `scripts/deploy.sh --mode <mode>`.
  Infrastructure (`pg`, `kafka`, `redis`, `frontend`, `traefik`, `status-page`) always runs; a bare
  `docker compose up` therefore starts no application. Two things never start by themselves, each
  in its own opt-in profile: the Telegram `bot` (it is not in the monolith and usually runs on
  another host than Kafka, so a second copy would fight over the same updates) and `kafka-ui`
  (profile `tools`: it publishes port 8088 without a password). Name them (`up bot`), put them in
  `COMPOSE_PROFILES` (`monolith,bot`) or pass `scripts/deploy.sh --with bot|tools`. Separate
  processes cannot share an in-memory broker, so every microservice block forces
  `IN_MEMORY_BROKER=false` (Kafka coordinates still come from `.env`). The aggregated OpenAPI
  (`/openapi.json`) exists only in the monolith. New services get their own container block
  mirroring an existing one (`notify`'s is a good template, with `<<: *microservice`) and are wired
  into the monolith too.
- Every HTTP service serves `GET /<service>/v1/health` (`router/health.py` =
  `health_router("<service>")` from `core/api/v1/health.py`, a liveness probe with no DB access)
  and its compose block probes it through `core/utils/healthcheck.py` (the slim image has no
  curl). The `aef` container probes `/user/v1/health` only: the monolith mounts every service's
  router. `tests/contract/test_compose_healthchecks.py` checks each probe path against the service's
  contract snapshot.
- **Outage and maintenance pages are Traefik's job, in three layers** (all covered by
  `tests/contract/test_compose_proxy.py` and the Docker tests in `tests/proxy/`):
  1. A container that runs but fails its probe: Traefik probes `/<service>/v1/health` itself
     (`loadbalancer.healthcheck.*` labels, 3 s, 1 s once unhealthy) and each router points at
     `<service>-guarded@file`, a `failover` service in `docker/traefik/dynamic/failover.yml` whose
     fallback is `outage@docker`. `--providers.docker.allowEmptyServices=true` keeps the router of
     an unhealthy container alive, and a failover needs every descendant probed, so the fallback
     has its own `/healthz` probe.
  2. A container that is stopped or removed: its router disappears, so the priority-1 `outage`
     router (every service prefix on the API host, and the frontend host) answers instead.
  3. Planned work: `scripts/deploy.sh maintenance on|off|status` starts the `maintenance` container
     (profile `maintenance`), whose priority-1000000 router answers every API-host request.
  The pages (`docker/status/`) are nginx behind envsubst: HTML for browsers, JSON
  `{status: "unavailable"|"maintenance", message, retry_after}` for the SPA, status 503 with
  `Retry-After`, and CORS headers for the known origins, because a CORS-less body is invisible to
  the browser. Do not replace the failover with an `errors` middleware by status: the apps return
  503 on purpose (`WEBPUSH_NOT_CONFIGURED`, `TELEGRAM_BOT_NOT_CONFIGURED`) and only the failover
  tells Traefik's "no healthy server" from the app's own 503. A container that is just starting can
  answer 500 for up to one probe interval; a planned deploy hides that behind the maintenance mode.
  A new routed service needs the healthcheck labels, a `<service>-guarded` entry and its prefix in
  the `outage` rule.
- `scripts/deploy.sh` builds the images while the old version still serves, switches the
  maintenance mode on, removes the other mode's containers, runs `up -d --wait`, and lifts the
  mode; if anything fails after it went on, it stays on. `--no-maintenance` and
  `--keep-maintenance` change that. Without `--mode` the mode and the extra profiles are whatever
  compose itself resolves from `COMPOSE_PROFILES` (shell or `.env`), so the script never
  overrides them; a bot or `kafka-ui` that is already running is left alone. The Docker tests need local images (`PROXY_TEST_TRAEFIK_IMAGE`,
  `PROXY_TEST_NGINX_IMAGE`) and skip themselves without them; they never pull.
- The frontend probes the same endpoint (`frontend/src/api/availability.ts`,
  `composables/useBackendStatus.ts`). A failed request is only a suspicion: the browser also
  reports a 500 without CORS headers as a network error, and a flaky link drops single requests,
  so a service counts as down only after three health probes in a row stay silent
  (`verifyReachable`); never mark it down from one request. The 503 pages of Traefik
  (`{status: "maintenance"|"unavailable"}`) are the exception: they are an answer of the
  infrastructure, so `probe` returns them as a `reason`, the service goes down at once and
  `utils/backendCopy.ts` picks the wording of the banner and of `/unavailable`. **Only a 401 on
  `/user/v1/auth/jwt/refresh` ends a session**; a network error, 5xx or a proxy 404 leaves it
  intact (`tryRefresh` answers `unknown`, the guard waits on `/unavailable`). There is exactly one
  refresh at a time (`refreshAccessToken`): the backend revokes the whole session when a used
  refresh token is presented again.
- **Signing keys are a start-up requirement, there is no fallback.** The access tokens are RS256;
  `create_jwt_auth` reads `RSA_PUBLIC_KEY_PATH` through `core.utils.keys.read_key`, which logs CRITICAL
  and raises `KeyMissingError` while the service imports its dependencies, so a service that verifies
  tokens does not start without the public key (the microservice images carry none: mount it). `user`
  makes its own pair only in the monolith (`ensure_access_keys`, also run first by `aef/__init__.py`,
  before any router builds a verifier); outside the monolith missing keys stop it. A shared secret
  never stands in for a key: `USER_SECRET` is gone, `PASS_SECRET` signs only the verification and reset
  tokens that `user` itself reads.
- `frontend/` is a **git submodule** (Ionic Vue) — treat it as a separate deployable; its API
  client (`frontend/src/api/generated/`) is Orval-generated from `frontend/api_schema/openapi.json`.
- `migrations/` is shared: one Alembic environment, but `alembic.ini` has a `[<service>]` section
  per service (`script_location`, `version_locations = migrations/versions/<service>`,
  `database_name`), and `migrations/env.py` picks the target service from `-n <service>` and does
  `__import__(f"{service}.models", fromlist=["*"])` — every service needs a `<service>/models/`
  package (not `model/`, singular, which is just where the ORM classes live) that re-exports every
  ORM class, or autogenerate/upgrade silently sees no tables. Run migrations with
  `alembic -n <service> upgrade head`; new revisions go under `migrations/versions/<service>/`.

## Profile (`src/profile`)

- **`profile` owns the link of an account with its person** (`person_account`: `person_id` primary
  key, unique `user_id`). `user` still signs the JWT (`sub`/`per` carry `person_id`) and every other
  service trusts it; `user` follows profile through the state event `person-link-changed`
  (`PersonLinkData`, `user/api/kafka/sub/link.py`, `UserService.apply_link`), which upserts its
  `person` projection, moves the person off another holder and announces `account.updated`. Profile
  reads the identity of the caller for personal data from its own table (`CallerPersonDep`,
  `RequiredPersonDep`); a JWT whose `per` disagrees makes it announce the link again (throttled,
  `PersonAccountService.announce`), and a person the token claims but profile has no link for is a
  409 `ACCOUNT_LINK_OUT_OF_SYNC`. The event goes out once per account, keyed by `user_id`
  (`on_person_link_changed`), so Kafka keeps the events of one account in order. `user` applies it
  asynchronously: after the first save of a profile the UI asks `GET /user/v1/users/me` until the
  account shows the person (`auth.refreshWhenLinked`, 3 s at most) and only then refreshes the token,
  or the new token would come without `per`.
- `user` asks profile for a link over `rpc.profile.link-account` (`LinkAccountRequest`; `replace` is
  the admin relink). Registration with an invite still succeeds when profile does not answer (the
  account stays unlinked, a warning is logged); the endpoints that need the link answer 503
  `PROFILE_SERVICE_UNAVAILABLE`. `POST /profile/v1/persons` is superuser-only and deleting a person
  announces the unlink first. **Run `python -m profile.bootstrap.links` once before profile serves**:
  it copies the links the user database already has; nothing runs it by itself.
- **An invitation is profile's**: `POST /profile/v2/persons/{person_id}/invite` (superuser) checks its
  own `person` and `person_account` (404 `PERSON_NOT_FOUND`, 400 `PERSON_ALREADY_HAS_ACCOUNT`). The token
  (a person id, RS256, `iss=profile`) is signed with `profile`'s own key pair and read with its public
  key by `core/utils/invite.py` (the algorithm is fixed on both sides). **A service that signs what
  another service verifies has its own RSA pair: the private key stays on its host, the verifiers get
  the public one** (`user`: `RSA_*_KEY_PATH` for access tokens, `profile`: `PROFILE_RSA_*_KEY_PATH` for
  invitations); a shared HMAC secret such as `USER_SECRET` is never the way to sign for someone else.
  `profile` checks its pair when it mounts its routers (`ensure_invite_keys`): the monolith makes the
  pair when there is none, outside the monolith a missing or half a pair stops the start; `user` outside
  the monolith needs the public key at start. In microservices mount the private key into `profile`
  only and the public one into `user`. A key that vanishes later is 503 `INVITE_SIGNING_NOT_CONFIGURED`
  and `user` accepts no invitation. `user` only redeems it: registration with `invite_token` and
  `POST /user/v1/users/me/link-invite` read it with the same helper, pre-check their own projections to
  fail before an account is made, and leave the authoritative link to `rpc.profile.link-account`. The
  old `POST /user/v1/users/invite` is gone; `PATCH /user/v1/users/{id}/person` (admin relink) is still
  `user`'s thin proxy over the same RPC.
- **Every change of the link is kept** in `person_account_history` (append-only; no FK, so a row
  outlives the person): the account (`user_id`), `old_person_id` and `new_person_id`, the `action`
  (`linked`, `replaced`, `unlinked`, derived from the two ids by `PersonLinkAction.of`), the `source`
  (`core.enum.profile.PersonLinkSource`: `own_profile`, `invite`, `admin`, `person_deleted`,
  `bootstrap`), `actor_id` (the account that asked, none for the system) and `created_at`. It is
  written in the transaction of the change by `PersonAccountHistoryRepo.record` (`_link`,
  `MyProfileService.create`, `PersonService.delete`, the bootstrap job), so a new code path that
  touches `person_account` must record too. `LinkAccountRequest` carries `source` and `actor_id`;
  `user` fills them (the account itself for an invite, the admin for a relink). A repeated request
  that changes nothing and a refused one leave no row. A trigger rejects `UPDATE` and `DELETE` of its
  rows (`TRUNCATE` and the owner of the table, who can drop the trigger, are not stopped). Superusers
  read it at `GET /profile/v2/account-links/history` (newest first; filters `user_id`, `person_id`,
  which matches either end of a change, `actor_id`, `action`, `source`, `created_at__gte|lte`). The
  history of access to sensitive data is meant to sit next to it.
- **The own profile is one aggregate**: `GET/POST/PUT /profile/v2/profiles/my` (`MyProfileWrite`,
  `MyProfileRead`, `service/my_profile.py`) writes person, profile, student card, diet, workplace and
  contacts in one transaction. A second `POST` is 403 `PROFILE_ALREADY_EXISTS`. `PUT` replaces: a
  contact that carries its `id` is kept, one left out is deleted, `student: null` removes the card.
  Every contact type has exactly one main contact (`main_flags`). The user's UI knows an account and a
  profile, never a person.
- **Reference find-or-create** (`POST /profile/v2/{universities,faculties,student-degrees,
  student-groups,diets,organizations}`, `service/reference.py`): a row is the same one when its
  normalised name is (`core.utils.names.normalize_name`, case-insensitive), a group within its
  faculty, a faculty within its university. University, faculty and organization belong to `org`, so
  profile asks it over `rpc.org.*` (`OrgRPC`, `org/api/kafka/sub/reference.py`) and projects the answer
  into its own `organization` table; `ensure_organizations` fetches a missing one lazily
  (`get-organization`). The UI sends its drafts only on submit, so an abandoned form leaves nothing.
  Any verified user may create them, except a degree: `student-degrees` is superuser-only, a profile
  only picks one (the administration sets them, later an integration with the university systems).
  The only dedupe is the name (no unique index): watch it for spam.
- **The student catalog is managed by superusers** at `/profile/v1/students/{degrees,groups}` (CRUD;
  reads are open to verified users). Names are normalised and unique (a degree by name, a group within
  its faculty: 409 `STUDENT_DEGREE_ALREADY_EXISTS`, `STUDENT_GROUP_ALREADY_EXISTS`), a degree that has
  groups and a group that has students are not deleted (409 `STUDENT_DEGREE_IN_USE`,
  `STUDENT_GROUP_IN_USE`), a missing one is 404 `STUDENT_DEGREE_NOT_FOUND` / `STUDENT_GROUP_NOT_FOUND`.
  The faculty of a group is projected from `org` as in the find-or-create (`StudentGroupUOW`,
  `ensure_organizations`). The new codes are not in the v1 OpenAPI (a released schema); the admin UI
  words them (`utils/apiErrors.ts`). The student detail routes are `/{student_id:uuid}`: registered
  before `degrees` and `groups`, a plain `{student_id}` swallowed `GET /students/degrees|groups` (422).
- The old `/my` endpoints stay: v1 for person, profile and contacts, v2 `/profile/v2/students/my` for
  the student card. Passports stay for superusers until their storage and encryption are designed.

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
- A UoW class declares its repositories as type hints; `BaseUOW.__aenter__` instantiates them, so
  `self.uow.<name>` exists only inside `async with uow`. A service never constructs a repository
  (`PartnerRepository(uow.session)`-style code is wrong) and never runs `select()`/`update()`
  through `self.uow.session`: a query is a repository method (`add_entity` stores an ORM
  instance). A service that needs another repository uses a composed UoW (`EventComposeUOW`).
- `org`'s collective, faculty, university and organization services share `OrgEntityService`
  (`org/service/base.py`); a subclass only names its model, DTO, filter, not-found exception and
  UoW repository. Fire-and-forget `asyncio` tasks go through `core.utils.tasks.track`, or the loop
  may garbage-collect them.
- `/event/v1/me/collectives/{collective_id}/...` routes that take a member, role, attendance or
  participation id depend on `verify_*_of_collective` (`event/dependency/principal.py`), not on
  `verify_collective_principal` alone: the principal must not reach another collective's rows.

## API layer, DTOs and schema versioning

Every HTTP service follows this: `event`, `org`, `geo`, `profile`, `notify`, `bot` and `user`
(`mail` serves only its health endpoint over HTTP). A new service copies the shape of `org` (simple CRUD) or `event`.

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
- Filters reach across relations on purpose: `IdentityFilterMixin` (`id`, `id__in`) on every
  resource an admin page links to, `RelatedSearchFilter.Constants.search_paths` lets `search` match
  columns of related rows (a chain walked through `has()`: an attendance is found by the person's
  name, the collective or the event), and an attendance is narrowed by `collective_id`, `event_id`
  and `person_id` through its participation and member. `MemberFilter` hides inactive members unless
  `include_inactive=true`; `is_active` alone cannot say "any". A filter DTO that has `id` extends
  `IdentityFilterDTOMixin`, which already carries the timestamp fields (two slotted dataclass bases
  cannot be combined). A field a filter resolves itself is set to `None` around `super().filter()`
  and restored after: `fastapi_filter` would look for it as a column.
- List endpoints sort and filter through `core/filter/`: `OrderedFilter` accepts only the fields in
  `Constants.order_fields` (anything else is a 422, and the allowed fields are listed in the
  `order_by` description), `TimestampFilterMixin` adds `created_at__gte/lte`, `edited_at__gte/lte`
  and `edited_at__isnull`, `RelatedSearchFilter` extends `search` over one related row with an
  `EXISTS`. `search` also finds a row by its id (`OrderedFilter._search_clauses`,
  `core.filter.identity.id_search_clause`): a whole uuid, the start of one (6+ hex characters) or a
  whole number for an integer key, so no list of an admin page needs a second box for it. A sort key that is not a model column (event `status`/`level`/`type`, ordered by the
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

## Page aggregates (`src/event`, API v2)

- **A page loads with one request.** v1 is the CRUD of one resource, meant for the administration;
  what a screen shows is read through v2 read models that join the pieces on the server. Never add
  an N+1 on the client (a request per row, per member name, per location): the data is already in the
  service's own tables (`person`, `organization`, `location`, `member`, `role`, `event_stage`
  projections), so one query can carry it. A new page gets its own read model next to the others.
- The read side is `ViewRepo` (`event/repository/view.py`, read-only queries, no transactions of its
  own) behind `ViewUOW`, and four services: `FeedService` (`/v2/me/context`, `/v2/feed`,
  `/v2/feed/cards`, `/v2/feed/pending`), `EventPageService` (`/v2/events/{id}`),
  `CollectiveViewService` (`/v2/collectives/{id}/roster|events|attendance-matrix`, leader and
  superusers only through `verify_collective_principal`) and `AttendanceChangeService`
  (`PATCH /v2/attendances/{id}`). `viewer_context`/`roster_of` (`service/viewer.py`) and `read_window`
  (`service/window.py`) are shared by them.
- **Windows are keyset-paged, not offset-paged.** `direction=around|past|future` with an `anchor` day or
  an opaque `cursor` (`date|id`, base64) of the previous answer; `limit` is per side, `has_more_*` is
  exact (`limit + 1` rows are read), a change between two requests neither repeats nor skips an
  event. The order is `(date, id)`; events without a date are not in a window. List parameters
  are repeated keys (`status=a&status=b`): the frontend sets `axios.defaults.paramsSerializer =
  { indexes: null }`, so the generated client needs no per-call option.
- **Visibility is decided on the server.** Everybody sees `active` events; any other status only the
  leaders of the collectives taking part (and superusers); a template is never in a window and only
  a leader opens its page. The places of a collective (names, marks, comments, roles) go to its
  leader, its members and superusers; counters are `null` for anyone else.
- **An unmarked place is `is_attended: null` in v2 reads and nowhere else.** The column is `NOT NULL`
  (`false` by default), so every v1 schema and DTO, the admin endpoints, the EDA events and the filters
  see `true` or `false`. `shown`/`shown_attendance` (`service/attendance_stats.py`) turn the stored
  value into `null` for a place that was never edited and is not verified (`MARKED` in `ViewRepo` is
  the same rule in SQL), and every v2 answer that carries a place goes through them. The client never
  works it out (no `edited_at` check): "not marked" is exactly `is_attended == null`. A new place is
  declared with `POST /v2/attendances`, whose answer already has that shape; the v1 `me` endpoint
  answers with the stored value.
- `GET /v2/me/context` is the whole picture of an account at start: collectives it leads or belongs to,
  with names, `is_verified`, the membership and its roles. The frontend asks once per minute and
  account (`principal.fetchCollectives`, `force` to skip the cache) and never fetches a collective by id
  or `/me/members` any more.
- A card (`EventCard`) carries the place, the time (first and last stage), the caller's own places and
  the counters of their collectives. `PATCH /v2/attendances/{id}` answers with the changed place and the
  counters of its participation, the frontend patches its store (`applyAttendanceChange`) and
  loads nothing. The member of the place may mark and comment until it is verified; the leader of the
  collective and superusers may set anything, `is_verified` included.
- **What the live updates of 0.5.1/0.5.2 (SSE or long polling) can rely on, and what they cannot:**
  rows have stable ids and every response of a mutation has the shape of the aggregate it changes, so
  a push can carry the same `AttendanceChanged` or only "event X changed" and the client re-reads
  `GET /v2/feed/cards?id=...` (a batch, any number of cards, one request). `EventCard.updated_at`
  (`max(event.edited_at ?? created_at, the latest change of a place of its participations)`) is the
  version to compare two copies by (`eventCalendar.upsertCards`). It does **not** move when a place is
  deleted or a member leaves: a push needs a tombstone (`deleted`, id) for those, and polling by
  `edited_at` alone would miss them. The in-memory broker lives in one process (`--workers 1`); a
  second worker needs Redis pub/sub or Kafka for the fan-out.

## Collective confirmation (`src/event`)

- A collective is confirmed by the administration, and **event owns that flag** (`collective.is_verified`,
  the projection of org that event enforces: a leader of an unconfirmed collective cannot create events,
  `403 COLLECTIVE_NOT_VERIFIED`; a superuser can). org knows nothing of it: a new collective starts
  unconfirmed and the flag is never sent in an organization event, so a rename in org cannot reset it.
- `GET /event/v1/collectives` (superusers; filters `is_verified`, `search` by name, `principal_id[__in]`,
  `id[__in]`, order `name|is_verified`) and `PATCH /event/v1/collectives/{id}` with `{is_verified}`. The
  admin page of collectives lists org's rows and asks `id__in` of event for the flags (two requests); its
  `Подтверждён` filter first takes the ids from event, then asks org for them. The field is hidden in the
  creation form: event learns of a new collective from the organization event, a moment after it.

## Collective profile (`src/event`)

- `GET /event/v2/collectives/{id}/profile?date_from&date_to` is the member profile of a whole roster
  (`service/collective_profile.py`, the same period rules and `COUNTED_STATUSES` as
  `service/member_profile.py`; rows come from `AttendanceRepo.collective_history`, mapped by the shared
  `attendance_stats.to_item` and rolled up per day, event, month, type and member). Access is the
  leader, the active members and superusers (`403 NOT_COLLECTIVE_MEMBER`); `can_manage` is the leader
  and superusers. A place is a declared attendance row of the collective's participation, so an event
  nobody was declared to does not appear. The member list holds the active members and the former ones
  who have rows in the period. `rate` of the summary and of a member is `attended / past` (unmarked
  count in `past`), while the UI colours a day by `attended / (attended + absent)`.

## Org (`src/org`)

- University, faculty and collective are joined-table children of `organization` and are written
  through ORM instances (`OrgEntityService`). A delete goes through the parent row
  (`SQLAlchemyRepository.delete_entity`): a Core `DELETE` of the subtype leaves the `organization` row
  typed `university` behind, an «university» with no row in `university` that cannot take a faculty
  (migration `c4e1b7a92d35` gave such orphans their rows back).
- A faculty or a collective points only at a `university` row: any other id is 404
  `UNIVERSITY_NOT_FOUND`, not a foreign key error (`UniversityLinkedService`). A university that still
  has faculties is not deleted, by the typed endpoint or by `DELETE /organizations/{id}`: 409
  `UNIVERSITY_HAS_FACULTIES` (the `ON DELETE CASCADE` of `faculty.university_id` would remove the
  `faculty` rows and leave their organizations behind). `POST /organizations` makes a plain
  organization whatever `type` it is sent. The admin pickers list universities and faculties through
  their own endpoints, never by `organization.type`.

## Geo (`src/geo`)

- **`address.name` is the clean address, `address.locality` the place line** ("Москва, Россия";
  city, then region and country only when they differ from the names before them,
  `geo/locality.py`). `AddressAlchemyRepo` writes `locality` from the city on every write that
  carries a `city_id` (`_prepare`), so API, cascade, bootstrap and live fetch need no code of their
  own; a city rename is not propagated. Never put it into a trigram index: every row of a city
  shares its trigrams and the index prunes nothing (a typo'd city name rechecked all rows, ~3 s per
  300k). The typo filter looks at `name`, `locality` only ranks the few survivors.
- Text search (`geo/search.py`): the morphological stage matches `address.search_tsv` (name weight
  A, locality weight C) with a cheap rank (`ts_rank` + exact-stem bonus); trigram scores cost ~10x
  per row and rank only the fuzzy stage, which `search_ranked` also caps (`FUZZY_CANDIDATES`).
  `search_page` (paginated, v1) and `search_ranked` (top-N with a score and a bias to a point, v2)
  share the two stages.
- **v2 is additive**: `GET /geo/v2/search` (typeahead over addresses and named locations, flat
  ranked list with a `kind` discriminator, no pagination), `GET /geo/v2/map` (GeoJSON, below) and
  `GET /geo/v2/{addresses,locations}/{id}`. v1 CRUD stays on v1; the v2 read models are
  `AddressReadV2`/`LocationReadV2` (the suffix keeps OpenAPI component names apart in the monolith).
- **External search** (`SearchService`, `service/external.py`, `geocoder/`): a provider is asked
  **outside any DB transaction** when fewer than `limit` local addresses match a query of 3+
  characters, or when the query names a house (`identity.query_house`) that none of them has.
  Photon (`GEO_PHOTON_URL`, houses only, `layer=house`) goes first; with `GEO_OVERPASS_SEARCH=true`
  Overpass (`geocoder/overpass.py`, street stem + house near the point, slow, default off) is asked
  next while the answer is still short, and its hits take their city from a stored address within
  `PLACE_RADIUS_M` (none near: dropped; the background live fetch fills a cold area). The named
  house comes first in the answer, wherever it was found. `ExternalSearch` is a TTL cache, a
  request budget (token bucket, `GEO_EXTERNAL_RATE` a second after a `GEO_EXTERNAL_BURST`, per
  process; a cached answer costs nothing), a 2-request cap and a circuit breaker per provider. A 429
  (`RateLimitedError`, `Retry-After`) pauses the provider for that long (60 s when it says nothing,
  at most 15 min). A failure is a `state` in the answer (`timeout`, `error`, `unavailable`,
  `throttled`), never an exception. `GEO_EXTERNAL_SEARCH=false` (tests) switches it all off.
  Nominatim is not an option, its policy forbids autocomplete.
- **Who may make geo call out**: typed text, and a point the user put on the map (`marked` in the
  frontend's `useGeoSearch`). A map that merely moves asks with `external=off`, and `external=off`
  also keeps the background Overpass fetch (`schedule_live_fetch`) from starting, as does a text
  with a bias point: only a point alone (a marker) or a found settlement starts it.
- **Around a point and settlement names** (`SearchService._around`, `_find_place`): with a point and
  no text the answer is the nearest stored places; when fewer than `limit` addresses lie within
  `NEARBY_ENOUGH_M` the provider lists the houses around the point (`NearbyGeocoder`, Photon
  `/reverse`, `NEARBY_RADIUS_KM`) and they are stored like any found address. No address farther than
  `NEARBY_MAX_M` is "around" (named locations stay). A short text without digits is first tried as a
  settlement (`PlaceGeocoder`, Photon `layer=city`, only when every typed word is a whole word of the
  name; a street of that name near the point wins, `layer=street`, 30 km): the answer is then the
  addresses nearest to its centre, `place` in the response says where it is, and the text search
  is skipped (Photon's `layer=house` answers a bare place name with shops of that name). A text
  that is a street some local hit already has is never a settlement. Both extras are optional
  capabilities of a geocoder (`runtime_checkable` protocols): one without them is `skipped`.
- **A found address is matched to a stored one before it is stored** (`SearchService._twins`,
  `geo/identity.py`): the same street and house (`address_key`: case, ё, street type and word order
  ignored) within `DUPLICATE_RADIUS_M` is the same address **whatever city it is filed under**
  ("Ростов" / "Ростов Великий"), so the stored row is returned and no city is created. Otherwise the
  row gets the `uuid5` id of the OSM import, so one in the same city collapses into it.
  `AddressAlchemyRepo.save_found` inserts a new row and refreshes a row of the **same `source`**
  (name, point, `synced_at`); an OSM or manual row is never rewritten by a provider.
  `resolve_city_loose` reuses a city whose region is spelled differently ("Татарстан" /
  "Республика Татарстан") but never merges across regions.
- **Photon rows age; `python -m geo.bootstrap.refresh`** asks the geocoder again for the rows not
  confirmed for `--older-than-days` (30) and, when the instance reports its build date (`/status`,
  `DatedGeocoder`), only for those confirmed before it. A found row takes the current data; a missing
  one is only reported. `--prune` deletes a row unseen for `--prune-after-days` (90) and a duplicate
  of another source's row, never one a location points at. `--delay` (1 s) is for the public Photon,
  use 0 for your own. Rerun it from cron; nothing runs it by itself.
- **Own Photon is optional** (compose profile `photon`, `scripts/deploy.sh --with photon`): the
  unofficial `rtuszik/photon-docker` image downloads the `PHOTON_REGION` index (default `ru`) on the
  first start and swaps in a fresh one every `PHOTON_UPDATE_INTERVAL` (`PARALLEL` keeps serving).
  It is internal (no port, no Traefik) and has no healthcheck on purpose: the first start downloads
  for a long time and `up --wait` would fail the deploy. Switch geo to it with
  `GEO_PHOTON_URL=http://photon:2322` in `.env`; the public instance stays the default. Disk and RAM
  of the `ru` index were not measured here: size `PHOTON_JAVA_PARAMS` and the volume from the image's
  README and watch the first start.
- **Locations that stand for less than a place.** An address-proxy location (`name IS NULL`, one
  per address, `find_or_create_address_proxy`, unique partial index) only attaches an address to an
  event: lists leave it out (`named_locations_only` in v2 search, `name__isnull=false` from the
  frontend on the v1 list, v2 map) and the UI shows it as the address. The fallback for a place with
  nothing on a map is a **text-only location**: a `name` and no address, no `spot` (`POST
  /geo/v2/locations` with a name alone; v1 still refuses it). The same text, whatever its case and
  spacing, is the same location (`find_or_create_text_only`). The UI copies the text or opens a map
  service with it as the search query (`MapLinkMenu` with `search`).
- **Other services see a location as `LocationData`**: the text to show (`display_name`) and where it
  is (`lat`/`lon`: its own point, else its address's; none for a text-only one), built by
  `location_to_data`. A moved or renamed address republishes the locations at it
  (`AddressService._tell_locations`). `event` keeps both in its `location` projection and puts them
  in the announcement (`location_lat`/`location_lon`); a row told about before the columns existed
  has no point until geo tells about it again.
- **Where a collective met lately** is `event`'s to say and geo's to describe: `GET
  /event/v2/collectives/{id}/recent-locations` lists the location ids of the collective's events
  (through its participations), the latest first, a place counted from its event's `edited_at`
  (`created_at` when never edited), once per place; address-only locations are included. For the
  collective's leader and superusers. The ids go to `GET /geo/v2/locations?id=…` (repeat `id`, up to 50),
  which returns the locations in the order given and skips an id that does not exist.
- **Map** (`repository/map.py`, `service/viewport.py`): the window is cut into cells of
  `radius_px` screen pixels in Web Mercator (arithmetic in SQL, no PROJ), one feature per cell: the
  place when it is alone, a cluster (`cluster: true`, `point_count`, `bbox`) otherwise. The answer is
  bounded by the cells that fit the window, not by data density, which is what keeps a zoomed-out
  window evenly filled. From zoom 17 nothing is clustered. Unnamed address-proxy locations are left
  out (the address is there). `west > east` is a window across the antimeridian (RFC 7946). The
  grouping uses `any_value` (PostgreSQL 16, as in `docker-compose.yml`) and carries only narrow
  columns; labels of single places come from a second query. Response media type is
  `application/geo+json`.
- The migration that adds `locality` rewrites `address` (about a minute per 300k rows).

## User (`src/user`)

- **Client settings are synced per account**: `GET/PATCH /user/v2/users/me/settings` (v2, so v1 stays
  frozen), one row per user in `user_settings` (`data` JSONB, `revision`, `ON DELETE CASCADE`). The
  client owns the names and the values; the server only bounds them (name `^[A-Za-z][A-Za-z0-9_.:-]{0,63}$`,
  at most 64 names per request, 16 KiB for the whole document, else 413 `SETTINGS_TOO_LARGE`).
  `PATCH` is a JSON merge patch over the top-level names (`null` removes one) under a row lock
  (`SettingsRepo.lock_for_user`: an `ON CONFLICT DO NOTHING` insert, then `SELECT ... FOR UPDATE`), so
  two devices changing different settings never overwrite each other and parallel first writes cannot
  both insert. A patch that changes nothing leaves `revision` as it was; `GET` of an account with none
  is `{values: {}, revision: 0}` without writing a row.
- **The client syncs through `composables/useSettingsSync.ts`** (started in `App.vue`) with the pure
  rules in `utils/settingsSync.ts`: `SETTING_GUARDS` lists the synced settings and checks every remote
  value (an unknown name or a wrong shape is ignored, so a newer app can keep its own names). The
  server wins for every setting this device did not change since the last sync; a change made here is
  `dirty` (kept in localStorage `settingsSync` with the owner account and the revision), sent after
  700 ms as one `PATCH` of only those names, and a failed send is retried at the next sync. Sync runs
  after sign-in and when the app returns to the foreground (`focus`, `visibilitychange`, `online`, at
  most every 20 s). Only settings the person picked on this device (they have their own localStorage
  entry, which is why `theme` is saved on change and not at start) seed an account that has none; a
  browser last used by another account sends nothing of what that account chose. A new synced setting
  is one more ref in `stores/settings.ts` plus its guard in `SETTING_GUARDS`.

## Telegram bot (`src/bot`)

- Handlers live in `bot/tg/api/router/{command,callback,chat_member,message}`; `load_common` picks
  up every package's `router` and sorts them by `Router.name`. The private-chat catch-all is
  `message/fallback.py`, so it has to stay the last message router.
- **Every answer depends on who is asking.** `ActorDep` (`bot/tg/dependency/actor.py`) resolves an
  `ActorDTO`: `unlinked`, `linked` (nothing attached yet), `member` or `leader`, plus
  `is_superuser`. `roles_known` is `False` when `event` did not answer — then never say the person
  has no collectives. A new flow must cover all four states and a group message from an anonymous
  admin or a bot, where `data["user"]` is `None`. `aiogram3_di` hands a dependency only the
  parameters that have **no default**, so a provider cannot take `user: TGUser | None = None`.
- `UserUpdateMiddleware` registers every human who interacts, not only those who sent `/start`
  (a person tapping a button in a group has never opened the bot). The username hint is private
  chat only, once a week, after the real answer.
- Texts are `res/locales/HTML.<lang>.yml`; `bot/enum/locales.py` is generated from the English
  file with `python scripts/generate_locales.py`, never edited by hand. Quote the keys `yes`, `no`,
  `on`, `off` (YAML turns them into booleans). Do not use `lang`, `key` or `markup` as a phrase
  placeholder: they collide with the parameters of `Localization.get`.
  `tests/bot/test_bot_locales.py` guards key parity, placeholders, Telegram limits and HTML tags.
- Callback payloads are aiogram `CallbackData` classes (`bot/tg/enum/callbacks.py`, at most 64
  bytes). Never name a `StrEnum` member like a `str` method (`replace`, `format`, …). Answer
  callbacks through the injected `CallbackAnswer`; `CallbackAnswerMiddleware` closes every one, so a
  hand-written `callback.answer()` is a double answer.
- Telegram shows only the most specific command scope, so each scope's list must be complete.
  Group chats use `all_group_chats` / `all_chat_administrators`; a private chat gets its own
  `BotCommandScopeChat` per role from `CommandMenuService.refresh(actor)`.
- A collective has one official chat and a chat belongs to one collective (both columns are
  unique). `CollectiveChatService.setup` requires the bot and the caller to be admins of the chat
  and the caller to lead the collective; settings (announcements on/off, silent, pin, update-notice
  detail, language) belong to the binding. An edited announcement is followed by a one-line
  "updated" reply by default; with `detailed_updates` the reply names the event and lists the
  changes (`build_update_notice`).
- The location line of an announcement is a link (`links.map_url`, Yandex Maps): the pin when the
  request has both `location_lat` and `location_lon`, else a search for the text. The URL is built
  from the clipped label, so it shrinks with the fit steps.
- Time in announcements is a `<tg-time>` entity (each reader sees their own zone); delivery falls
  back to plain text and to link-less buttons when Telegram rejects either. Ephemeral replies
  (`reply_to_sender`) are for hints and refusals only and fall back to an ordinary reply.
- **The text inside `<tg-time>` is a fallback the bot formats itself**, so it must not depend on the
  host zone: `core/utils/tz.py` (`as_aware`, `localize`) reads a naive datetime as UTC and shows it in
  the stage's `timezone`, else in `DISPLAY_TIMEZONE` (IANA name, unset = the value's own zone). The
  `unix` attribute comes from `as_aware(...).timestamp()`, never from a naive `.timestamp()`. The
  event service's text notifications go through the same helper; set `DISPLAY_TIMEZONE` for `bot` and
  `event` (or `aef`) when users live in one zone.
- An announcement is a **rich message** (Bot API 10.1, `sendRichMessage`; `build_announcement_rich`
  → `TelegramDeliveryItem.rich_html`): a stage is one `▫️ time <b>name</b>` line (the same
  `announcement.stage_line` phrase as the text fallback, time first so the ranges start at one
  place), the lines of a day are one `<p>` joined by `<br>`, and when the stages start on different
  days (grouped in the stage's own `timezone`) each day gets `<hr/>` and an `<h5>` with a
  `<tg-time format="wD">` instead of a date glued to every time; the one exception is a stage that
  ends on another day, whose end carries its date. There is no table: Telegram gives a table's
  columns no width control (no `width`, `<col>`), so the name started mid-message. Rich HTML accepts
  only the tags of the Bot API's "rich message formatting options" (a line break is `<br>`, text
  newlines mean nothing), so its structure lives in code and the locale files keep the legacy HTML
  that `ALLOWED_TAGS` in `test_bot_locales.py` checks.
  `build_announcement_text` stays the fallback: `TelegramDeliveryService` sends or edits it when
  Telegram rejects the rich one (`_rich_rejected`), which is also how an announcement posted as
  plain text before keeps being edited. Rich limits: 32768 characters, 500 blocks, 20 table columns.
- Bot tests drive the real dispatcher: the `tg` fixture (`tests/bot/conftest.py`) with
  `tests/support/telegram.py`'s recording session. It fails a test whose handler raised, even
  though the error middleware swallowed it.

## Frontend design code (`frontend/`)

The UI has one design language and agents extend it instead of reinventing it. Before writing
markup or CSS, find the piece that already exists; a screen that looks different from its neighbours
is a defect, not a style choice.

- **Tokens** — `frontend/src/theme/variables.css`: brand and surface colours (Ionic variables, light
  and `.ion-palette-dark`), the type scale `--fs-2xs … --fs-2xl` (11/12/13/14/16/18/22px), weights
  `--fw-regular|medium|semibold|bold` (400/500/600/700), icon sizes `--icon-xl` (28px) and
  `--icon-hero` (40px, empty and error states), radii `--radius-sm|md|lg|xl|pill`
  (10/12/16/20/999px), `--border-w` (1.5px) and `--font-mono`; for fields `--field-h` (48px),
  `--field-pad-x` (14px) and `--field-border` (a step stronger in the dark theme); the colours of an
  attendance outcome `--att-attended-rgb|absent|unmarked|upcoming` (RGB triplets: green, red, yellow,
  brand violet), used through `ui-att` below. The font is
  `Inter Variable`, bundled from `@fontsource-variable/inter` and loaded in `main.ts`.
- **Primitives** — `frontend/src/theme/components.css`, loaded once from `main.ts`: the field
  (`ui-field` and its parts: `ui-field-box`, `ui-field-label`, `ui-field-outline`, `ui-field-control`
  for the native `input`/`textarea`/`button` inside it, `ui-field-value` for a value that
  is not typed, `ui-field-foot`; `ui-field-title` for the heading of a group of controls and
  `ui-toggle-row` for a switch), `ui-menu` and `ui-menu-item` (a list of options under a field),
  `ui-select-trigger` (the button of a select inside a field), `ui-popup` and `ui-option` (the
  floating list of a dropdown, with `ui-option--active|selected|disabled` and a leading
  `ui-option-icon` when the option has an `icon`), `ui-select-pill`
  (+ `--sm`, `--set`: the compact select of a toolbar, with a leading icon and room for a
  direction button) and the `ui-pop` transition,
  `ui-icon-btn` (+ `--primary`, `--danger`, `--delete`, `--active`), `ui-help` (the round «?» button of a hint,
  drawn by `common/HelpTip`, its bubble is `ui-help-tip`), `ui-chips` and `ui-chip` (+ `--active`),
  `ui-btn` (+ `--primary`, `--ghost`, `--sm`); `ui-card`, `ui-card-head` and `ui-card-title` (a section
  card; `HomePage`'s own `.section-card` is a copy of it, see the debt below), `ui-count` (the number
  badge in a card head) and `ui-banner` (a tinted line with a close button: the day picked on a
  heatmap); `ui-att--attended|absent`
  (a filled mark), `ui-att--unmarked` (yellow hatching), `ui-att--upcoming` (a hollow one),
  `ui-att-rate` (a cell filled with the `--att-rate` colour set inline), `ui-att-hatch` (the same
  colour as stripes on the grey ground of `ui-att--unmarked`: a day with unmarked events, its marked
  ones having given it the colour; `--att-hatch` is the stripe period, 4px) and `ui-att-ink--<outcome>`
  (an icon or text in the outcome colour): every attendance chart, legend and calendar dot takes its
  colour from these, never from its own rgba; a day of the heatmap/calendar is the exception, it is
  coloured by its presence ratio through `rateColor`/`rateGradient` (`utils/memberAttendance.ts`: the
  presence token at 1, the unmarked token at 0.5, the absence token at 0, blended with `color-mix` in
  between; an unmarked event adds nothing to the ratio, so a day with only those stays at the middle,
  which is exactly `ui-att--unmarked`, and the hatching only says that not every mark is set), so a
  day with both presence and absence is never painted as one of them; the dialog parts `ui-sheet`, `ui-sheet-head`, `ui-sheet-title`,
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
  `prefix`/`suffix` slots and the `help` button (`HelpTip` before the suffix). On top of it: `UiInput`, `UiTextarea`, `UiSelect` (a custom
  dropdown on `useSelect`, see Dropdowns below), `PasswordField`,
  `DateTimeField`, `EntityPickerField` (search a reference, shows the pick as a value),
  `admin/SearchPicker` (+ `creatable`, `browse`, `locked`), `geo/LocationField` and `geo/AddressSearchSelect`.
- **Shared components** — `frontend/src/components/common/` and friends: `DateTimeField` (built on
  `TimeSpinner` and `TimeDrum`), `TimestampsMeta`, `event/StageFields` (one stage of an event, used
  by the create form and the event page), `common/SlidingTabs` (a row of tabs whose
  active pill slides to the chosen one; a tab takes `badge`, `invalid` and the list `shake`; the principal panel and the profile form use it), `common/UiSelectPill`,
  `event/EventCreateModal` (the new-event form, opened from the events list and the dashboard),
  `event/EventEditModal` and `event/EventStagesModal` (the event and its stages, shared by the
  event page and the admin: the caller passes the API adapter, `save` or `StageApi`),
  `admin/ResourceTable` and `admin/ResourceFormModal` for admin lists and forms (with
  `admin/ResourceFilterFields` for the filter fields, `admin/RowActionsMenu` for the actions of a row and
  `admin/MultiSearchField` for a field that takes several records), `common/SortFab` and `common/AppFab`
  (the floating buttons of a phone); `member/` (the attendance dashboards of a member and of a
  collective: `AttendanceHead` (the card with the rate), `AttendanceTiles`, `AttendanceActivity` (the
  Год/Месяц card with the period chips, the heatmap or calendar, the legend and the slots for the day
  picked and the empty state), `AttendanceHeatmap` (takes `items` or ready `days`), `MonthBars`,
  `TypeBars`, `AttendanceHistory`, `AttendanceLegend` (`labels` and `scaleLabels` rename the
  outcomes), `ProfileWho`, all fed by `utils/memberAttendance.ts` and `composables/useAttendancePeriod`;
  and `MemberEditorModal` / `MemberDeleteAlert`, the one add/edit dialog and delete confirmation
  shared by the member list and the profile), `collective/CollectiveEventList` and
  `CollectiveMemberList`, `common/PageState` (the error or not-found card with actions) and
  `common/BackLink`, `profile/PersonFile` (the admin dossier: person, profile, student card and contacts, fed by `adminPersonFileApi(personId)` from `profile/personFileApi`) and
  `calendar/CalendarGrid` (takes `dayMarks`, a list of dots per `yyyy-MM-dd`, to colour the day).
  New screens compose these.

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
- **Copy is short and does not hand-hold.** A label, a button or a heading says what it is and the
  person is trusted to work out the rest: no "Что вы хотите добавить?" under "Добавить контакт", no
  "Начните вводить…", "Выберите…" or "Нажмите…" as a placeholder, no sentence that repeats the title
  above it, no subtitle that repeats the tab (the login page has none). A name is the plain Russian
  one ("Электронная почта", not "Email" or "Адрес почты"; "Имя пользователя", not "Username"). An
  error says what is wrong in a few words. What is left to explain (what a switch does to other data,
  who sees the data, why a step is needed) is a `HelpTip`: a round «?» beside the title or inside the
  field (`help` of `UiField`, `UiInput`, `PasswordField`, `SearchPicker`), text as a prop or as `<p>`s
  in the slot. A message the person needs to act now (an error, a blocked button, a warning that
  appears on a change) is not a help: it stays visible as `error` or `hint`. The hints are a setting
  (`useSettingsStore().showHints`, «Подсказки» on the settings page, on by default): when it is off
  `HelpTip` draws nothing, so nothing a screen needs may live only in one.
- **Dates and times** go through `DateTimeField` only: typeable, with the `ДД.ММ.ГГГГ ЧЧ:ММ`
  template always visible, and a picker with a calendar and the two-drum `TimeSpinner`. Never use
  `<input type="date|time|datetime-local">` and never give such a field a placeholder text. A field
  may be given `suggest` (a date or a datetime): on focus it prefills the date of the suggestion, and
  a time is never filled in on the user's behalf. A new stage's start suggests the previous stage or
  the event date, and its end suggests the start.
- **Dropdowns** are `UiSelect` (in a field) and `UiSelectPill` (in a toolbar), both fed with
  `options: SelectOption[]` (`utils/selectOptions`: `optionsFromPairs`, `withAny`) and drawn by
  `UiSelectMenu`, a listbox teleported to `body` and anchored under the control, as wide as the
  field, flipped above when there is no room. Never use `<select>`/`<option>` or `ion-select`: the
  browser draws their list itself, in the colours of the OS, which is how text ended up the colour of
  the background in the dark theme. The list never takes focus (`mousedown.prevent`), keyboard works
  from the trigger (`composables/useSelect`: arrows, Home/End, Enter, Escape, type-ahead).
- **A list that offers its results never pushes the page.** The results of `EntityPickerField`
  (and so of `SearchPicker`) are a `UiSelectMenu` popup anchored under the input, like a dropdown:
  an inline list under a field shifted every field below it in a filter panel.
- **Filters and sort on a phone are floating buttons.** On a phone the filters of a list open in a
  sheet (`ion-modal`, breakpoints `[0, 0.6, 1]`, header "Фильтры", close button: `HomePage`,
  `DashboardPage`, `ResourceTable`) from a small `AppFab secondary` above the main one, and the sort
  is its own `SortFab` above that (`stack` counts the small ones; the menu lists the sorts, a tap on
  the direction row flips the order). On a desktop the filters stay on the page and the sort is a
  `UiSelectPill`. An admin list also keeps its search in a bar that sticks to the top, on a phone and
  on a desktop, and goes away with the swipe up (`composables/useHideOnScroll`, a `transform`, never a
  height, so the list does not jump; the desktop filter panel sits outside the bar, so a tall panel
  never drops with it); the small buttons then slip under the main one (`AppFab` `tucked`). The list ends with room
  for the main button (88px), so it never covers the last row's actions.
- **A row of an admin table never loses its edit and delete buttons.** The other actions of a row
  (`rowLinks`, `extraAction`) are buttons while there is one of them and fold into one `RowActionsMenu`
  ("⋯") when there are two or more: a menu that hides a single button is a defect, and so is clipping
  the cell (`text-overflow` on the actions cell once replaced the delete button with an ellipsis).
  Every action of a row, links and edit and delete alike, is a `ui-icon-btn` in one `.row-actions` row
  (34px, one centre line; edit is `--primary`, delete is `--delete`, which stays red at rest where
  `--danger` only tints on hover): an `ion-button` there has another size and baseline and made the row
  crooked. On a phone the link chips and the buttons share one card footer, the buttons on the first
  chip row (`.mobile-link` is as tall as the button).
- **A form field with several records** is a `multisearch` field of `ResourceFormModal`
  (`MultiSearchField`: chips plus a picker). Its `choices(search, form)` may look at the form, and
  `dependsOn` blocks it until the field it depends on is set (the roles of a member need the
  collective); its value goes to the API as a list of ids, an empty one included, because an empty
  list is how a link is cleared.
- **A place picker opens on what was used before.** `LocationField` and `LocationPickerModal` take a
  `collectiveId` and, with nothing typed, list that collective's recent places first
  (`composables/useRecentLocations`: the event service for the ids, then geo for the rows), under the
  heading "Недавние места", with the map fitted to them; without recents, or without a collective,
  the general list of locations. The list follows the map (the places around its centre) only after
  the user has touched it (`GeoMap` `interact`: pointer, wheel or keys), never because the map
  settled by itself after a fit: that is what used to replace the list with the nearby addresses.
- **Filters live in the URL.** A list page keeps its search, sort and filters in the address bar
  (`composables/useUrlState` for plain pages, `utils/urlState` `readQuery`/`patchQuery` for the rest;
  `ResourceTable` does it for every admin list: `q`, `sort`, `order` and one key per filter). Values
  equal to their defaults stay out of the URL, other query parameters are left alone, and it is
  written with `replaceState`, so no history entries. This is the state of the screen, not the
  parameters of an API request: the two share names only by convention. A page that links to a
  filtered list builds the target with `withQuery('/admin/members', { collective_id })`; the panel
  layouts accept a target with a query, and recreate the page when only the query changed.
- **The home list and the calendar** (`views/main/HomePage.vue`, `components/event/EventList.vue`). The
  facets (status for a leader, type, level, format) are multi-select chips (`ui-chip`, «Все» is the
  empty list) and «Только предстоящие» is a switch; they live in the URL (`utils/homeFilters`) and go
  to the server (`status`/`status__in`, `type__in`, `level__in`, `format__in`, `date__gte`), never
  filtered on the client alone: a window of 10+10 events filtered afterwards left a short list with
  `hasMore*` still true and nothing to scroll to load more. A change of the filters reloads the
  window around the selected day. **The list scrolls to a day only through `EventList.scrollTo(day,
  smooth)`**, which puts the first card of the day (else the next one) at the top edge and answers
  whether it got there (`false`: the list was too short, so `HomePage.aimAt` loads more and tries
  again). The selected day follows the list only while the person scrolls (`wheel`, `touchstart`,
  `pointerdown`, `keydown` mark it as theirs) and is the card at the **top edge**, never the middle of
  the list window (on a phone the window is taller than the screen); a programmatic scroll and the
  compensation after a load never change the day, and nothing loads while a jump is settling.
  `settings.collapseOnScroll` (default on) decides whether the week calendar on a phone and the search
  bar of an admin list (`useHideOnScroll`) hide on the way down.
- **Admin lists** cross-link: a `ResourceTable` takes `rowLinks` (a button per row, a chip on a phone)
  and `ResourceFormModal` takes `links`, both leading to another list with the filter already set
  (`utils/adminLinks`). A filter of type `picker` searches a record of another resource
  (`utils/adminPickers`: one entry per resource with its `search` and the `ResourceKind` that names a
  picked id); a reference field of a form shows the name of the saved value by asking for that id
  (`resolveResourceLabel`), never by looking for it among the first search results.
- **The collective profile** (`views/principal/CollectiveProfilePage.vue`) is the member profile for
  the whole roster and lives in two places the same way: the panel tab «Дашборд» `/principal/dashboard`
  (the landing tab; the layout passes the active collective as `collectiveId`) and `/collective/<id>`
  (`views/CollectivePage.vue`, open to the leader and the active members). Its heatmap day is coloured
  by the share of the declared roster that came, `attended / (attended + absent)` of the day's places
  (`collectiveDays`), and unmarked places only hatch the day. The member profile reached from it goes
  back to the tab through `principalReturnTo`. The attendance matrix (`views/principal/DashboardPage.vue`,
  the file kept its old name) is the tab «Участия» `/principal/attendances` (`gridOutline`); the old
  `/principal/collective` redirects to the dashboard.
- **The user-facing name of the personal data card is «Подробная информация»** (the block on `/profile`,
  the form at `/profile/data`, the invitation pages, toasts and errors): not «профиль». «Профиль» stays
  for the page and the menu entry of the account, for the attendance profiles of a member and of a
  collective, and in the admin panel (`Профили`, the person file), which keeps the technical word.
- **A user makes their own profile** at `/profile/data` (`views/ProfileFormPage.vue`); `/profile/edit`
  is the account (email, password). One form builds person, profile, student card, diet, workplace and
  contacts through `/profile/v2/profiles/my` (`stores/myProfile`); the token carries the person id, so
  the page refreshes it (`auth.tryRefresh()`) after creating. A new profile is one continuous form; an
  existing one is `SlidingTabs` sections (`utils/profileFormDiff`: `SECTIONS`, the count of changed
  fields per section as the tab `badge`, a section with a missing required field `invalid` and
  `shake`n after a failed save), swiped on a phone with `composables/useSwipe` (`data-no-swipe` opts a
  region out), and one save button for all of them. A reference shared by profiles (university,
  faculty, group, degree, diet, workplace) is a `SearchPicker` with `creatable` (a typed name nobody
  has comes out as a `draft`, made by `POST /profile/v2/...` at submit, not before; the degree is
  `creatable` for a superuser only) and `browse` (the
  list opens on focus); a picked group fills its faculty, university, degree and grade and `locked`
  closes them. Contacts go through `profile/ContactsEditor` (the "Добавить контакт" selector turns into a
  field named after the kind and built for it, `utils/contactTypes`; the first contact of a kind becomes
  the main one, a star in the field tells which is). Passport data is
  not in it. The admin dossier is `profile/PersonFile` (admin only).
- **A field of an admin form can depend on the form**: `FormField.visibleWhen(form)` shows and saves it
  only while it holds (the university of a faculty on the organizations page). The student catalog has
  its own admin pages next to «Студенты»: «Группы» (`/admin/student-groups`) and «Степени»
  (`/admin/student-degrees`); a faculty carries its university.
- **A route component that holds `ion-tabs` is wrapped in `ion-page`** (`TabsShell`). The outer
  `ion-router-outlet` switches pages only for a component that registers an `ion-page`: without it the
  login page stayed in the DOM next to the app after signing in (`tests/unit/tabsShell.spec.ts`).
- **A new primitive** is added to `components.css` and to the list above in the same change.
- **Sub-pages of the principal and admin panels** (`/principal/members/<id>`, `/admin/persons/<id>`)
  are in-place routes: the layout matches a path prefix and renders the page itself, and a child page
  navigates with `usePrincipalNavigate` / `useAdminNavigate` (a modal that is open must be dismissed
  first, `modalController.dismiss()`, or its overlay stays over the new page), never `router.push`
  inside the panel
  (see `utils/inPlaceNav.ts`). Such a page must also handle a deep link and a missing entity.
  `MemberProfilePage` is the one page that lives in two places: in the panel
  (`/principal/members/<id>`, reached from the member list and the dashboard) and outside it
  (`/member/<id>`, `views/MemberPage.vue`, reached from the event page and open to the members of
  the collective); it finds out which by injecting `principalNavigateKey`, and shows edit/delete
  only when the API answers `can_manage`.
- **Check what you built** in the light and the dark theme, at phone width (375px) and on a desktop,
  with `npx vue-tsc --noEmit`, `npx eslint <files>` and `npx vitest run`.

Known debt, to be paid when a view is touched and not as a drive-by: per-view copies of `.auth-btn`
(6 files), `.section-card` (`HomePage`, the old `ui-card`), `.sort-btn` (3), `.lcf-btn` (the `ui-btn` look), `.icon-btn`, `.form-field` (now only a
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

## Changelog (`frontend/public/changelog/`)

The in-app changelog ("Что нового") is written for the **users of the app** (students, collective
leaders, people working in the admin panel), not for developers or operators. It is shown to them
after every update, so it has to read like news, not like release notes for the team.

- **What goes in:** what changes for the person using the app - a new feature, a changed behaviour,
  a fixed bug. That is the whole content. A change the user cannot see gets no line, however big it
  was (refactors, tests, speed-ups nobody notices, internal clean-ups).
- **How it is written:** in plain Russian anyone understands: what the person can do now, or no
  longer suffers from, in the words of the screen (the names of pages and buttons as they are shown).
  Never: endpoint paths, HTTP codes, environment variables, migrations, deploy/Docker steps, names of
  services and libraries (Photon, Kafka, Traefik, Orval, ...), API versions, schema fields, ids.
- **Where the technical side goes:** the commit message and the hand-over message to the maintainer
  (a migration to run, a new setting, an API change, a known limitation). Not the changelog: no
  "Сервер и API" and no "Развёртывание" sections.
- **Structure:** group by what the user sees (`Мероприятия`, `Telegram-бот`, `Административная
  панель`, `Исправления`, ...); a release describes everything user-visible since the previous one.
- **Format** (the page's parser reads only this): a file `<version>.md` with `## <version> — <date>`,
  `### section`, `- item` and `**bold**`; no backticks, links or nested lists; plus the newest entry
  first in `index.json`. It is committed as `docs(changelog): ...` in the `frontend` submodule.

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
- **Lint and type-check are clean and stay clean.** `uv run ruff check .` ends with "All checks passed!"
  (`[tool.ruff.lint]` selects `E, F, I, UP, B, SIM, C4, RUF, ASYNC, N`) and `uv run basedpyright`
  (`typeCheckingMode = "strict"`, whole repo: `src/`, `tests/`, `migrations/`, `scripts/`) reports 0
  errors with an empty `.basedpyright/baseline.json`. A new finding is a regression of your change:
  fix it, do not baseline it. Where a suppression is the honest answer, keep it narrow:
  - a systematic false positive goes into `pyproject.toml` with a comment saying why (FastAPI `Depends`
    as a B008 immutable call, the Cyrillic look-alikes in `allowed-confusables`, the relaxed
    `executionEnvironments` for `tests` and `migrations`, `reportMissingTypeStubs` for packages without
    stubs, generated files exempt from E501);
  - a single place gets `# noqa: CODE` or `# pyright: ignore[oneRule]` plus a short reason when a third
    party fixes the shape (pydantic field defaults and `Constants` of fastapi-filter, aiogram's
    `start_polling`, faststream's overloaded `subscriber`); never a bare ignore, never `# type: ignore`.
  - `uv run basedpyright` rewrites the baseline file when findings disappear; commit that rewrite.
    Run it in a fully synced environment (`uv sync --all-groups`), a partial venv invents "unknown
    type" findings from unresolved imports.
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
