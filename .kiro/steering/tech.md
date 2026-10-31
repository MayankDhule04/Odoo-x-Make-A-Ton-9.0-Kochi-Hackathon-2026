# Tech stack and conventions

## Stack
- **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0 with sync sessions, Alembic, psycopg 3, Pydantic v2 with pydantic-settings, pytest.
- **Database**: PostgreSQL 17 in Docker.
- **Frontend**: React 19, Vite 8, TypeScript 7, Tailwind CSS 4, TanStack Query 5, TanStack Table 8, Recharts 3.
- **Runtime**: Docker Compose with three services: `db`, `api` (port 8000) and `web` (port 5173, proxies `/api` to the API).
- **Added later by the owning member**: JWT access and refresh tokens with argon2 or bcrypt (auth), APScheduler or Celery beat (billing schedule), WeasyPrint (invoice PDFs), SMTP with a dev outbox (email).

## Shared contracts
- Money is never a float. Use `Decimal` in Python and `Numeric` (or integer minor units, if §C.3 says so) in Postgres. Money in JSON is a string.
- Timestamps are timezone-aware UTC: `DateTime(timezone=True)` columns, and database sessions run with `timezone=UTC`. Convert to local time only in the UI.
- Every protected route depends on `require_role(...)` from `app.core`. Customer-scoped queries take the customer id from the authenticated user, never from the request.
- Every state change goes through one transition function per entity that rejects illegal transitions and writes a history row.
- Changes to prices, plans, discounts and record states also write an audit log entry.

## Backend conventions
- All routes live under `/api`. Routers stay thin: business logic goes in `app/services/<domain>`, request and response models in `app/schemas/<domain>`.
- Get a database session with the `DbSession` dependency from `app.core.db`.
- Models inherit from `app.models.base.Base` and use `TimestampMixin` for `created_at` and `updated_at`. Give every `CheckConstraint` an explicit name, because the naming convention requires it.
- Schema changes go through Alembic migrations only, never `Base.metadata.create_all`.
- Tests use the `client` and `db_session` fixtures from `app/tests/conftest.py`. Each test runs inside a transaction that is rolled back afterwards.

## Frontend conventions
- Call the API with relative `/api/...` URLs. The Vite dev server proxies them to the API.
- Fetch server data with TanStack Query.
- TanStack Table is pinned to v8: use `useReactTable` and `getCoreRowModel`, not the v9 `useTable` API.

## Commands (run from the repo root)
| Task | Command |
|---|---|
| Start or rebuild everything | `docker compose up --build` |
| Run backend tests | `docker compose exec api pytest` |
| Create a migration | `docker compose exec api alembic revision --autogenerate -m "<domain>: <change>"` |
| Apply migrations | Automatic when the API starts, or `docker compose exec api alembic upgrade head` |
| Seed demo data | `docker compose exec api python /scripts/seed.py` |
| Reset the database | `docker compose down -v` |

Run `docker compose up --build` again after changing `requirements*.txt`, `package.json`, `vite.config.ts` or a Dockerfile.
