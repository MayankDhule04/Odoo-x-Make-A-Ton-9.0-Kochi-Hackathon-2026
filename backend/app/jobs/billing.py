"""Daily recurring billing job.

Can be scheduled via APScheduler / cron or triggered on demand.
"""

import logging
from datetime import date

from app.core.db import SessionLocal
from app.services.billing.engine import BillingRunResult, run_billing

logger = logging.getLogger(__name__)


def run_daily_billing_job(as_of_date: date | None = None) -> BillingRunResult:
    """Execute the daily recurring billing job in a standalone database session."""
    today = as_of_date or date.today()
    logger.info("Starting daily billing job for date: %s", today)
    with SessionLocal() as db:
        result = run_billing(db, as_of_date=today, actor=None)
        db.commit()
    logger.info(
        "Billing job completed: %d invoices created, %d skipped, total amount: %s",
        result.created_count,
        result.skipped_count,
        result.total_amount,
    )
    return result

