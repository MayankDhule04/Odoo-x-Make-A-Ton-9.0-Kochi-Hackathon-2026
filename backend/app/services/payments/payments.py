"""Payment recording and invoice payment-status derivation.

Services flush but do not commit; the route commits. Overpayment is rejected (documented).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.billing import Invoice, InvoiceStatus
from app.models.payments import Payment
from app.schemas.payments import PaymentCreate, PaymentStatusSummary
from app.services.audit import record_audit

ZERO = Decimal("0.00")


class PaymentError(ValueError):
    """Raised when a payment can't be recorded (wrong invoice state or overpayment)."""


def record_payment(db: Session, invoice: Invoice, data: PaymentCreate, *, actor: User) -> Payment:
    if invoice.status is InvoiceStatus.DRAFT:
        raise PaymentError("Confirm the invoice before recording a payment.")
    if invoice.status is InvoiceStatus.CANCELLED:
        raise PaymentError("Cannot record a payment against a cancelled invoice.")
    if invoice.status is InvoiceStatus.PAID:
        raise PaymentError("This invoice is already fully paid.")

    amount_due = invoice.amount_total - invoice.amount_paid
    if data.amount > amount_due:
        raise PaymentError(
            f"Payment of {data.amount} exceeds the amount due ({amount_due}). "
            "Overpayment is not allowed."
        )

    payment = Payment(
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        amount=data.amount,
        method=data.method,
        paid_at=data.paid_at,
        note=data.note,
    )
    db.add(payment)

    invoice.amount_paid = invoice.amount_paid + data.amount
    became_paid = invoice.amount_paid >= invoice.amount_total
    if became_paid:
        invoice.status = InvoiceStatus.PAID

    db.flush()
    record_audit(
        db, actor=actor, entity_type="invoice", entity_id=invoice.id, action="payment",
        changes={
            "amount": str(data.amount),
            "method": data.method.value,
            "amount_paid": str(invoice.amount_paid),
            "status": invoice.status.value,
        },
    )
    return payment


def list_payments(db: Session, *, invoice_id: int | None = None, customer_id: int | None = None) -> Select:
    query = select(Payment).order_by(Payment.id.desc())
    if invoice_id is not None:
        query = query.where(Payment.invoice_id == invoice_id)
    if customer_id is not None:
        query = query.where(Payment.customer_id == customer_id)
    return query


def get_payment(db: Session, payment_id: int) -> Payment | None:
    return db.get(Payment, payment_id)


def status_summary(db: Session, today: date | None = None) -> PaymentStatusSummary:
    """Counts of invoices by derived payment state, using SQL aggregation."""
    today = today or date.today()
    due = Invoice.amount_total - Invoice.amount_paid
    open_states = (InvoiceStatus.DRAFT, InvoiceStatus.CONFIRMED)

    paid = db.scalar(select(func.count()).where(Invoice.status == InvoiceStatus.PAID)) or 0
    partially_paid = (
        db.scalar(
            select(func.count()).where(
                Invoice.status.in_(open_states), Invoice.amount_paid > ZERO, due > ZERO
            )
        )
        or 0
    )
    overdue = (
        db.scalar(
            select(func.count()).where(
                Invoice.status.in_(open_states), due > ZERO, Invoice.due_date < today
            )
        )
        or 0
    )
    # Outstanding = open, unpaid balance, not yet overdue.
    outstanding = (
        db.scalar(
            select(func.count()).where(
                Invoice.status.in_(open_states), due > ZERO, Invoice.due_date >= today
            )
        )
        or 0
    )
    total_outstanding = (
        db.scalar(select(func.coalesce(func.sum(due), ZERO)).where(Invoice.status.in_(open_states), due > ZERO))
        or ZERO
    )
    total_overdue = (
        db.scalar(
            select(func.coalesce(func.sum(due), ZERO)).where(
                Invoice.status.in_(open_states), due > ZERO, Invoice.due_date < today
            )
        )
        or ZERO
    )
    return PaymentStatusSummary(
        paid=paid,
        partially_paid=partially_paid,
        outstanding=outstanding,
        overdue=overdue,
        total_outstanding=total_outstanding,
        total_overdue=total_overdue,
    )
