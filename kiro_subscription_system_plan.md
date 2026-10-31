# Brightloop Subscription Management System: Kiro Prompt and Build Plan

Made for the Odoo Make-a-ton problem statement. Three parts: (A) how to run it in Kiro, (B) the master prompt, (C) the phased plan with steering files, tasks and a demo script.

---

## Part A: How to use this with Kiro

1. Create an empty project folder and open it in Kiro.
2. Create the three steering files from Part C.1 under `.kiro/steering/` (`product.md`, `tech.md`, `structure.md`).
3. Open a **Spec** session and paste the **Master Prompt** from Part B. Let Kiro generate `requirements.md`, then `design.md`, then `tasks.md`. Review each before approving.
4. Check that `requirements.md` covers every row in the traceability table (Part C.4). If a row is missing, ask Kiro to add it.
5. Execute tasks one phase at a time (Part C.2). Do not run the whole task list at once. Run the tests at the end of each phase.
6. Build Phases 1 to 5 first. Those cover every expectation in the problem statement. Phase 6 (differentiators) comes after the core works.

---

## Part B: Master Prompt (paste into a Kiro Spec session)

```
You are building "Brightloop Subscriptions", a unified subscription management
platform for a company that sells software on subscription (monthly/yearly plans,
add-ons, product variants). It must run the full life of a subscription business:
products and plans -> quotations -> subscriptions -> invoices -> payments ->
revenue reporting. Customers range from small shops on monthly plans to large
companies on yearly contracts.

Generate requirements.md (EARS-style acceptance criteria), design.md and tasks.md.
Treat everything below as mandatory unless marked OPTIONAL.

## Roles and access (RBAC enforced on the backend, not just the UI)
- ADMIN: controls everything. Only ADMIN can create staff users, create discount
  rules, and configure taxes, plans and products.
- STAFF (internal): day-to-day work with limited access. Can manage customers,
  create quotations and subscriptions, confirm/cancel/send/print invoices, record
  payments. Cannot create staff, discounts or taxes.
- CUSTOMER: portal only. Sees and manages ONLY their own subscriptions and invoices.
  Every customer-scoped query must filter by the authenticated customer.

## Auth
- Sign-up with email + password. Email is unique across all accounts
  (case-insensitive). Self sign-up always creates a CUSTOMER.
- Password rules: MORE than 8 characters (so at least 9), at least one uppercase,
  one lowercase and one special character. Validate on client and server, with clear
  error messages.
- Forgot password: generate a single-use, expiring reset token (30 min), store only
  its hash, and send a reset link to the registered email (use SMTP with a dev
  fallback that writes the email to a viewable "outbox" screen and the console).
  Do not reveal whether an email exists.
- Passwords hashed with argon2 or bcrypt. JWT access token + refresh token.
  Rate-limit login and reset endpoints.

## Products and variants (ADMIN)
- Product: name, type (service/software/add-on/physical), sales price, cost price,
  notes. Margin is computed (sales - cost).
- Variants by attribute, e.g. attribute "Brand" with value "Odoo" adding +560 to
  the price. Each variant has a price extra. Effective price = base + variant extra.

## Plans (ADMIN)
- Name, price, billing period (DAILY, WEEKLY, MONTHLY, YEARLY), minimum quantity,
  available-from and available-to dates.
- Per-plan flags decided by the admin: auto-close when it ends, allow early close,
  allow pause, allow renew.
- A plan outside its availability window cannot be used for new subscriptions.

## Quotation templates and subscriptions
- Quotation template: preset plan + product lines, validity in days. A sales rep
  creates a quotation from a template and can edit it afterwards.
- Subscription: unique auto-generated number (e.g. SUB-2026-000123), customer,
  plan, start date, expiry date, payment terms (e.g. Immediate, Net 15, Net 30),
  and lines: product (and variant), quantity, unit price, taxes, amount.
- State machine: DRAFT -> QUOTATION -> CONFIRMED -> ACTIVE -> CLOSED. Illegal
  transitions are rejected. Every transition is stored in a history table (who,
  when, from, to) and shown as a timeline so anyone on the team can see where it stands.
- Pause / resume / early close / renew according to the plan's flags.

## Invoicing (the billing run)
- Invoices are generated automatically from subscriptions that are due. Customer
  details, lines, taxes and totals are pre-filled from the subscription.
- Billing run is IDEMPOTENT and transactional: never bill twice, never skip.
  Enforce with a unique constraint on (subscription_id, period_start, period_end)
  and next_billing_date advancement in the same transaction. A re-run of the same
  day creates zero duplicates. A crash mid-run must be safely resumable.
- Runs on a schedule (daily job) and can be triggered manually by ADMIN/STAFF.
- Tax engine: admin-defined tax rules (name, percentage, applies to products or
  categories, inclusive/exclusive). Tax computed automatically per line.
- Invoice state machine: DRAFT -> CONFIRMED -> PAID. Also CANCELLED. Staff can
  confirm, cancel, send (email) and print (PDF) any invoice. Confirmed invoices are
  immutable (corrections via cancel + re-issue or credit note).
- Sequential invoice numbers with no gaps per year.

## Discounts (ADMIN only)
- Rule: type (FIXED amount or PERCENTAGE), minimum purchase amount, minimum quantity,
  start date, end date, usage limit (max number of times it can be applied).
- Applies to specific products OR to whole subscriptions.
- Once a rule applies, it appears on the NEXT invoice automatically as its own
  discount line, with no manual step. It stops when expired or when the usage limit
  is reached. Usage count increments atomically and only when an invoice is confirmed.

## Payments
- Record a payment against an invoice: method (card, bank transfer, UPI, cash,
  cheque), amount, date, note. Partial payments supported. Invoice becomes PAID when
  fully paid. Overpayment is rejected or stored as credit (pick one and document it).
- At any time show which invoices are paid, partially paid, outstanding and overdue
  (overdue = past due date and not fully paid), and by how many days.

## Reporting dashboard (finance lead)
- One page showing: active subscriptions count, revenue collected, amount still
  owed, overdue invoices list, payments list. Filters: date range, customer, plan,
  status, payment method. A summary view with KPI tiles and charts, plus drill-down
  tables. Export to CSV.
- Performance: with 10,000+ subscriptions and 50,000+ invoices, every page and API
  endpoint responds in under 2 seconds. Use server-side pagination, proper indexes,
  and SQL aggregation (no loading everything into memory). Add a seed script that
  generates this volume and a test that asserts the latency budget.

## Differentiators (build AFTER all of the above works)
Research on Odoo Subscriptions, Chargebee, Recurly and Stripe Billing shows common
gaps. Implement these:
1. Dunning and payment recovery: configurable retry schedule (e.g. day 1, 3, 5, 7),
   automated reminder emails, grace period, and automatic suspension after the final
   failure. Failed payments are a leading source of involuntary churn, and basic
   billing tools often only retry on a fixed schedule.
2. Proration: mid-cycle upgrades, downgrades and quantity changes produce correct
   prorated credit/charge lines on the next invoice.
3. True MRR analytics: MRR movements split into New, Expansion, Contraction and Churn,
   with a monthly waterfall chart, ARR, churn rate and ARPU. Many systems mix
   proration into revenue and misreport upgrades and downgrades.
4. Billing run preview (dry-run): before the run, show exactly which invoices will be
   created, totals, and any exceptions (missing tax, inactive customer, expired plan)
   in an exceptions queue. Admin approves, then it runs.
5. Revenue-at-risk panel: overdue and failing subscriptions ranked by amount and
   days late, with one-click "send reminder".
6. Discount simulator: before saving a rule, show how many current subscriptions it
   would hit and the projected monthly impact.
7. Audit log: immutable record of who changed what (prices, plans, discounts, states).
8. Customer portal self-service: view subscriptions and invoices, download PDFs, pay or
   report a payment, pause/cancel/renew where the plan allows, and change plan or
   quantity with a live price preview.

## Non-functional
- Money stored as integer minor units or DECIMAL, never float. Single currency (INR)
  with currency code on every amount.
- All timestamps UTC, shown in the user's timezone.
- Input validation on every endpoint, consistent error format, OpenAPI docs.
- Automated tests for: password rules, unique email, RBAC (each role vs each
  protected endpoint), state transitions, billing idempotency, tax math, discount
  limits, payment-to-status logic, dashboard totals, and the latency budget.
- Docker Compose to run everything with one command. README with setup, demo
  credentials (one admin, one staff, one customer) and architecture diagram.

## Tech stack
Backend: Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL, APScheduler (or
Celery beat) for the billing job, WeasyPrint for invoice PDFs.
Frontend: React + Vite + TypeScript, Tailwind, TanStack Query, TanStack Table,
Recharts. Admin/staff app and customer portal share one codebase with role-based routes.
Testing: pytest + httpx for the API, Vitest for key UI logic, Playwright for 2 or 3
happy-path flows.
```

