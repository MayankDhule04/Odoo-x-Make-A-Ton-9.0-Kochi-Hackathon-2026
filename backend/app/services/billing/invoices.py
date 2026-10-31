"""Invoice management: creation, lifecycle transitions, printing and emailing.

State machine: DRAFT -> CONFIRMED -> PAID (plus CANCELLED).
Confirmed invoices are immutable; corrections happen through cancellation and re-issuance.
Numbering: INV-<year>-<zero-padded id>, sequential without gaps.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.billing import DiscountUsage, Invoice, InvoiceLine, InvoiceStatus
from app.models.catalog import Discount
from app.models.customers import Customer
from app.models.subscriptions import Subscription
from app.schemas.billing import InvoiceCreate
from app.services.audit import record_audit
from app.services.email import send_email

ZERO = Decimal("0.00")


class InvoiceError(ValueError):
    """Raised for illegal invoice transitions or invalid operations."""


def _next_invoice_number(db: Session, year: int) -> tuple[int, str]:
    """Reserve next sequential invoice id and format INV-YYYY-######."""
    # Attempt Postgres sequence first
    try:
        seq_id = db.execute(text("SELECT nextval('invoices_id_seq')")).scalar_one()
    except Exception:
        # Fallback for environments without the sequence or sqlite
        max_id = db.scalar(select(func.max(Invoice.id))) or 0
        seq_id = max_id + 1
    return int(seq_id), f"INV-{year}-{int(seq_id):06d}"


def create_invoice(
    db: Session,
    data: InvoiceCreate,
    *,
    actor: User | None = None,
) -> Invoice:
    """Create a manual DRAFT invoice with lines."""
    customer = db.get(Customer, data.customer_id)
    if customer is None:
        raise InvoiceError(f"Customer {data.customer_id} not found.")

    if data.subscription_id:
        sub = db.get(Subscription, data.subscription_id)
        if sub is None:
            raise InvoiceError(f"Subscription {data.subscription_id} not found.")

    year = data.issue_date.year if data.issue_date else date.today().year
    seq_id, number = _next_invoice_number(db, year)

    subtotal = ZERO
    tax_total = ZERO
    discount_total = ZERO

    invoice = Invoice(
        id=seq_id,
        number=number,
        customer_id=data.customer_id,
        subscription_id=data.subscription_id,
        status=InvoiceStatus.DRAFT,
        issue_date=data.issue_date,
        due_date=data.due_date,
        period_start=data.period_start,
        period_end=data.period_end,
        notes=data.notes,
    )

    for line_in in data.lines:
        line_sub = line_in.unit_price * line_in.quantity
        subtotal += line_sub
        tax_total += line_in.tax_amount
        discount_total += line_in.discount_amount

        invoice.lines.append(
            InvoiceLine(
                description=line_in.description,
                quantity=line_in.quantity,
                unit_price=line_in.unit_price,
                product_id=line_in.product_id,
                variant_id=line_in.variant_id,
                tax_id=line_in.tax_id,
                tax_rate=line_in.tax_rate,
                tax_amount=line_in.tax_amount,
                discount_amount=line_in.discount_amount,
                amount=line_in.amount,
                line_type=line_in.line_type,
            )
        )

    invoice.amount_subtotal = subtotal
    invoice.amount_tax = tax_total
    invoice.amount_discount = discount_total
    invoice.amount_total = max(ZERO, subtotal + tax_total - discount_total)

    db.add(invoice)
    db.flush()

    record_audit(
        db,
        actor=actor,
        entity_type="invoice",
        entity_id=invoice.id,
        action="create",
        changes={"number": invoice.number, "total": str(invoice.amount_total)},
    )
    return invoice


def get_invoice(db: Session, invoice_id: int) -> Invoice | None:
    return db.get(Invoice, invoice_id)


def list_invoices(
    db: Session,
    *,
    status: InvoiceStatus | None = None,
    customer_id: int | None = None,
    search: str | None = None,
) -> Select:
    query = select(Invoice).order_by(Invoice.id.desc())
    if status is not None:
        query = query.where(Invoice.status == status)
    if customer_id is not None:
        query = query.where(Invoice.customer_id == customer_id)
    if search:
        search_filter = f"%{search.strip()}%"
        query = query.join(Customer).where(
            or_(
                Invoice.number.ilike(search_filter),
                Customer.name.ilike(search_filter),
                Customer.email.ilike(search_filter),
            )
        )
    return query


