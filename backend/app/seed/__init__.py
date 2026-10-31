"""Demo data steps, run in order by scripts/seed.py.

The API container runs scripts/seed.py on every start, so each step must be idempotent
(safe to run again) and fast. Put large-volume data (10k subscriptions, 50k invoices)
behind a separate command instead.
"""