---

## Part C: The plan

### C.1 Steering files (put under `.kiro/steering/`)

**product.md**
```
# Product
Brightloop Subscriptions: one platform for products, plans, quotations,
subscriptions, invoices, payments and revenue reports.
Roles: ADMIN (everything), STAFF (day-to-day, limited), CUSTOMER (own data only).
Core rule: money is never wrong. No double billing, no skipped billing, no float math.
Success: every scenario in the problem statement works end to end, pages load in < 2s
with 10k subscriptions, and the differentiators are demoable.
```

**tech.md**
```
# Tech
Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL.
Frontend: React + Vite + TypeScript + Tailwind + TanStack Query/Table + Recharts.
Rules:
- Business logic lives in services/, never in route handlers.
- RBAC via a single dependency (require_role) on every route; customers are scoped by owner id.
- Money = Decimal / integer minor units. Dates in UTC.
- Every state change goes through a state-machine function that records history.
- Every list endpoint is paginated and indexed; no N+1 queries.
- Every feature ships with tests.
```

**structure.md**
```
# Structure
backend/app/{api,services,models,schemas,core,jobs,tests}
backend/alembic/
frontend/src/{pages,components,features,api,lib}
scripts/seed.py
docker-compose.yml, README.md
```

### C.2 Phased build plan

