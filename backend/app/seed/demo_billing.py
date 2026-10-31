"""Demo invoices and subscriptions for testing and the 5-minute demo script."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceLine, InvoiceStatus
from app.models.catalog import Plan, Product, ProductVariant, Tax
from app.models.customers import Customer
from app.models.subscriptions import PaymentTerms, Subscription, SubscriptionLine, SubscriptionStatus


def seed_demo_billing(db: Session) -> list[str]:
    """Create demo subscription due for billing and a confirmed invoice if not present."""
    created: list[str] = []
    today = date.today()

    customer = db.scalar(select(Customer).where(Customer.email == "customer@brightloop.dev"))
    plan = db.scalar(select(Plan).where(Plan.name == "Monthly Standard"))
    product = db.scalar(select(Product).where(Product.name == "Brightloop Pro"))
    tax = db.scalar(select(Tax).where(Tax.name == "GST 18%"))

    if not customer or not plan or not product:
        return created

    variant = None
    if product.variants:
        variant = product.variants[0]

    # Create a demo active subscription due for billing today
    sub_num = "SUB-2026-000001"
    sub = db.scalar(select(Subscription).where(Subscription.number == sub_num))
    if sub is None:
        sub = Subscription(
            number=sub_num,
            customer_id=customer.id,
            plan_id=plan.id,
            start_date=today - timedelta(days=30),
            expiry_date=today + timedelta(days=335),
            next_billing_date=today,
            payment_terms=PaymentTerms.NET_15,
            status=SubscriptionStatus.ACTIVE,
        )
        unit_price = product.sales_price + (variant.price_extra if variant else Decimal("0.00"))
        sub.lines.append(
            SubscriptionLine(
                product_id=product.id,
                variant_id=variant.id if variant else None,
                tax_id=tax.id if tax else None,
                quantity=1,
                unit_price=unit_price,
                amount=unit_price,
            )
        )
        db.add(sub)
        db.flush()
        created.append(f"subscription '{sub_num}' (ACTIVE, due for billing)")

    # Create an initial confirmed invoice
    inv_num = "INV-2026-000001"
    inv = db.scalar(select(Invoice).where(Invoice.number == inv_num))
    if inv is None:
        inv = Invoice(
            number=inv_num,
            customer_id=customer.id,
            subscription_id=sub.id if sub else None,
            status=InvoiceStatus.CONFIRMED,
            issue_date=today - timedelta(days=30),
            due_date=today - timedelta(days=15),
            period_start=today - timedelta(days=30),
            period_end=today - timedelta(days=1),
            amount_subtotal=Decimal("1000.00"),
            amount_tax=Decimal("180.00"),
            amount_discount=Decimal("100.00"),
            amount_total=Decimal("1080.00"),
            amount_paid=Decimal("0.00"),
            notes="Initial subscription setup invoice",
        )
        inv.lines.append(
            InvoiceLine(
                description="Brightloop Pro (Generic)",
                quantity=1,
                unit_price=Decimal("1000.00"),
                product_id=product.id,
                variant_id=variant.id if variant else None,
                tax_id=tax.id if tax else None,
                tax_rate=Decimal("18.000"),
                tax_amount=Decimal("180.00"),
                discount_amount=Decimal("100.00"),
                amount=Decimal("1080.00"),
                line_type="STANDARD",
            )
        )
        db.add(inv)
        db.flush()
        created.append(f"invoice '{inv_num}' (CONFIRMED)")

    return created
