# Product: Brightloop Subscriptions

A subscription management system built for a hackathon: product catalog and plans, quotations, the subscription lifecycle, recurring invoicing, payments, dunning, a finance dashboard and a customer self-service portal.

## Roles
- **ADMIN**: everything, including the catalog, plans, tax and discount rules, and creating staff users.
- **STAFF**: day-to-day operations such as subscriptions, invoices, payments and billing runs. Cannot create staff users.
- **CUSTOMER**: signs up on their own and sees only their own subscriptions, invoices and payments.

## Workstreams
| Member | Workstream | Differentiators |
|---|---|---|
| 1 | Platform foundation, auth, RBAC | #7 Audit log |
| 2 | Catalog, quotations, subscriptions | #2 Proration, #6 Discount simulator |
| 3 | Billing runs, invoices, payments | #1 Dunning, #4 Dry-run preview, #5 Revenue at risk |
| 4 | Finance dashboard, customer portal, shared frontend shell | #3 MRR waterfall, #8 Portal self-service |

## Source documents
- `TEAM_TASK_DIVISION.md`: who owns what, and the definition of done for each workstream.
- `kiro_subscription_system_plan.md`: the master plan, the shared data model (§C.3) and the 5-minute demo script (§C.6). Table and column names in §C.3 are a shared contract.