Rough timing assumes a 24 to 36 hour hackathon. Adjust to your actual time. **Phases 1 to 5 are the full problem statement. Phase 6 is what makes you unique.**

| Phase | Goal | Tasks | Done when |
|---|---|---|---|
| **0. Setup** (1h) | Project skeleton | Repo, Docker Compose (Postgres, API, web), Alembic, CI-less test runner, steering files, base layout | `docker compose up` shows a health endpoint and a blank UI |
| **1. Auth and RBAC** (3h) | Scene 1 | User model, unique email, password validator, signup, login, JWT, forgot/reset with outbox, `require_role`, admin-only "create staff", customer scoping helper, seed 3 demo users | Tests prove: duplicate email rejected, 8-char password rejected, 9-char valid one accepted, reset token single-use and expiring, staff cannot create staff, customer cannot read another customer's data |
| **2. Catalog** (3h) | Scene 2 | Product + variant attribute models and CRUD, plan model and CRUD with period, min qty, availability dates and the 4 flags, tax rules, discount rules (admin only), admin UI screens | Effective price shows 560 extra for the Odoo brand; a plan outside its dates can't be selected |
| **3. Quotes and subscriptions** (4h) | Scene 3 | Quotation templates, create-from-template, subscription with numbering, lines, totals, payment terms, state machine with history and timeline UI, pause/resume/close/renew by plan flags | Illegal transitions blocked; timeline shows every change |
| **4. Billing engine and invoices** (5h) | Scenes 4 and 5 | Invoice generator, tax calculation, discount application as invoice lines, idempotency constraint, next-billing-date advance, scheduler job, manual run button, invoice state machine, send (email) and print (PDF), sequential numbering | Running the billing job twice creates zero extra invoices; crash-resume test passes; discount stops at expiry and at usage limit; tax math tests pass |
| **5. Payments and dashboard** (4h) | Scenes 6 and 7 | Payment recording with partials, status derivation, overdue calculation, finance dashboard with KPI tiles, filters, tables, CSV export, indexes, seed script for 10k subs / 50k invoices, latency test | Totals reconcile with raw SQL; every endpoint < 2s on the seeded database |
| **6. Differentiators** (6h, in this order) | Standing out | (1) Dunning + retries + suspension, (2) proration, (3) MRR waterfall (new/expansion/contraction/churn), (4) billing dry-run preview + exceptions queue, (5) revenue-at-risk panel, (6) discount simulator, (7) audit log, (8) portal plan-change with price preview | Each is demoable in under 60 seconds |
| **7. Polish** (3h) | Judging readiness | UI pass (empty states, loading, errors), README, architecture diagram, demo data story, demo video or slides, bug bash | Fresh clone runs with one command; demo script runs cleanly 3 times |

