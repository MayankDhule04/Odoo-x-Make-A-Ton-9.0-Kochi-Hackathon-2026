# Brightloop Subscriptions — 5-minute demo script

Run `docker compose up --build`, open http://localhost:5173, and have the API docs ready at
http://localhost:8000/api/docs. The seed creates the three demo accounts and a small demo
catalog (a product with the Odoo brand variant +560, a monthly plan, GST 18%, a 10% discount).

Demo accounts: `admin@brightloop.dev` / `Admin@12345`, `staff@brightloop.dev` / `Staff@12345`,
`customer@brightloop.dev` / `Customer@12345`.

## 0. Sign-up & auth (30s)
1. Log out, go to **Sign up**. Type a weak password → the checklist rejects it (needs 9+ chars,
   upper, lower, special). Fix it → account created as a CUSTOMER.
2. Mention **Forgot password** writes a single-use reset link to the dev **Email Outbox** (admin page).

## 1. Catalog as ADMIN (60s)
Log in as **admin**. Open **Catalog**.
1. **Products** tab → open "Brightloop Pro". Show the **Odoo** variant: base ₹1000 + ₹560 extra =
   **effective price ₹1560**, and the computed margin.
2. **Discounts** tab → create a 10% rule, click **Simulate reach** → it shows how many active
   subscriptions it would hit and the **projected monthly impact** (#6 discount simulator).
3. **Taxes** tab → show the GST 18% rule.
4. Open **Plans** → note the availability window and the **Selectable now** column (a plan outside
   its dates can't be used for a new subscription).

## 2. Quote → subscription as STAFF (60s)
Log in as **staff**. Open **Quotation Templates**, then **Subscriptions → New Subscription**.
1. Create from a template (or manually): pick the customer, plan, and a product line.
2. Open the subscription. Walk the lifecycle with the buttons: **Submit → Confirm → Activate**.
   Point at the **timeline** recording every transition (who/when/from/to).
3. Try an illegal move earlier (e.g. Activate on a draft) → rejected (409).

## 3. Billing day as STAFF (60s)
Open **Billing / Invoices**.
1. Click **Dry-run preview** → see which invoices will be created, totals, and the **exceptions
   queue** (#4). Fix an exception if shown.
2. Run the billing. **Run it again** → zero duplicates (idempotent).
3. Open an invoice → show the tax and discount lines. **Send** it (lands in the outbox) and
   **View** the printable invoice.

## 4. Payments & recovery (45s)
Open **Payments**.
1. Record a **partial** payment on an invoice, then the rest → the invoice flips to **PAID**.
2. **Revenue at risk** tab → overdue subscriptions ranked by amount and days late; click
   **Send reminder** (#5).
3. **Dunning** tab → **Run dunning now** → reminders logged for days 1/3/5/7 and, past the final
   notice, the subscription is **auto-suspended** (#1).

## 5. Finance dashboard (45s)
Open **Dashboard**.
1. KPI tiles: active subs, revenue collected, amount owed, overdue, **MRR / ARR / ARPU / churn**.
2. The **MRR waterfall** chart: New / Expansion / Contraction / Churn by month (#3).
3. Click **Export invoices CSV** / **Export payments CSV**.
4. Mention the latency test: dashboard stays under 2 seconds at thousands of invoices.

## 6. Customer portal (40s)
Log in as **customer**.
1. **My Subscriptions** → you only see your own. Click **Change** on an active one, adjust the
   quantity, and **Preview** → a live **prorated** credit/charge and the amount to pay now (#2, #8).
   Confirm the change.
2. Use **Pause / Cancel / Renew** where the plan allows.
3. **My Invoices** → view an invoice and **Pay** it.

## Closing line
"Everyone builds the happy path. Brightloop proves **correctness** — idempotent billing that
survives re-runs — and adds the operator features that matter: dunning, a dry-run with an
exceptions queue, a true MRR waterfall, proration, a discount simulator, an immutable audit log,
and a self-service portal."
