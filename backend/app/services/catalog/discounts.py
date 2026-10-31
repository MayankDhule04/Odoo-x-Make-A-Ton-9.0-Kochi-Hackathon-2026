"""Discount rule business logic (admin only)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import Discount, Product
from app.schemas.catalog import DiscountCreate
from app.services.audit import record_audit


def create_discount(db: Session, data: DiscountCreate, *, actor: User) -> Discount:
    payload = data.model_dump(exclude={"product_ids"})
    discount = Discount(**payload)
    if data.product_ids:
        discount.products = list(
            db.scalars(select(Product).where(Product.id.in_(data.product_ids)))
        )
    db.add(discount)
    db.flush()
    record_audit(
        db, actor=actor, entity_type="discount", entity_id=discount.id, action="create",
        changes={"name": discount.name, "type": discount.type.value, "value": str(discount.value)},
    )
    return discount


def list_discounts(db: Session):
    return select(Discount).order_by(Discount.id)