### C.3 Data model (give this to Kiro in design.md if it drifts)

`users`, `customers`, `products`, `product_attributes`, `product_variants`, `plans`, `quotation_templates`, `quotation_template_lines`, `subscriptions`, `subscription_lines`, `subscription_history`, `taxes`, `discounts`, `discount_products`, `discount_usages`, `invoices`, `invoice_lines`, `payments`, `dunning_attempts`, `mrr_events`, `audit_log`, `email_outbox`, `password_reset_tokens`.

Indexes that matter for the 2-second budget: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer_id)`, `payments(invoice_id)`, and the unique `(subscription_id, period_start, period_end)` on invoices.

### C.4 Requirement traceability (check Kiro's `requirements.md` against this)

| Problem statement item | Covered in |
|---|---|
| Email unique per account | Phase 1 |
| Password > 8 chars, upper, lower, special | Phase 1 |
| Reset link to registered email | Phase 1 |
| Admin / staff / customer roles; only admin adds staff | Phase 1 |
| Product: name, type, sales price, cost price, notes | Phase 2 |
| Variants with price extra (Odoo brand +560) | Phase 2 |
| Plan: price, daily/weekly/monthly/yearly, min qty, dates | Phase 2 |
| Auto-close, early close, pause, renew set per plan | Phase 2 and 3 |
| Quotation template with plan, lines and validity days | Phase 3 |
| Subscription number, customer, plan, dates, payment terms, lines | Phase 3 |
| Draft, Quotation, Confirmed, Active, Closed visible to team | Phase 3 |
| Invoices auto-created from subscriptions | Phase 4 |
| Auto taxes from admin rules | Phase 2 and 4 |
| Confirm, cancel, send, print; Draft, Confirmed, Paid | Phase 4 |
| Nothing billed twice or skipped | Phase 4 |
| Discount rules: fixed or %, min purchase/qty, dates, usage limit, admin only | Phase 2 |
| Discount on products or whole subscriptions, auto on next invoice, stops at expiry or limit | Phase 4 |
| Payment: method, amount, date, note, against an invoice | Phase 5 |
| Paid vs outstanding visible; overdue chasing | Phase 5 |
| Dashboard: active subs, revenue, owed, overdue; filters and summary | Phase 5 |
| Every page under 2 seconds at thousands of subscriptions | Phase 5 |

### C.5 Why this beats other teams (the pitch in four lines)

1. Everyone will build the happy path. You will prove **correctness**: idempotent billing, tested to survive re-runs and crashes.
2. Research shows failed payments drive a large share of subscription churn (commonly estimated at 20 to 40%), and basic tools only retry on a fixed schedule. Your **dunning and revenue-at-risk** features target that directly.
3. Research shows basic MRR reporting often mishandles upgrades, downgrades and proration. Your **MRR waterfall with proration** reports them properly.
4. Odoo's own Subscriptions app is known to need extra configuration or custom development for advanced proration. A **dry-run billing preview with an exceptions queue** and a **discount simulator** show the judges you thought about the people running billing day.

### C.6 Demo script (5 minutes)

1. Sign up as a new customer. Show the weak password rejected, then accepted. Show the reset email in the outbox.
2. Log in as admin. Create a product with the Odoo brand variant (+560), a monthly plan, a 10% discount rule (simulator shows impact), and a tax rule.
3. Log in as staff. Create a quote from a template, confirm it, and show the state timeline.
4. Billing day: open the dry-run preview, show one exception in the queue, fix it, run the billing. Run it again and show zero duplicates. Open an invoice and show the auto discount and tax lines. Send it and print the PDF.
5. Record a partial payment, then a final one. Watch the status change.
6. Simulate a failed payment and show the dunning retries and the revenue-at-risk panel.
7. Open the finance dashboard on 10k+ subscriptions. Use the filters, show the MRR waterfall, and show page load times under 2 seconds.
8. Log in as the customer. Show they see only their own data, then change plan with the live price preview.

### C.7 Common mistakes to tell Kiro to avoid

- Doing RBAC only in the frontend. Enforce it on every API route.
- Using floats for money.
- Generating invoices in a loop without a transaction or unique constraint.
- Computing dashboard numbers in Python by loading all rows. Use SQL aggregates.
- Letting a customer endpoint accept a customer id from the client. Use the authenticated user.
- Treating "more than eight characters" as 8. It means 9 or more.
