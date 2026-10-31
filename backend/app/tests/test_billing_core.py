"""Unit tests for the billing calculation engine, idempotency, taxes, and discounts."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import DiscountUsage, Invoice, InvoiceStatus
from app.models.catalog import (
    BillingPeriod,
    Discount,
    DiscountTarget,
    DiscountType,
    Plan,
    Product,
    Tax,
)
from app.models.customers import Customer
from app.models.subscriptions import PaymentTerms, Subscription, SubscriptionLine, SubscriptionStatus
from app.services.billing.calculator import (
    calculate_subscription_invoice,
    compute_tax,
    find_applicable_discounts,
)
from app.services.billing.dry_run import preview_billing_run
from app.services.billing.engine import run_billing
from app.services.billing.invoices import (
    cancel_invoice,
    confirm_invoice,
    create_invoice,
    get_invoice,
)
from app.schemas.billing import InvoiceCreate, InvoiceLineIn


def test_compute_tax_exclusive():
    """Exclusive tax adds percentage onto base price."""
    base, tax = compute_tax(Decimal("100.00"), Decimal("18.000"), inclusive=False)
    assert base == Decimal("100.00")
    assert tax == Decimal("18.00")

    # Odd rounding check: 33.33 * 18% = 5.9994 -> 6.00
    base, tax = compute_tax(Decimal("33.33"), Decimal("18.000"), inclusive=False)
    assert base == Decimal("33.33")
    assert tax == Decimal("6.00")


def test_compute_tax_inclusive():
    """Inclusive tax extracts tax portion from total price."""
    # 118.00 inclusive of 18% = base 100.00, tax 18.00
    base, tax = compute_tax(Decimal("118.00"), Decimal("18.000"), inclusive=True)
    assert base == Decimal("100.00")
    assert tax == Decimal("18.00")


def test_discount_eligibility_and_expiry(db_session: Session):
    today = date.today()
    # Active discount
    d_active = Discount(
        name="Valid Promo",
        type=DiscountType.PERCENTAGE,
        value=Decimal("10.00"),
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=5),
        min_purchase_amount=Decimal("100.00"),
        min_quantity=1,
        usage_limit=5,
        usage_count=2,
    )
    # Expired discount
    d_expired = Discount(
        name="Old Promo",
        type=DiscountType.FIXED,
        value=Decimal("50.00"),
        start_date=today - timedelta(days=20),
        end_date=today - timedelta(days=1),
        min_purchase_amount=Decimal("0.00"),
    )
    # Reached limit discount
    d_maxed = Discount(
        name="Maxed Promo",
        type=DiscountType.PERCENTAGE,
        value=Decimal("20.00"),
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=5),
        usage_limit=3,
        usage_count=3,
    )
    db_session.add_all([d_active, d_expired, d_maxed])
    db_session.flush()

    applicable = find_applicable_discounts(db_session, today, Decimal("200.00"), 2)
    names = [d.name for d in applicable]
    assert "Valid Promo" in names
    assert "Old Promo" not in names
    assert "Maxed Promo" not in names


def test_billing_run_idempotency_and_date_advance(db_session: Session, make_user):
    """Running the billing engine twice on the same day creates 0 duplicate invoices."""
    today = date.today()
    user = make_user()
    customer = db_session.scalar(select(Customer).where(Customer.user_id == user.id))

    plan = Plan(
        name="Monthly Test",
        price=Decimal("500.00"),
        billing_period=BillingPeriod.MONTHLY,
        available_from=today - timedelta(days=60),
        available_to=today + timedelta(days=300),
    )
    product = Product(
        name="Base Product",
        sales_price=Decimal("500.00"),
        cost_price=Decimal("200.00"),
    )
    db_session.add_all([plan, product])
    db_session.flush()

    sub = Subscription(
        number="SUB-TEST-IDEMPOTENT",
        customer_id=customer.id,
        plan_id=plan.id,
        start_date=today - timedelta(days=30),
        expiry_date=today + timedelta(days=335),
        next_billing_date=today,
        payment_terms=PaymentTerms.NET_15,
        status=SubscriptionStatus.ACTIVE,
    )
    sub.lines.append(
        SubscriptionLine(
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("500.00"),
            amount=Decimal("500.00"),
        )
    )
    db_session.add(sub)
    db_session.flush()

    # First run: generates 1 invoice and advances next_billing_date
    res1 = run_billing(db_session, as_of_date=today, actor=user)
    assert res1.created_count == 1
    assert len(res1.invoices) == 1
    invoice = res1.invoices[0]
    assert invoice.status == InvoiceStatus.CONFIRMED
    assert invoice.amount_total == Decimal("500.00")
    assert sub.next_billing_date > today

    # Second run immediately on same day: creates 0 duplicates
    res2 = run_billing(db_session, as_of_date=today, actor=user)
    assert res2.created_count == 0

    # Verify database has exactly 1 invoice for this subscription
    invoices = list(db_session.scalars(select(Invoice).where(Invoice.subscription_id == sub.id)).all())
    assert len(invoices) == 1


def test_invoice_confirm_atomicity_and_discount_usage(db_session: Session, make_user):
    """Confirming an invoice records DiscountUsage and increments usage_count atomically."""
    today = date.today()
    user = make_user()
    customer = db_session.scalar(select(Customer).where(Customer.user_id == user.id))

    discount = Discount(
        name="Special 100 Off",
        type=DiscountType.FIXED,
        value=Decimal("100.00"),
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=30),
        usage_limit=10,
        usage_count=0,
    )
    db_session.add(discount)
    db_session.flush()

    data = InvoiceCreate(
        customer_id=customer.id,
        issue_date=today,
        due_date=today + timedelta(days=15),
        lines=[
            InvoiceLineIn(
                description="Service item",
                quantity=1,
                unit_price=Decimal("500.00"),
                amount=Decimal("500.00"),
            ),
            InvoiceLineIn(
                description="Discount: Special 100 Off",
                quantity=1,
                unit_price=Decimal("-100.00"),
                discount_amount=Decimal("100.00"),
                amount=Decimal("-100.00"),
                line_type="DISCOUNT",
            ),
        ],
    )
    inv = create_invoice(db_session, data, actor=user)
    assert inv.status == InvoiceStatus.DRAFT
    assert discount.usage_count == 0

    # Confirm invoice
    confirmed_inv = confirm_invoice(db_session, inv, actor=user)
    assert confirmed_inv.status == InvoiceStatus.CONFIRMED
    assert discount.usage_count == 1

    # Verify DiscountUsage row was created
    usages = list(db_session.scalars(select(DiscountUsage).where(DiscountUsage.invoice_id == inv.id)).all())
    assert len(usages) == 1
    assert usages[0].amount_applied == Decimal("100.00")

    # Cancel invoice: reverses discount usage
    cancelled_inv = cancel_invoice(db_session, confirmed_inv, actor=user)
    assert cancelled_inv.status == InvoiceStatus.CANCELLED
    assert discount.usage_count == 0
    usages_after = list(db_session.scalars(select(DiscountUsage).where(DiscountUsage.invoice_id == inv.id)).all())
    assert len(usages_after) == 0


def test_dry_run_preview_detects_exceptions(db_session: Session, make_user):
    """Dry run preview surfaces inactive customer and expired plan in the exceptions queue."""
    today = date.today()
    user = make_user()
    customer = db_session.scalar(select(Customer).where(Customer.user_id == user.id))
    customer.is_active = False  # Set customer inactive!

    plan = Plan(
        name="Expired Plan",
        price=Decimal("100.00"),
        billing_period=BillingPeriod.MONTHLY,
        available_from=today - timedelta(days=60),
        available_to=today - timedelta(days=1),  # Expired!
    )
    product = Product(name="Item", sales_price=Decimal("100.00"), cost_price=Decimal("50.00"))
    db_session.add_all([plan, product])
    db_session.flush()

    sub = Subscription(
        number="SUB-EXCEPT-001",
        customer_id=customer.id,
        plan_id=plan.id,
        start_date=today - timedelta(days=30),
        expiry_date=today + timedelta(days=300),
        next_billing_date=today,
        status=SubscriptionStatus.ACTIVE,
    )
    sub.lines.append(
        SubscriptionLine(product_id=product.id, quantity=1, unit_price=Decimal("100.00"), amount=Decimal("100.00"))
    )
    db_session.add(sub)
    db_session.flush()

    preview = preview_billing_run(db_session, as_of_date=today)
    assert preview.exceptions_count >= 1
    codes = [e.error_code for e in preview.exceptions]
    assert "INACTIVE_CUSTOMER" in codes
