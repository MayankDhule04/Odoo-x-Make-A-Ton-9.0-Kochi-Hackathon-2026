# Brightloop Subscriptions — Team Task Division (4 Members)

This document splits the build plan in `kiro_subscription_system_plan.md` into **four
domain-aligned workstreams**, one per team member. Each section lists the scope, what
"done" looks like, the files you own, and a **ready-to-paste Kiro prompt** so everyone
builds against the same contract.

Read `kiro_subscription_system_plan.md` fully before starting. This doc only says *who
does what*. The master prompt, steering files, data model and demo script live there.

---

## 0. Team roster

Fill this in so commits map to people.

| Member | Name | GitHub handle | Workstream |
|---|---|---|---|
| 1 | _(team lead)_ | | Platform Foundation, Auth & RBAC |
| 2 | | | Catalog & Subscriptions |
| 3 | | | Billing, Invoices & Payments |
| 4 | | | Reporting, Portal & Frontend |

---

## 1. Submission & commit rules (read first — this affects scoring)

These come from the hackathon repository guidelines and **directly impact evaluation**:

- The repo is **public** and submitted through the portal by the Team Leader **before 10:00 AM**.
- **Your latest code must always be on the `main` branch.**
- **Every member pushes their own code at least once every hour.** Do not let one person
  commit for the whole team. Individual commits are used to measure each member's contribution.
- **Each member commits under their own Git identity.** Before your first commit, set it:
  ```bash
  git config user.name "Your Name"
  git config user.email "your-github-email@example.com"
  ```
- Write **clear commit messages** that explain what you did, e.g.
  `feat(auth): add password validator rejecting <=8 char passwords` not `update`.

### Branch & merge workflow (keeps `main` always working)
1. Pull latest `main` before you start: `git pull origin main`.
2. Work on a short-lived branch: `git checkout -b m2-catalog`.
3. Commit small and often with messages scoped to your workstream.
4. Push your branch, open a PR into `main`, get a quick teammate review, merge.
5. Alternatively (fast hackathon mode) commit straight to `main`, but **always pull before
   you push** and keep commits small to avoid conflicts.
6. Because work is split by folder/domain (see each section), conflicts should be rare.

### Suggested commit message prefixes per member
- Member 1: `feat(core)`, `feat(auth)`, `chore(infra)`
- Member 2: `feat(catalog)`, `feat(subs)`
- Member 3: `feat(billing)`, `feat(payments)`
- Member 4: `feat(dashboard)`, `feat(portal)`, `feat(ui)`

---

## 2. How the work is split (overview)

The split follows the phases in the plan but groups them by **domain**, so each person owns
a vertical slice (backend models + services + API + the matching UI) and the differentiators
that belong to their domain.

| Member | Phases from the plan | Differentiators owned | Primary folders |
|---|---|---|---|
| **1. Foundation, Auth & RBAC** | 0 (Setup), 1 (Auth/RBAC), part of 7 (README, Docker, diagram) | #7 Audit log | `backend/app/core`, `backend/app/api/auth`, `docker-compose.yml`, `scripts/`, `.kiro/steering/` |
| **2. Catalog & Subscriptions** | 2 (Catalog), 3 (Quotes & Subscriptions) | #2 Proration, #6 Discount simulator | `backend/app/{models,services,api}/catalog`, `.../subscriptions`, `frontend/src/features/catalog`, `.../subscriptions` |
| **3. Billing, Invoices & Payments** | 4 (Billing engine & invoices), 5a (Payments) | #1 Dunning, #4 Dry-run preview, #5 Revenue-at-risk | `backend/app/{models,services,api,jobs}/billing`, `.../payments`, `frontend/src/features/invoices`, `.../payments` |
| **4. Reporting, Portal & Frontend** | 5b (Dashboard, seed, latency), part of 7 (UI polish) | #3 MRR waterfall, #8 Customer portal self-service | `backend/app/{services,api}/reporting`, `frontend/src/{pages,components,lib}`, `frontend/src/features/portal` |

