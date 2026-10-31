"""Reporting endpoints (Member 4): finance dashboard, MRR analytics and CSV exports."""

from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.core.db import DbSession
from app.core.rbac import StaffOrAdmin
from app.models.billing import InvoiceStatus
from app.schemas.reporting import DashboardSummary, MrrAnalytics
from app.services import reporting as reporting_service

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(
    db: DbSession,
    _user: StaffOrAdmin,
    start: date | None = Query(default=None, description="Revenue window start (paid_at)."),
    end: date | None = Query(default=None, description="Revenue window end (paid_at)."),
    customer_id: int | None = Query(default=None),
    plan_id: int | None = Query(default=None),
) -> DashboardSummary:
    return reporting_service.dashboard_summary(
        db, start=start, end=end, customer_id=customer_id, plan_id=plan_id
    )


@router.get("/mrr", response_model=MrrAnalytics)
def mrr(db: DbSession, _user: StaffOrAdmin) -> MrrAnalytics:
    return reporting_service.mrr_analytics(db)


@router.get("/invoices.csv", response_class=PlainTextResponse)
def export_invoices_csv(
    db: DbSession,
    _user: StaffOrAdmin,
    status: InvoiceStatus | None = Query(default=None),
    customer_id: int | None = Query(default=None),
) -> PlainTextResponse:
    csv_text = reporting_service.invoices_csv(db, status=status, customer_id=customer_id)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices.csv"},
    )


@router.get("/payments.csv", response_class=PlainTextResponse)
def export_payments_csv(
    db: DbSession,
    _user: StaffOrAdmin,
    customer_id: int | None = Query(default=None),
) -> PlainTextResponse:
    csv_text = reporting_service.payments_csv(db, customer_id=customer_id)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments.csv"},
    )