def confirm_invoice(
    db: Session,
    invoice: Invoice,
    *,
    actor: User | None = None,
) -> Invoice:
    """Transition DRAFT -> CONFIRMED. Confirmed invoices become immutable."""
    if invoice.status != InvoiceStatus.DRAFT:
        raise InvoiceError(f"Cannot confirm invoice in {invoice.status.value} status.")

    invoice.status = InvoiceStatus.CONFIRMED

    # Record discount usage and increment discount counters atomically
    if invoice.amount_discount > ZERO:
        for line in invoice.lines:
            if line.line_type == "DISCOUNT":
                # Find the discount rule matching this line description
                rule_name = line.description.replace("Discount: ", "").strip()
                discount = db.scalar(select(Discount).where(Discount.name == rule_name))
                if discount:
                    discount.usage_count += 1
                    db.add(
                        DiscountUsage(
                            discount_id=discount.id,
                            invoice_id=invoice.id,
                            customer_id=invoice.customer_id,
                            amount_applied=line.discount_amount or abs(line.amount),
                        )
                    )

    db.flush()
    record_audit(
        db,
        actor=actor,
        entity_type="invoice",
        entity_id=invoice.id,
        action="confirm",
        changes={"status": InvoiceStatus.CONFIRMED.value},
    )
    return invoice


def cancel_invoice(
    db: Session,
    invoice: Invoice,
    *,
    actor: User | None = None,
    reason: str | None = None,
) -> Invoice:
    """Transition DRAFT or CONFIRMED -> CANCELLED."""
    if invoice.status in (InvoiceStatus.CANCELLED, InvoiceStatus.PAID):
        raise InvoiceError(f"Cannot cancel invoice in {invoice.status.value} status.")

    old_status = invoice.status
    invoice.status = InvoiceStatus.CANCELLED

    # If it was confirmed, revert any discount usages
    if old_status == InvoiceStatus.CONFIRMED:
        usages = list(db.scalars(select(DiscountUsage).where(DiscountUsage.invoice_id == invoice.id)).all())
        for usage in usages:
            discount = db.get(Discount, usage.discount_id)
            if discount and discount.usage_count > 0:
                discount.usage_count -= 1
            db.delete(usage)

    db.flush()
    record_audit(
        db,
        actor=actor,
        entity_type="invoice",
        entity_id=invoice.id,
        action="cancel",
        changes={"from": old_status.value, "to": InvoiceStatus.CANCELLED.value, "reason": reason or ""},
    )
    return invoice