### Dependency order (who unblocks whom)
```
Member 1 (Phase 0 + Auth)  ──►  everyone (nobody can build until the skeleton + auth exist)
        │
        ├──►  Member 2 (needs user/RBAC + DB)
        ├──►  Member 3 (needs subscriptions from M2 for real billing; can start on stubs/fixtures)
        └──►  Member 4 (needs invoices/payments from M3 + seed data; can start on UI shell + charts with mock data)
```
**Day-1 rule:** Member 1 delivers Phase 0 (skeleton + Docker + DB + one migration) and the
`User`/auth scaffolding **first**, within the first ~2 hours, so the other three can run the
app locally and start their slices. While waiting, Members 2–4 scaffold their UI shells and
write their Kiro requirements/design against the shared data model in the plan.

---

## 3. Member 1 — Platform Foundation, Auth & RBAC

**Scope (plan Phase 0, Phase 1, Differentiator #7, part of Phase 7)**
- Project skeleton, Docker Compose (Postgres + API + web), Alembic baseline, test runner.
- The three steering files under `.kiro/steering/` (`product.md`, `tech.md`, `structure.md`).
- `User` model, unique case-insensitive email, password validator (**>8 chars = 9+**, upper,
  lower, special), signup (always CUSTOMER), login, JWT access + refresh, rate limiting.
- Forgot/reset password with single-use 30-min hashed token + dev **email outbox** screen.
- `require_role` dependency enforcing RBAC on **every** route; customer-scoping helper that
  forces customer queries to the authenticated user id.
- Admin-only "create staff user" endpoint. Seed script for 3 demo users (admin/staff/customer).
- Differentiator #7: immutable **audit log** of who changed what (prices, plans, discounts, states).
- Part of Phase 7: README (setup, demo credentials, architecture diagram), one-command Docker run.

**Done when**
- `docker compose up` brings up DB + API health endpoint + blank UI.
- Tests prove: duplicate email rejected; 8-char password rejected; 9-char valid accepted;
  reset token single-use and expiring; staff cannot create staff; a customer cannot read
  another customer's data.
- Every protected route goes through `require_role`; audit log records a sample change.

**Ready-to-paste Kiro prompt**
```
You are building the foundation of "Brightloop Subscriptions" (see the master prompt and
steering files). Scope this spec to ONLY the following; stub or leave interfaces for the rest.

1. Project skeleton per structure.md: backend/app/{api,services,models,schemas,core,jobs,tests},
   backend/alembic/, frontend/src/{pages,components,features,api,lib}, scripts/seed.py,
   docker-compose.yml (Postgres + FastAPI + React/Vite), README.md. One-command `docker compose up`.
2. Auth & RBAC:
   - User model with CUSTOMER/STAFF/ADMIN roles. Email unique case-insensitively.
   - Password rule: MORE than 8 chars (>=9), >=1 upper, >=1 lower, >=1 special. Validate on
     server (and expose rules to the client). Hash with argon2 or bcrypt.
   - Signup (always creates CUSTOMER), login, JWT access + refresh, rate-limit login/reset.
   - Forgot/reset: single-use token expiring in 30 min, store only its hash, send a reset
     link via SMTP with a dev fallback that writes to a viewable "outbox" screen + console.
     Never reveal whether an email exists.
   - require_role dependency used on every protected route. A customer-scoping helper that
     forces every customer-scoped query to the authenticated user's id (never trust a client id).
   - Admin-only endpoint to create STAFF users.
   - Seed script: 1 admin, 1 staff, 1 customer (document the credentials in the README).
3. Audit log (differentiator #7): immutable table + service recording who/when/what for
   changes to prices, plans, discounts and record states. Expose a read API for admins.
Generate requirements.md (EARS), design.md, tasks.md. Money = Decimal/integer minor units,
timestamps UTC. Write tests for: unique email, password rule (8 rejected, 9 accepted), reset
token single-use + expiry, RBAC (each role vs protected endpoints), customer data isolation.
Do not implement catalog, subscriptions, billing, payments or dashboards — leave typed stubs.
```

---

## 4. Member 2 — Catalog & Subscriptions

**Scope (plan Phase 2, Phase 3, Differentiators #2 and #6)**
- Products (name, type, sales/cost price, notes, computed margin) + variant attributes with
  price extra (effective price = base + variant extra; Odoo brand +560).
- Plans: price, billing period (DAILY/WEEKLY/MONTHLY/YEARLY), min qty, available-from/to,
  and the 4 flags (auto-close, allow early close, allow pause, allow renew). A plan outside
  its window cannot be used for new subscriptions.
- Tax rules and discount rules are **defined** here (admin-only CRUD). *(Applying tax/discount
  to invoices is Member 3.)*
- Quotation templates (preset plan + product lines, validity days); create-from-template, editable.
- Subscription: auto number (SUB-2026-000123), customer, plan, dates, payment terms, lines
  (product/variant, qty, unit price, taxes, amount).
- State machine DRAFT→QUOTATION→CONFIRMED→ACTIVE→CLOSED with rejected illegal transitions,
  a history table (who/when/from/to) and a **timeline UI**. Pause/resume/early-close/renew
  gated by the plan flags.
- Differentiator #2 **Proration**: mid-cycle upgrades/downgrades/qty changes compute correct
  prorated credit/charge lines (surface them for Member 3's next invoice).
- Differentiator #6 **Discount simulator**: before saving a rule, show how many current
  subscriptions it would hit and projected monthly impact.
- Admin UI screens for catalog + the subscription timeline.

**Done when**
- Effective price shows +560 for the Odoo brand variant; a plan outside its dates can't be selected.
- Illegal state transitions are blocked; the timeline shows every change with actor + time.
- Proration produces correct credit/charge lines on a change; discount simulator returns counts/impact.

**Ready-to-paste Kiro prompt**
```
You are building the Catalog & Subscriptions domain of "Brightloop Subscriptions" (see master
prompt + steering). Assume Member 1's auth, User model, RBAC (require_role), audit log and the
DB/Docker skeleton already exist — import and use them, do not reimplement them.

Scope this spec to ONLY:
1. Products: name, type (service/software/add-on/physical), sales price, cost price, notes,
   computed margin. Variants by attribute (e.g. Brand=Odoo +560), each with a price extra;
   effective price = base + variant extra. Admin-only CRUD.
2. Plans: name, price, period (DAILY/WEEKLY/MONTHLY/YEARLY), min qty, available-from/to, and
   flags auto-close/allow-early-close/allow-pause/allow-renew. Reject use of a plan outside its
   availability window for new subscriptions. Admin-only CRUD.
3. Tax rules and discount rules: admin-only CRUD only (name, %/fixed, applies-to, inclusive/
   exclusive for tax; type/min purchase/min qty/start/end/usage limit/target for discount).
   Do NOT apply them to invoices here — that is the billing domain.
4. Quotation templates (plan + product lines + validity days) and create-from-template (editable).
5. Subscriptions: auto number SUB-YYYY-###### , customer, plan, start/expiry dates, payment
   terms (Immediate/Net 15/Net 30), lines (product+variant, qty, unit price, taxes, amount).
   State machine DRAFT->QUOTATION->CONFIRMED->ACTIVE->CLOSED through a single transition
   function that records history (who/when/from/to) and rejects illegal transitions. Pause/
   resume/early-close/renew gated by plan flags. Timeline UI of the history.
6. Differentiator proration: mid-cycle upgrade/downgrade/qty change produces correct prorated
   credit/charge lines; expose them so the billing run can add them to the next invoice.
7. Differentiator discount simulator: given a draft discount rule, return how many current
   subscriptions match and the projected monthly impact.
Generate requirements.md (EARS), design.md, tasks.md. Money = Decimal/integer minor units,
dates UTC. Tests: effective price math, plan availability enforcement, every illegal state
transition rejected, history completeness, proration math, simulator counts. Build the admin
catalog screens and the subscription timeline in the shared React app with role-based routes.
```

---

## 5. Member 3 — Billing Engine, Invoices & Payments

**Scope (plan Phase 4, Phase 5a, Differentiators #1, #4, #5)**
- Invoice generator from due subscriptions (customer, lines, taxes, totals pre-filled).
- **Idempotent, transactional** billing run: unique `(subscription_id, period_start, period_end)`
  + `next_billing_date` advance in the same transaction. Re-run same day = 0 duplicates;
  crash mid-run is safely resumable.
- Tax engine applying Member 2's admin tax rules per line; discount application as its own
  invoice discount line (stops at expiry / usage limit; usage increments atomically on confirm).
- Scheduler (APScheduler/Celery beat) daily job + manual run button for ADMIN/STAFF.
- Invoice state machine DRAFT→CONFIRMED→PAID (+ CANCELLED); confirmed invoices immutable;
  send (email) and print (PDF via WeasyPrint); sequential invoice numbers, no gaps per year.
- Payments: method (card/bank/UPI/cash/cheque), amount, date, note; partial payments; invoice
  becomes PAID when fully paid; overpayment handling (reject OR store as credit — document which).
- Status derivation (paid/partial/outstanding/overdue) and overdue-by-N-days.
- Differentiator #1 **Dunning**: configurable retry schedule (day 1/3/5/7), reminder emails,
  grace period, auto-suspension after final failure.
- Differentiator #4 **Dry-run preview**: before a run, show which invoices will be created,
  totals, and exceptions (missing tax, inactive customer, expired plan) in an exceptions queue;
  admin approves, then it runs.
- Differentiator #5 **Revenue-at-risk panel**: overdue/failing subscriptions ranked by amount
  and days late, with one-click "send reminder".

**Done when**
- Running the billing job twice creates zero extra invoices; crash-resume test passes.
- Discount stops at expiry and at usage limit; tax math tests pass.
- Partial then final payment flips the invoice to PAID; dunning retries + suspension fire on
  a simulated failure; dry-run shows one exception that can be fixed then run.

**Ready-to-paste Kiro prompt**
```
You are building the Billing, Invoices & Payments domain of "Brightloop Subscriptions" (see
master prompt + steering). Assume Member 1's auth/RBAC/audit/skeleton and Member 2's
subscriptions, plans, tax rules and discount rules already exist — import and use them.

Scope this spec to ONLY:
1. Invoice generation from subscriptions that are due: pre-fill customer, lines, taxes, totals.
   The billing run MUST be idempotent and transactional: unique constraint on
   (subscription_id, period_start, period_end) AND advance next_billing_date in the SAME
   transaction. A same-day re-run creates zero duplicates; a crash mid-run is safely resumable.
2. Tax engine applying admin tax rules per line (inclusive/exclusive). Discount application as a
   separate invoice discount line; a rule stops at expiry or when its usage limit is reached;
   usage count increments atomically and only when an invoice is confirmed.
3. Scheduler (APScheduler or Celery beat) daily job + a manual "run billing" action for ADMIN/STAFF.
4. Invoice state machine DRAFT->CONFIRMED->PAID plus CANCELLED. Confirmed invoices immutable
   (corrections via cancel + re-issue or credit note). Send via email, print to PDF (WeasyPrint).
   Sequential invoice numbers with no gaps per year.
5. Payments: method (card/bank transfer/UPI/cash/cheque), amount, date, note, against an invoice.
   Partial payments; invoice becomes PAID when fully paid. Overpayment: pick reject OR store as
   credit and document it. Derive paid/partially-paid/outstanding/overdue and overdue-by-N-days.
6. Differentiator dunning: configurable retry schedule (e.g. day 1,3,5,7), reminder emails, grace
   period, automatic suspension after the final failure.
7. Differentiator dry-run preview: before running, list which invoices will be created, totals,
   and exceptions (missing tax, inactive customer, expired plan) in an exceptions queue; admin
   approves then it runs.
8. Differentiator revenue-at-risk: overdue/failing subscriptions ranked by amount + days late,
   with one-click "send reminder".
Generate requirements.md (EARS), design.md, tasks.md. Money = Decimal/integer minor units, UTC.
Tests: billing idempotency (double run = 0 dupes), crash-resume, tax math, discount expiry +
usage-limit, sequential numbering, payment-to-status logic, dunning schedule + suspension.
Build the invoice + payment + dry-run + revenue-at-risk screens in the shared React app.
```

---

## 6. Member 4 — Reporting Dashboard, Customer Portal & Frontend

**Scope (plan Phase 5b, Differentiators #3 and #8, part of Phase 7)**
- Finance dashboard (one page): active subscriptions count, revenue collected, amount owed,
  overdue invoices list, payments list. Filters: date range, customer, plan, status, method.
  KPI tiles + charts + drill-down tables + CSV export.
- **Performance**: 10k+ subscriptions, 50k+ invoices, every page/endpoint < 2s. Server-side
  pagination, proper indexes, SQL aggregation (no loading everything into memory). Seed script
  for that volume + a latency test asserting the budget.
- Differentiator #3 **True MRR analytics**: MRR movements split into New/Expansion/Contraction/
  Churn, monthly waterfall chart, ARR, churn rate, ARPU.
- Differentiator #8 **Customer portal self-service**: customer views own subscriptions +
  invoices, downloads PDFs, pays/reports a payment, pause/cancel/renew where the plan allows,
  change plan/quantity with a **live price preview** (uses Member 2's proration).
- Part of Phase 7: shared UI polish — empty/loading/error states, consistent layout, demo data story.
- Owns the shared frontend shell: routing, role-based navigation, API client, chart/table libs.

**Done when**
- Dashboard totals reconcile with raw SQL; every endpoint < 2s on the seeded 10k/50k database.
- MRR waterfall renders New/Expansion/Contraction/Churn correctly across months.
- Customer sees only their own data; plan change shows a correct live price preview before confirm.

**Ready-to-paste Kiro prompt**
```
You are building the Reporting Dashboard, Customer Portal and shared frontend of "Brightloop
Subscriptions" (see master prompt + steering). Assume Member 1's auth/RBAC/skeleton, Member 2's
subscriptions/plans/proration, and Member 3's invoices/payments already exist — consume their
APIs; do not reimplement them.

Scope this spec to ONLY:
1. Finance dashboard (one page): active subscriptions count, revenue collected, amount owed,
   overdue invoices list, payments list. Filters: date range, customer, plan, status, payment
   method. KPI tiles + charts + drill-down tables + CSV export. All numbers via SQL aggregation,
   never by loading rows into memory.
2. Performance: assume 10,000+ subscriptions and 50,000+ invoices. Every page and endpoint must
   respond in under 2 seconds via server-side pagination, proper indexes
   (subscriptions(status,next_billing_date), invoices(status,due_date), invoices(customer_id),
   payments(invoice_id)) and SQL aggregates. Provide scripts/seed.py that generates this volume
   and a test asserting the <2s latency budget on key endpoints.
3. Differentiator MRR analytics: compute MRR movements split into New, Expansion, Contraction,
   Churn; render a monthly waterfall chart; also show ARR, churn rate and ARPU. Keep proration
   out of recognized MRR so upgrades/downgrades report correctly.
4. Differentiator customer portal self-service: authenticated customer sees ONLY their own
   subscriptions + invoices, downloads invoice PDFs, pays or reports a payment, and pauses/
   cancels/renews where the plan allows. Change plan or quantity with a LIVE price preview that
   reuses the proration service. Every customer query is scoped to the authenticated user id.
5. Shared frontend shell: React + Vite + TS + Tailwind + TanStack Query/Table + Recharts, with
   role-based routes for admin/staff vs customer. Consistent empty/loading/error states.
Generate requirements.md (EARS), design.md, tasks.md. Tests: dashboard totals reconcile with raw
SQL, latency budget on the seeded DB, MRR waterfall math, and customer data isolation in the portal.
```

---

## 7. Integration checkpoints

Sync as a team at these points so the slices fit together:

1. **After Member 1's Phase 0 + auth land on `main`** — everyone pulls, confirms `docker compose up`
   works, and confirms the shared data model names match `kiro_subscription_system_plan.md` §C.3.
2. **After Member 2's subscriptions land** — Member 3 switches billing from fixtures to real
   subscriptions; Member 4 wires the portal subscription views.
3. **After Member 3's invoices + payments land** — Member 4 points the dashboard at real data and
   runs the seed + latency test.
4. **Before the demo** — run the 5-minute demo script in `kiro_subscription_system_plan.md` §C.6
   end to end, three times, on a fresh clone.

### Shared contracts nobody may break alone
- The data model table/column names in §C.3 of the plan.
- Money as Decimal/integer minor units; dates in UTC — no floats anywhere.
- `require_role` on every protected route; customer queries scoped to the authenticated user.
- Every state change goes through a state-machine function that writes history.

If you need to change a shared contract, post it to the team and update the plan doc first.
