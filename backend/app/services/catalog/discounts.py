"""Discount rule business logic (admin only)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import Discount, Product
from app.schemas.catalog import DiscountCreate, DiscountUpdate
from app.services.audit import record_audit


def _resolve_products(db: Session, product_ids: list[int]) -> list[Product]:
    if not product_ids:
        return []
    return list(db.scalars(select(Product).where(Product.id.in_(product_ids))))


def create_discount(db: Session, data: DiscountCreate, *, actor: User) -> Discount:
    payload = data.model_dump(exclude={"product_ids"})
    discount = Discount(**payload)
    discount.products = _resolve_products(db, data.product_ids)
    db.add(discount)
    db.flush()
    record_audit(
        db, actor=actor, entity_type="discount", entity_id=discount.id, action="create",
        changes={"name": discount.name, "type": discount.type.value, "value": str(discount.value)},
    )
    return discount


def list_discounts(db: Session):
    return select(Discount).order_by(Discount.id)


def get_discount(db: Session, discount_id: int) -> Discount | None:
    return db.get(Discount, discount_id)


def update_discount(db: Session, discount: Discount, data: DiscountUpdate, *, actor: User) -> Discount:
    payload = data.model_dump(exclude_unset=True)
    product_ids = payload.pop("product_ids", None)
    changes: dict[str, list[str]] = {}
    for field, value in payload.items():
        old = getattr(discount, field)
        if old != value:
            changes[field] = [str(old), str(value)]
            setattr(discount, field, value)
    if product_ids is not None:
        discount.products = _resolve_products(db, product_ids)
        changes["product_ids"] = [str(product_ids)]
    db.flush()
    if changes:
        record_audit(
            db, actor=actor, entity_type="discount", entity_id=discount.id,
            action="update", changes=changes,
        )
    return discount


def delete_discount(db: Session, discount: Discount, *, actor: User) -> None:
    discount_id = discount.id
    db.delete(discount)
    db.flush()
    record_audit(db, actor=actor, entity_type="discount", entity_id=discount_id, action="delete")


# --- Discount simulator (differentiator #6) ------------------------------------------

from decimal import ROUND_HALF_UP, Decimal  # noqa: E402

from app.models.catalog import BillingPeriod, Plan  # noqa: E402
from app.models.subscriptions import Subscription, SubscriptionStatus  # noqa: E402
from app.schemas.catalog import DiscountSimulateRequest, DiscountSimulationResult  # noqa: E402
from app.schemas.catalog import DiscountType, DiscountTarget  # noqa: E402

_ZERO = Decimal("0.00")
_CENTS = Decimal("0.01")

# Convert a per-period discount to a rough monthly figure for the projection.
_MONTHLY_FACTOR = {
    BillingPeriod.DAILY: Decimal("30"),
    BillingPeriod.WEEKLY: Decimal("4"),
    BillingPeriod.MONTHLY: Decimal("1"),
    BillingPeriod.YEARLY: Decimal("1") / Decimal("12"),
}


def simulate_discount(db: Session, data: DiscountSimulateRequest) -> DiscountSimulationResult:
    """How many current ACTIVE subscriptions the rule would hit, and the projected
    monthly revenue impact."""
    actives = list(
        db.scalars(select(Subscription).where(Subscription.status == SubscriptionStatus.ACTIVE))
    )
    product_ids = set(data.product_ids)
    matched = 0
    impact = _ZERO

    for sub in actives:
        if data.target is DiscountTarget.PRODUCT:
            lines = [line for line in sub.lines if line.product_id in product_ids]
        else:
            lines = list(sub.lines)
        base = sum((line.amount for line in lines), _ZERO)
        qty = sum((line.quantity for line in lines), 0)

        if base <= _ZERO or base < data.min_purchase_amount or qty < data.min_quantity:
            continue

        matched += 1
        per_period = data.value if data.type is DiscountType.FIXED else base * data.value / Decimal("100")
        plan = db.get(Plan, sub.plan_id)
        factor = _MONTHLY_FACTOR.get(plan.billing_period, Decimal("1")) if plan else Decimal("1")
        impact += per_period * factor

    return DiscountSimulationResult(
        active_subscriptions=len(actives),
        matched_count=matched,
        projected_monthly_impact=impact.quantize(_CENTS, rounding=ROUND_HALF_UP),
    )
