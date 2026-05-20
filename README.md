# Plum'ID — API

REST API for **Plum'ID** (bird-feather identification).
Stack: **FastAPI**, **SQLAlchemy 2**, **PostgreSQL** (SQLite for tests),
**JWT** (user accounts), **API Key** (service-to-service),
**HMAC + anti-replay** (mobile app uploads), **SMTP** (email verification).

* **Interactive docs**: `http://localhost:8000/docs` (Swagger)
* **OpenAPI schema**: `http://localhost:8000/openapi.json`

---

## Architecture

The deployment target is **Railway with three services** (the same shape
also runs locally via `docker compose`):

```
┌─────────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  plumid-db          │     │  plumid-api      │     │  plumid-model    │
│  postgres:16        │◄────┤  FastAPI / Py3.11│────▶│  FastAPI worker  │
│  init: 01-schema.sql│     │  /auth /species  │     │  /predict /preprocess
│  (custom image)     │     │  /feathers …     │     │  (sibling repo)  │
└─────────────────────┘     └──────────────────┘     └──────────────────┘
```

* **plumid-db** — built from `db/Dockerfile`, bootstraps the schema and
  seed data from `db/initdb/01-schema.sql` on first boot.
* **plumid-api** — this repository.
* **plumid-model** — sibling repository ([`../plumid-model`](../plumid-model)),
  exposes preprocessing + prediction over HTTP.

---

## Local development — 3-container stack

```bash
# 1. Copy the env template and review the values
cp .env.example .env

# 2. Build & start all three services
docker compose up -d --build

# 3. Tail the logs
docker compose logs -f api
```

The API listens on <http://localhost:8000>. PostgreSQL is exposed on
`localhost:5432`. The model service answers on `http://localhost:8001`.

> The `model` service expects the `plumid-model` repository to live next
> to `plumid-api` on disk (i.e. `../plumid-model`). Override the path
> with `MODEL_BUILD_CONTEXT` if it lives elsewhere.

### Tear down

```bash
docker compose down          # stop services
docker compose down -v       # also wipe the Postgres volume (full reset)
```

---

## Railway deployment

Each of the three components becomes its own Railway **service**:

| Service        | Source                       | Runtime |
| -------------- | ---------------------------- | ------- |
| `plumid-db`    | this repo, root `db/`        | Postgres image baked from `db/Dockerfile` |
| `plumid-api`   | this repo, root              | Python (Dockerfile auto-detected) |
| `plumid-model` | `plumid-model` repo, root    | Python (Dockerfile auto-detected) |

### 1. Create the database service

* New service → **Deploy from GitHub repo** → pick the `plumid-api` repo
  → set the **root directory** to `db/`.
* Add a persistent volume mounted at `/var/lib/postgresql/data`
  (Railway → Service → *Volumes*).
* Set service variables:
  * `POSTGRES_USER=postgres`
  * `POSTGRES_PASSWORD=<strong-password>`
  * `POSTGRES_DB=plumid`
* On the first boot, the init script creates the schema, the
  application roles (`plumid_app`, `plumid_editor`, …), and seeds the
  `species` table.

> **Alternative**: use Railway's managed PostgreSQL plugin instead of
> the custom container. In that case skip the `db/` service and apply
> `db/initdb/01-schema.sql` once via `psql $DATABASE_URL -f …`. The
> downside is that managed Postgres restricts `CREATE ROLE` — you may
> need to drop the role-creation block from the SQL and connect the API
> as the master user.

### 2. Create the API service

* New service → **Deploy from GitHub repo** → pick `plumid-api`.
* Service variables (minimum):
  * `DATABASE_URL` — point to the Postgres service. With the custom DB
    container above, use the application role:
    `postgresql+psycopg2://plumid_app:AppUser123!@${{plumid-db.RAILWAY_PRIVATE_DOMAIN}}:5432/plumid`
    (Railway exposes the private DNS as a template variable).
  * `MODEL_SERVICE_URL` — `http://${{plumid-model.RAILWAY_PRIVATE_DOMAIN}}:8001`
  * `AUTH_SECRET`, `APP_HMAC_SECRET`, `PLUMID_API_KEY` — strong random secrets.
  * `CORS_ALLOW_ORIGINS` — comma-separated list of front-end domains.
  * SMTP settings if email verification is enabled.
* Railway injects `$PORT`; the container's CMD honours it.

### 3. Create the model service

Follow the deployment instructions in `../plumid-model/README.md`.

### Networking

Railway's private networking lets services reach each other on
`*.railway.internal`. The API talks to Postgres and to the model
service over that internal DNS — no public exposure required for those
two. Only the API needs a public domain.

---

## Configuration reference

