# Repository structure

```
backend/
  app/
    main.py              FastAPI app; mounts app/api/router.py under /api
    core/                settings, database, security (passwords, JWT), rbac; later audit log, email (Member 1)
    api/<domain>/        routers; app/api/router.py already includes every domain
    services/<domain>/   business logic
    models/<domain>/     SQLAlchemy models; import each model in the package __init__.py
    schemas/<domain>/    Pydantic request and response models
    jobs/                scheduled jobs such as billing runs and dunning
    seed/                demo data steps called by scripts/seed.py
    tests/               pytest suite, shared fixtures (conftest.py) and helpers.py
  alembic/versions/      migrations, one per change
frontend/src/
  pages/ components/ lib/   shared shell, routing and layout (Member 4)
  api/                      API client
  features/<domain>/        screens for each domain
scripts/seed.py             runs the app/seed steps; the API runs it on every start
.kiro/steering/             these steering files
```

## Domains and owners
| Domain | Backend packages | Frontend | Owner |
|---|---|---|---|
| Auth, RBAC, audit log | `core`, `api/auth`, `models/auth` | `features/auth` | Member 1 |
| Customers | `models/customers` | | Member 1 |
| Catalog | `api/catalog`, `models/catalog` | `features/catalog` | Member 2 |
| Subscriptions | `api/subscriptions`, `models/subscriptions` | `features/subscriptions` | Member 2 |
| Billing and invoices | `api/billing`, `models/billing`, `jobs` | `features/invoices` | Member 3 |
| Payments | `api/payments`, `models/payments` | `features/payments` | Member 3 |
| Reporting and portal | `api/reporting` | `pages`, `components`, `lib`, `features/portal` | Member 4 |

## Data model (shared contract)
Use exactly these table names: `users`, `customers`, `products`, `product_attributes`, `product_variants`, `plans`, `quotation_templates`, `quotation_template_lines`, `subscriptions`, `subscription_lines`, `subscription_history`, `taxes`, `discounts`, `discount_products`, `discount_usages`, `invoices`, `invoice_lines`, `payments`, `dunning_attempts`, `mrr_events`, `audit_log`, `email_outbox`, `password_reset_tokens`.

Required indexes for the 2-second budget: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer_id)`, `payments(invoice_id)`, and a unique `(subscription_id, period_start, period_end)` on `invoices`.

## Working rules
- Work inside your own domain folders. Keep edits to shared files (`app/main.py`, `app/api/router.py`, `app/models/__init__.py`, `docker-compose.yml`, `package.json`, `requirements.txt`) small, and tell the team when you make them.
- Pull `main` right before creating a migration. If two migrations end up with the same parent, the API container stops at startup with "Multiple head revisions". Fix it with `docker compose run --rm api alembic merge heads -m "merge heads"` and commit the merge migration. The test `test_single_alembic_head` catches the same problem.
- The test `test_models_match_migrations` fails if a model changed without a matching migration.
- Seed steps live in `app/seed/` and must be idempotent and fast, because the API runs `scripts/seed.py` on every start. Put large-volume data (10k subscriptions, 50k invoices) behind a separate command.
- Scope commit messages to your domain, for example `feat(auth): ...`, `feat(catalog): ...`, `feat(billing): ...`, `feat(portal): ...`.
