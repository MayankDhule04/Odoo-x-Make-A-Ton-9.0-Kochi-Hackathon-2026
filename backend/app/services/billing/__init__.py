"""Billing services (Member 3): billing run engine, dry-run preview, and invoices."""

from app.services.billing.calculator import (
    CalculationResult,
    calculate_subscription_invoice,
    compute_tax,
)
from app.services.billing.dry_run import preview_billing_run
from app.services.billing.engine import (
    BillingRunResult,
    calculate_due_date,
    run_billing,
)
from app.services.billing.invoices import (
    InvoiceError,
    cancel_invoice,
    confirm_invoice,
    create_invoice,
    get_invoice,
    list_invoices,
    render_invoice_html,
    send_invoice,
)

__all__ = [
    "BillingRunResult",
    "CalculationResult",
    "InvoiceError",
    "calculate_due_date",
    "calculate_subscription_invoice",
    "cancel_invoice",
    "compute_tax",
    "confirm_invoice",
    "create_invoice",
    "get_invoice",
    "list_invoices",
    "preview_billing_run",
    "render_invoice_html",
    "run_billing",
    "send_invoice",
]

