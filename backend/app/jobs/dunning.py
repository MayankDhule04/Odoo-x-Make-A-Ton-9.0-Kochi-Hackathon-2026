"""Daily dunning job: send overdue reminders and auto-suspend after the final notice.

Schedule alongside the billing job (APScheduler / cron) or trigger on demand.
"""

import logging
from datetime import date

from app.core.db import SessionLocal
from app.schemas.payments import DunningRunResponse
from app.services.payments.dunning import run_dunning

logger = logging.getLogger(__name__)


def run_daily_dunning_job(as_of_date: date | None = None) -> DunningRunResponse:
    today = as_of_date or date.today()
    logger.info("Starting daily dunning job for date: %s", today)
    with SessionLocal() as db:
        result = run_dunning(db, as_of_date=today, actor=None)
        db.commit()
    logger.info(
        "Dunning job completed: %d invoices processed, %d reminders, %d suspensions",
        result.invoices_processed,
        result.reminders_sent,
        result.suspensions,
    )
    return result
