"""Payment endpoints (Member 3): recording payments, payment-status summary, dunning and
the revenue-at-risk panel."""

from fastapi import APIRouter, HTTPException, Query, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import CurrentPrincipal, StaffOrAdmin
from app.models.billing import Invoice
from app.models.payments import Payment
from app.schemas.payments import (
    DunningAttemptRead,
    DunningRunRequest,
    DunningRunResponse,
    MessageResponse,
    PaymentCreate,
    PaymentRead,
    PaymentStatusSummary,
    RevenueAtRiskResponse,
)
from app.services import billing as billing_service
from app.services import payments as payments_service
from app.services.payments import PaymentError

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment(body: PaymentCreate, db: DbSession, principal: CurrentPrincipal) -> Payment:
    """Staff/admin record any payment; a customer may pay/report only on their own invoice."""
    invoice = billing_service.get_invoice(db, body.invoice_id)
    if invoice is None or (principal.is_customer and invoice.customer_id != principal.customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    try:
        payment = payments_service.record_payment(db, invoice, body, actor=principal.user)
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(payment)
    return payment


@router.get("", response_model=Page[PaymentRead])
def list_payments(
    db: DbSession,
    params: PaginationDep,
    principal: CurrentPrincipal,
    invoice_id: int | None = Query(default=None, description="Filter by invoice id."),
) -> Page[PaymentRead]:
    customer_id = principal.customer_id if principal.is_customer else None
    query = payments_service.list_payments(db, invoice_id=invoice_id, customer_id=customer_id)
    return paginate(db, query, params)


@router.get("/summary", response_model=PaymentStatusSummary)
def payment_status_summary(db: DbSession, _user: StaffOrAdmin) -> PaymentStatusSummary:
    return payments_service.status_summary(db)


# --- Dunning -------------------------------------------------------------------------

@router.post("/dunning/run", response_model=DunningRunResponse)
def run_dunning(body: DunningRunRequest, db: DbSession, user: StaffOrAdmin) -> DunningRunResponse:
    result = payments_service.run_dunning(db, as_of_date=body.as_of_date, actor=user)
    db.commit()
    return result


@router.get("/dunning", response_model=Page[DunningAttemptRead])
def list_dunning(
    db: DbSession,
    params: PaginationDep,
    _user: StaffOrAdmin,
    subscription_id: int | None = Query(default=None),
    invoice_id: int | None = Query(default=None),
) -> Page[DunningAttemptRead]:
    return paginate(db, payments_service.dunning_query(subscription_id, invoice_id), params)


# --- Revenue at risk -----------------------------------------------------------------

@router.get("/revenue-at-risk", response_model=RevenueAtRiskResponse)
def revenue_at_risk(db: DbSession, _user: StaffOrAdmin) -> RevenueAtRiskResponse:
    return payments_service.revenue_at_risk(db)


@router.post("/revenue-at-risk/{subscription_id}/remind", response_model=MessageResponse)
def remind_subscription(subscription_id: int, db: DbSession, user: StaffOrAdmin) -> MessageResponse:
    sent = payments_service.send_reminder_for_subscription(db, subscription_id, actor=user)
    db.commit()
    if sent == 0:
        return MessageResponse(message="No overdue invoices for this subscription.")
    return MessageResponse(message=f"Sent {sent} reminder(s).")