All runtime config goes through environment variables. See
[`.env.example`](.env.example) for the full list. Highlights:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | *(empty)* | Full Postgres DSN; takes priority over the discrete fields. Both `postgres://…` and `postgresql://…` are accepted (auto-rewritten to use psycopg2). |
| `IP_DB` / `PORT_DB` / `USER_DB` / `MDP_DB` / `NAME_DB` | `postgres` / `5432` / `plumid_app` / `AppUser123!` / `plumid` | Used to build the DSN if `DATABASE_URL` is empty. Aliases: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`. |
| `DB_SSLMODE` | *(empty)* | Set to `require` / `verify-full` for managed Postgres providers. |
| `MODEL_SERVICE_URL` | *(empty)* | URL of the model microservice. If empty, `/upload/feather` returns a stub instead of forwarding. |
| `AUTH_SECRET` | `PLEASE_CHANGE_ME` | HS256 secret for JWT signing. **Replace in production.** |
| `APP_HMAC_SECRET` | `CHANGE_ME_SUPER_SECRET` | Shared with the mobile app for the `/upload/feather` HMAC signature. |
| `PLUMID_API_KEY` | `MON_SUPER_TOKEN` | Bearer token for service-to-service calls. |
| `CORS_ALLOW_ORIGINS` | `*` | CSV of allowed origins. |

---

## Database schema

The schema is defined once, in `db/initdb/01-schema.sql`, and faithfully
mirrored by the SQLAlchemy models under `models/`. A matching Alembic
baseline lives at `alembic/versions/0001_baseline_pg.py` for environments
where the SQL bootstrap is not used.

### Tables

* **species** — reference data (one row per bird species).
  `idspecies`, `sex CHAR(1)`, `region`, `environment`, `information TEXT`,
  `species_name UNIQUE`, `species_url_picture TEXT`.
* **feathers** — feather records linked to a species.
  `idfeathers`, `side`, `type`, `body_zone`, `species_id → species`.
* **pictures** — image metadata linked to a feather.
  `idpictures`, `url TEXT`, `longitude NUMERIC(9,6)`, `latitude NUMERIC(9,6)`,
  `date_collected DATE`, `feathers_id → feathers`.
* **users** — accounts.
  `idusers`, `password_hash`, `role`, `mail UNIQUE`, `created_at`,
  `username`, `is_active`, `email_verified_at`, `is_verified`,
  `pictures_id → pictures` *(profile picture)*.

> **Note**: pictures do **not** carry a foreign key back to the user.
> Instead, users hold an optional `pictures_id` that references a
> profile/avatar picture. This matches `SQL_migration_DB.sql`.

### Migrations

Schema and seed data are managed by **Alembic**, run automatically at
container startup via `entrypoint.sh` → `scripts/run_migrations.py`.

The runner is idempotent and handles three cases without manual
intervention:

* Fresh database → applies the full chain (baseline + every revision).
* Pre-existing database without `alembic_version` (e.g. tables created
  by a manual SQL bootstrap) → stamps the baseline as already applied,
  then runs only the newer revisions.
* Already at head → no-op.

To make this work on Railway's native Postgres plugin, set the
`MIGRATIONS_DATABASE_URL` variable on the API service to the superuser
DSN (the application role `plumid_app` cannot create the
`alembic_version` table). The application's runtime `DATABASE_URL` can
remain the restricted `plumid_app` account.

See [`docs/migrations.md`](docs/migrations.md) for the complete guide
(toggles, adding revisions, troubleshooting).

---

## Authentication

Two mechanisms coexist:

1. **API Key** — for service-to-service calls (model service, internal
   tooling). Header: `Authorization: Bearer <PLUMID_API_KEY>`.
2. **JWT (HS256)** — for user accounts. Issued by `POST /auth/login`,
   consumed by `Authorization: Bearer <jwt>`.

The mobile-app upload endpoint (`POST /upload/feather`) is authenticated
with the user's JWT only — no HMAC signature, no nonces. The app just
sends:

```
Authorization: Bearer <jwt>
Content-Type:  multipart/form-data; boundary=...

file=@<photo.jpg>
```

When `MODEL_SERVICE_URL` is set, the endpoint forwards the image to the
model service (`POST /predict`) and relays its response:

* `200` → the prediction (`species_id`, `species_name`, `confidence`, `top_k`)
* `422` → preprocessing warning (`NO_FEATHER` or `TOO_MANY_FEATHERS`)
  relayed verbatim so the app can display the user-facing `message`
* `503` → model not ready yet (cold start)

If `MODEL_SERVICE_URL` is empty, the endpoint returns a stub
(`prediction: null`) to keep local development unblocked.

---

## Endpoints

```
GET    /health
POST   /auth/register
POST   /auth/login
GET    /auth/me
POST   /auth/request-password-reset
POST   /auth/reset-password
POST   /species
GET    /species/{idspecies}
DELETE /species/{idspecies}
POST   /feathers
GET    /feathers/{idfeathers}
DELETE /feathers/{idfeathers}
POST   /pictures
GET    /pictures/{idpictures}
DELETE /pictures/{idpictures}
POST   /upload/feather       (Bearer JWT, forwarded to model service)
```

See `/docs` for the full interactive contract.

---

## Tests

```bash
# Inside the api container
docker compose exec api pytest -q

# Or locally with a venv
pip install -r requirements.txt
pytest -q
```

Tests use an in-memory SQLite database (see `tests/conftest.py`), so
they don't need PostgreSQL or any of the other services.

---

## Repository layout

```
plumid-api/
├── alembic/                # Alembic config + single PG baseline
├── core/                   # security primitives (bcrypt, JWT)
├── crud/                   # data-access helpers
├── db/                     # ── plumid-db service ──────────────
│   ├── Dockerfile          # custom postgres:16 image
│   ├── initdb/
│   │   └── 01-schema.sql   # auto-run on first DB boot
│   └── railway.json
├── dependencies/           # FastAPI deps (auth, …)
├── docs/                   # internal docs (alembic guide, …)
├── middlewares/            # tracing, body-cap, rate limiter
├── models/                 # SQLAlchemy models (mirror of the SQL schema)
├── routes/                 # FastAPI routers
├── schemas/                # Pydantic schemas
├── security/               # HMAC + anti-replay
├── services/               # outbound integrations (SMTP, …)
├── tests/                  # pytest suite (SQLite-backed)
├── compose.yaml            # 3-container local stack
├── Dockerfile              # API image
├── railway.json            # API service config
├── requirements.txt
├── settings.py             # pydantic-settings
└── README.md
```
