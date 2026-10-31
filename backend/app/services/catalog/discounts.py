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
