"""Billing endpoints (Member 3): recurring billing runs, dry-run preview, and invoices."""

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import CurrentPrincipal, Principal, StaffOrAdmin
from app.models.billing import Invoice, InvoiceStatus
from app.schemas.billing import (
    BillingRunRequest,
    BillingRunResponse,
    DryRunResponse,
    InvoiceActionRequest,
    InvoiceCreate,
    InvoiceDetail,
    InvoiceRead,
)
from app.services import billing as billing_service
from app.services.billing import InvoiceError

invoices_router = APIRouter(prefix="/invoices", tags=["invoices"])
billing_ops_router = APIRouter(prefix="/billing", tags=["billing"])


def _visible_or_404(db: DbSession, invoice_id: int, principal: Principal) -> Invoice:
    invoice = billing_service.get_invoice(db, invoice_id)
    if invoice is None or (principal.is_customer and invoice.customer_id != principal.customer_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found.",
        )
    return invoice


# --- Invoice CRUD & Lifecycle --------------------------------------------------------

@invoices_router.get("", response_model=Page[InvoiceRead])
def list_invoices(
    db: DbSession,
    params: PaginationDep,
    principal: CurrentPrincipal,
    status: InvoiceStatus | None = Query(default=None, description="Filter by invoice status."),
    customer_id: int | None = Query(default=None, description="Filter by customer id."),
    search: str | None = Query(default=None, description="Search by invoice number or customer name."),
) -> Page[InvoiceRead]:
    # Customers can only view their own invoices
    effective_customer_id = principal.customer_id if principal.is_customer else customer_id

    query = billing_service.list_invoices(
        db,
        status=status,
        customer_id=effective_customer_id,
        search=search,
    )
    query = principal.scope(query, Invoice.customer_id)
    return paginate(db, query, params)


@invoices_router.get("/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(
    invoice_id: int,
    db: DbSession,
    principal: CurrentPrincipal,
) -> Invoice:
    return _visible_or_404(db, invoice_id, principal)


@invoices_router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    body: InvoiceCreate,
    db: DbSession,
    user: StaffOrAdmin,
) -> Invoice:
    try:
        invoice = billing_service.create_invoice(db, body, actor=user)
    except InvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(invoice)
    return invoice


@invoices_router.post("/{invoice_id}/confirm", response_model=InvoiceRead)
def confirm_invoice(
    invoice_id: int,
    db: DbSession,
    user: StaffOrAdmin,
) -> Invoice:
    invoice = billing_service.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    try:
        invoice = billing_service.confirm_invoice(db, invoice, actor=user)
    except InvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(invoice)
    return invoice


@invoices_router.post("/{invoice_id}/cancel", response_model=InvoiceRead)
def cancel_invoice(
    invoice_id: int,
    db: DbSession,
    user: StaffOrAdmin,
    body: InvoiceActionRequest = InvoiceActionRequest(),
) -> Invoice:
    invoice = billing_service.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    try:
        invoice = billing_service.cancel_invoice(db, invoice, actor=user, reason=body.note)
    except InvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(invoice)
    return invoice


@invoices_router.post("/{invoice_id}/send")
def send_invoice(
    invoice_id: int,
    db: DbSession,
    user: StaffOrAdmin,
) -> dict[str, str]:
    invoice = billing_service.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    try:
        billing_service.send_invoice(db, invoice, actor=user)
    except InvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return {"message": f"Invoice {invoice.number} sent to customer."}


@invoices_router.get("/{invoice_id}/render", response_class=HTMLResponse)
def render_invoice(
    invoice_id: int,
    db: DbSession,
    principal: CurrentPrincipal,
) -> HTMLResponse:
    invoice = _visible_or_404(db, invoice_id, principal)
    html = billing_service.render_invoice_html(invoice)
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)


# --- Dry-run preview & billing run operations ----------------------------------------

@billing_ops_router.post("/dry-run", response_model=DryRunResponse)
def dry_run_billing(
    body: BillingRunRequest,
    db: DbSession,
    user: StaffOrAdmin,
) -> DryRunResponse:
    """Preview upcoming recurring invoice creation and review exceptions."""
    return billing_service.preview_billing_run(db, as_of_date=body.as_of_date)


@billing_ops_router.post("/run", response_model=BillingRunResponse)
def execute_billing_run(
    body: BillingRunRequest,
    db: DbSession,
    user: StaffOrAdmin,
) -> BillingRunResponse:
    """Execute recurring billing run idempotently and advance next_billing_date."""
    result = billing_service.run_billing(db, as_of_date=body.as_of_date, actor=user)
    db.commit()
    return BillingRunResponse(
        as_of_date=result.as_of_date,
        created_count=result.created_count,
        skipped_count=result.skipped_count,
        total_amount=result.total_amount,
        invoices=result.invoices,
    )


# Combined router mounting both /invoices and /billing, as well as /billing/invoices alias
router = APIRouter()
router.include_router(invoices_router)
router.include_router(billing_ops_router)
router.include_router(invoices_router, prefix="/billing")
