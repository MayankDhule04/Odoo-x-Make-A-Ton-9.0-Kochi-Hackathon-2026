"""Subscription creation, editing and read queries.

Numbering: SUB-<year>-<zero-padded id>. Services flush; the route commits.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Select, select, text
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import Product, ProductVariant
from app.models.subscriptions import (
    QuotationTemplate,
    Subscription,
    SubscriptionHistory,
    SubscriptionLine,
    SubscriptionStatus,
)
from app.schemas.subscriptions import (
    SubscriptionCreate,
    SubscriptionFromTemplate,
    SubscriptionLineIn,
    SubscriptionUpdate,
)
from app.services.audit import record_audit
from app.services.subscriptions.transitions import TransitionError

ZERO = Decimal("0.00")
_EDITABLE = (SubscriptionStatus.DRAFT, SubscriptionStatus.QUOTATION)


class SubscriptionLookupError(LookupError):
    """A referenced product, variant or template was not found."""


def _next_number(db: Session, year: int) -> tuple[int, str]:
    """Reserve the next id from the table's sequence and build the number from it."""
    seq_id = db.execute(text("SELECT nextval('subscriptions_id_seq')")).scalar_one()
    return int(seq_id), f"SUB-{year}-{int(seq_id):06d}"


def _effective_unit_price(db: Session, product_id: int, variant_id: int | None) -> Decimal:
    product = db.get(Product, product_id)
    if product is None:
        raise SubscriptionLookupError(f"Product {product_id} not found.")
    extra = ZERO
    if variant_id is not None:
        variant = db.get(ProductVariant, variant_id)
        if variant is None or variant.product_id != product_id:
            raise SubscriptionLookupError(f"Variant {variant_id} not found on product {product_id}.")
        extra = variant.price_extra
    return product.sales_price + extra


def _build_line(db: Session, data: SubscriptionLineIn) -> SubscriptionLine:
    unit_price = (
        data.unit_price
        if data.unit_price is not None
        else _effective_unit_price(db, data.product_id, data.variant_id)
    )
    return SubscriptionLine(
        product_id=data.product_id,
        variant_id=data.variant_id,
        tax_id=data.tax_id,
        quantity=data.quantity,
        unit_price=unit_price,
        amount=unit_price * data.quantity,
    )


def create_subscription(db: Session, data: SubscriptionCreate, *, actor: User) -> Subscription:
    seq_id, number = _next_number(db, data.start_date.year)
    sub = Subscription(
        id=seq_id,
        number=number,
        customer_id=data.customer_id,
        plan_id=data.plan_id,
        start_date=data.start_date,
        expiry_date=data.expiry_date,
        payment_terms=data.payment_terms,
        status=SubscriptionStatus.DRAFT,
    )
    for line_in in data.lines:
        sub.lines.append(_build_line(db, line_in))
    db.add(sub)
    db.flush()

    # Initial history row (from_status is null for creation).
    db.add(
        SubscriptionHistory(
            subscription_id=sub.id,
            from_status=None,
            to_status=SubscriptionStatus.DRAFT,
            actor_id=actor.id if actor else None,
            note="created",
        )
    )
    record_audit(
        db, actor=actor, entity_type="subscription", entity_id=sub.id, action="create",
        changes={"number": sub.number, "customer_id": sub.customer_id},
    )
    db.flush()
    return sub


def create_from_template(db: Session, data: SubscriptionFromTemplate, *, actor: User) -> Subscription:
    template = db.get(QuotationTemplate, data.template_id)
    if template is None:
        raise SubscriptionLookupError(f"Quotation template {data.template_id} not found.")
    expiry = data.expiry_date or (data.start_date + timedelta(days=template.validity_days))
    create = SubscriptionCreate(
        customer_id=data.customer_id,
        plan_id=template.plan_id,
        start_date=data.start_date,
        expiry_date=expiry,
        payment_terms=data.payment_terms,
        lines=[
            SubscriptionLineIn(
                product_id=line.product_id,
                variant_id=line.variant_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
            for line in template.lines
        ],
    )
    return create_subscription(db, create, actor=actor)


def list_subscriptions(db: Session) -> Select:
    return select(Subscription).order_by(Subscription.id.desc())


def get_subscription(db: Session, subscription_id: int) -> Subscription | None:
    return db.get(Subscription, subscription_id)


def update_subscription(db: Session, sub: Subscription, data: SubscriptionUpdate, *, actor: User) -> Subscription:
    if sub.status not in _EDITABLE:
        raise TransitionError("A subscription can only be edited while it is a draft or quotation.")
    fields = data.model_dump(exclude_unset=True)

    if "lines" in fields:
        sub.lines.clear()
        db.flush()
        for line_in in data.lines or []:
            sub.lines.append(_build_line(db, line_in))

    for field in ("plan_id", "start_date", "expiry_date", "payment_terms"):
        if field in fields:
            setattr(sub, field, fields[field])

    db.flush()
    record_audit(
        db, actor=actor, entity_type="subscription", entity_id=sub.id, action="update",
        changes={k: str(v) for k, v in fields.items() if k != "lines"},
    )
    return sub


def history_query(db: Session, subscription_id: int) -> Select:
    return (
        select(SubscriptionHistory)
        .where(SubscriptionHistory.subscription_id == subscription_id)
        .order_by(SubscriptionHistory.id)
    )