def send_invoice(
    db: Session,
    invoice: Invoice,
    *,
    actor: User | None = None,
) -> None:
    """Send an invoice email to the customer with invoice summary and details."""
    customer = invoice.customer or db.get(Customer, invoice.customer_id)
    if not customer or not customer.email:
        raise InvoiceError(f"Customer {invoice.customer_id} has no valid email address.")

    subject = f"Invoice {invoice.number} from Brightloop Subscriptions"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #4f46e5;">Brightloop Subscriptions</h2>
        <p>Dear {customer.name},</p>
        <p>Your invoice <strong>{invoice.number}</strong> has been issued.</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
          <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
            <th style="padding: 10px; text-align: left;">Description</th>
            <th style="padding: 10px; text-align: center;">Qty</th>
            <th style="padding: 10px; text-align: right;">Unit Price</th>
            <th style="padding: 10px; text-align: right;">Amount</th>
          </tr>
          {''.join(f'''
          <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px;">{line.description}</td>
            <td style="padding: 10px; text-align: center;">{line.quantity}</td>
            <td style="padding: 10px; text-align: right;">₹{line.unit_price}</td>
            <td style="padding: 10px; text-align: right;">₹{line.amount}</td>
          </tr>
          ''' for line in invoice.lines)}
        </table>
        <div style="text-align: right; margin-top: 15px;">
          <p>Subtotal: ₹{invoice.amount_subtotal}</p>
          <p>Taxes: ₹{invoice.amount_tax}</p>
          {f'<p>Discount: -₹{invoice.amount_discount}</p>' if invoice.amount_discount > ZERO else ''}
          <h3 style="color: #1e293b;">Total Amount Due: ₹{invoice.amount_total}</h3>
          <p>Due Date: <strong>{invoice.due_date}</strong></p>
        </div>
        <p>Thank you for choosing Brightloop!</p>
      </body>
    </html>
    """

    send_email(db, to=customer.email, subject=subject, body=body)

    record_audit(
        db,
        actor=actor,
        entity_type="invoice",
        entity_id=invoice.id,
        action="send",
        changes={"to": customer.email, "number": invoice.number},
    )


def render_invoice_html(invoice: Invoice) -> str:
    """Render a clean, high-fidelity printable HTML invoice with CSS @media print."""
    customer = invoice.customer
    customer_name = customer.name if customer else f"Customer #{invoice.customer_id}"
    customer_email = customer.email if customer else ""
    billing_addr = customer.billing_address if customer and customer.billing_address else "Not specified"

    rows_html = "".join(
        f"""
        <tr>
          <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">{line.description}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: center;">{line.quantity}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">₹{line.unit_price}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">₹{line.tax_amount}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">₹{line.discount_amount}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: 600;">₹{line.amount}</td>
        </tr>
        """
        for line in invoice.lines
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Invoice {invoice.number} - Brightloop Subscriptions</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #1e293b;
      background: #f8fafc;
      margin: 0;
      padding: 40px;
    }}
    .invoice-card {{
      max-width: 800px;
      margin: 0 auto;
      background: #ffffff;
      padding: 48px;
      border-radius: 12px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
      border: 1px solid #e2e8f0;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 2px solid #f1f5f9;
    }}
    .brand {{
      font-size: 24px;
      font-weight: 800;
      color: #4f46e5;
    }}
    .invoice-meta {{
      text-align: right;
    }}
    .invoice-number {{
      font-size: 20px;
      font-weight: 700;
      color: #0f172a;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      margin-top: 6px;
    }}
    .badge-draft {{ background: #f1f5f9; color: #475569; }}
    .badge-confirmed {{ background: #eff6ff; color: #2563eb; }}
    .badge-paid {{ background: #ecfdf5; color: #059669; }}
    .badge-cancelled {{ background: #fef2f2; color: #dc2626; }}
    .details-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 32px;
      margin-bottom: 36px;
    }}
    .section-title {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      margin-bottom: 8px;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 24px;
    }}
    th {{
      text-align: left;
      padding: 10px 12px;
      background: #f8fafc;
      font-size: 12px;
      text-transform: uppercase;
      color: #64748b;
      font-weight: 600;
    }}
    .totals {{
      margin-left: auto;
      width: 320px;
      margin-top: 24px;
    }}
    .totals-row {{
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      font-size: 14px;
      color: #475569;
    }}
    .grand-total {{
      border-top: 2px solid #e2e8f0;
      margin-top: 8px;
      padding-top: 12px;
      font-size: 18px;
      font-weight: 800;
      color: #0f172a;
    }}
    .print-button {{
      display: inline-block;
      background: #4f46e5;
      color: white;
      padding: 10px 20px;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 600;
      font-size: 14px;
      margin-bottom: 24px;
      cursor: pointer;
    }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .invoice-card {{ box-shadow: none; border: none; padding: 0; }}
      .no-print {{ display: none !important; }}
    }}
  </style>
</head>
<body>
  <div class="no-print" style="max-width: 800px; margin: 0 auto 16px auto; text-align: right;">
    <button class="print-button" onclick="window.print()">Print / Download PDF</button>
  </div>
  <div class="invoice-card">
    <div class="header">
      <div>
        <div class="brand">Brightloop Subscriptions</div>
        <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px;">Billing & Subscription Platform</p>
      </div>
      <div class="invoice-meta">
        <div class="invoice-number">{invoice.number}</div>
        <div class="badge badge-{invoice.status.value.lower()}">{invoice.status.value}</div>
      </div>
    </div>

    <div class="details-grid">
      <div>
        <div class="section-title">Billed To</div>
        <div style="font-weight: 700; font-size: 16px;">{customer_name}</div>
        <div style="color: #64748b; font-size: 14px; margin-top: 2px;">{customer_email}</div>
        <div style="color: #475569; font-size: 13px; margin-top: 6px; white-space: pre-line;">{billing_addr}</div>
      </div>
      <div style="text-align: right;">
        <div class="section-title">Invoice Information</div>
        <div style="font-size: 14px; color: #475569;">Issue Date: <strong>{invoice.issue_date}</strong></div>
        <div style="font-size: 14px; color: #475569; margin-top: 4px;">Due Date: <strong>{invoice.due_date}</strong></div>
        {f'<div style="font-size: 13px; color: #64748b; margin-top: 4px;">Period: {invoice.period_start} to {invoice.period_end}</div>' if invoice.period_start else ''}
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th>Description</th>
          <th style="text-align: center;">Qty</th>
          <th style="text-align: right;">Price</th>
          <th style="text-align: right;">Tax</th>
          <th style="text-align: right;">Discount</th>
          <th style="text-align: right;">Total</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>

    <div class="totals">
      <div class="totals-row">
        <span>Subtotal</span>
        <span>₹{invoice.amount_subtotal}</span>
      </div>
      <div class="totals-row">
        <span>Tax</span>
        <span>₹{invoice.amount_tax}</span>
      </div>
      {f'''
      <div class="totals-row" style="color: #16a34a;">
        <span>Discount</span>
        <span>-₹{invoice.amount_discount}</span>
      </div>
      ''' if invoice.amount_discount > ZERO else ''}
      <div class="totals-row grand-total">
        <span>Grand Total</span>
        <span>₹{invoice.amount_total}</span>
      </div>
      <div class="totals-row" style="margin-top: 6px;">
        <span>Amount Paid</span>
        <span>₹{invoice.amount_paid}</span>
      </div>
      <div class="totals-row" style="font-weight: 700; color: {'#dc2626' if invoice.amount_due > ZERO else '#16a34a'};">
        <span>Balance Due</span>
        <span>₹{invoice.amount_due}</span>
      </div>
    </div>

    {f'''
    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #f1f5f9; font-size: 13px; color: #64748b;">
      <strong>Notes:</strong> {invoice.notes}
    </div>
    ''' if invoice.notes else ''}
  </div>
</body>
</html>"""
