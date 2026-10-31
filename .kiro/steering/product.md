# Product: Brightloop Subscriptions

One platform for products, plans, quotations, subscriptions, invoices, payments and revenue reports. It runs the full life of a subscription business: products and plans, then quotations, subscriptions, invoices, payments and revenue reporting. Customers range from small shops on monthly plans to large companies on yearly contracts.

## Core rule
Money is never wrong: no double billing, no skipped billing, no float math.

## Success criteria
- Every scenario in the problem statement works end to end.
- Every page loads in under 2 seconds with 10,000+ subscriptions and 50,000+ invoices.
- Every differentiator can be demoed in under 60 seconds.

## Roles (enforced on the backend, not just the UI)
- **ADMIN**: controls everything. Only an admin can create staff users, create discount rules, and configure taxes, plans and products.
- **STAFF**: day-to-day work with limited access. Manages customers, creates quotations and subscriptions, confirms, cancels, sends and prints invoices, and records payments. Cannot create staff, discounts or taxes.
- **CUSTOMER**: portal only. Signs up on their own and sees and manages only their own subscriptions and invoices.

## Workstreams
| Member | Workstream | Differentiators |
|---|---|---|
| 1 | Platform foundation, auth, RBAC, customers | #7 Audit log |
| 2 | Catalog, quotations, subscriptions | #2 Proration, #6 Discount simulator |
| 3 | Billing runs, invoices, payments | #1 Dunning, #4 Dry-run preview, #5 Revenue at risk |
| 4 | Finance dashboard, customer portal, shared frontend shell | #3 MRR waterfall, #8 Portal self-service |

## Source documents
- `kiro_subscription_system_plan.md`: the master prompt, the phased plan, the data model (§C.3), the requirement traceability table (§C.4) and the 5-minute demo script (§C.6). Table names in §C.3 are a shared contract.
- `TEAM_TASK_DIVISION.md`: who owns what, and the definition of done for each workstream.
