# Tech stack and conventions

## Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 with sync sessions, Alembic, psycopg 3, Pydantic v2 with pydantic-settings.
- **Database**: PostgreSQL 17 in Docker.
- **Frontend**: React 19, Vite 8, TypeScript 7, Tailwind CSS 4, TanStack Query 5, TanStack Table 8, Recharts 3. The admin/staff app and the customer portal share one codebase with role-based routes.
- **Testing**: pytest with FastAPI's TestClient (runs on httpx2) for the API, Vitest for key UI logic, Playwright for 2 or 3 happy-path flows.
- **Runtime**: Docker Compose with three services: `db`, `api` (port 8000) and `web` (port 5173, proxies `/api` to the API).
- **Added by the owning member**: APScheduler or Celery beat for the billing job and WeasyPrint for invoice PDFs (Member 3).

## Shared contracts (never break these alone)
- **Money** is never a float. Use `Decimal` in Python and `Numeric` in Postgres (or integer minor units). Single currency, INR, with a currency code on every amount. Money in JSON is a string.
- **Time**: store timezone-aware UTC (`DateTime(timezone=True)`); database sessions run with `timezone=UTC`. Convert to the user's time zone only in the UI.
- **RBAC** is enforced on every API route with `require_role` (added with the auth work), never only in the frontend. Customers are scoped by the authenticated user, never by an id sent by the client.
- **State changes** go through one transition function per entity that rejects illegal transitions and writes a history row. Changes to prices, plans, discounts and record states also write an audit log entry.
- **Lists**: every list endpoint is paginated and backed by an index. No N+1 queries. Dashboard numbers come from SQL aggregates, never from loading rows into Python.
- **Billing** runs in a transaction with a unique `(subscription_id, period_start, period_end)` constraint, never in a bare loop.
- **Validation**: every endpoint validates its input with Pydantic and returns errors in one consistent format.
- **Tests**: every feature ships with tests.
- "More than 8 characters" means 9 or more.

## Backend conventions
- All routes live under `/api`. Routers stay thin: business logic goes in `app/services/<domain>`, request and response models in `app/schemas/<domain>`.
- Get a database session with the `DbSession` dependency from `app.core.db`.
- Models inherit from `app.models.base.Base`, use integer `id` primary keys, and use `TimestampMixin` for `created_at` and `updated_at`. Give every `CheckConstraint` an explicit name, because the naming convention requires it.
- Store enums as strings with a named check constraint: `sa.Enum(MyEnum, native_enum=False, create_constraint=True, name="my_enum", length=20)`. Native Postgres enum types are hard to change in migrations.
- Schema changes go through Alembic migrations only, never `Base.metadata.create_all`.
- Tests use the fixtures in `app/tests/conftest.py`. Each test runs inside a transaction that is rolled back afterwards.

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
