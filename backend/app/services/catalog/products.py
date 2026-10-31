"""Product / variant business logic. Services flush but never commit; the route commits.

Changes to prices are recorded in the audit log (shared contract).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import Product, ProductAttribute, ProductVariant
from app.schemas.catalog import ProductCreate, ProductUpdate
from app.services.audit import record_audit

_PRICE_FIELDS = {"sales_price", "cost_price"}


def create_product(db: Session, data: ProductCreate, *, actor: User) -> Product:
    product = Product(
        name=data.name,
        type=data.type,
        sales_price=data.sales_price,
        cost_price=data.cost_price,
        notes=data.notes,
    )
    for attr in data.attributes:
        product.attributes.append(ProductAttribute(name=attr.name))
    for variant in data.variants:
        product.variants.append(
            ProductVariant(
                value=variant.value,
                price_extra=variant.price_extra,
                attribute_id=variant.attribute_id,
            )
        )
    db.add(product)
    db.flush()
    record_audit(
        db,
        actor=actor,
        entity_type="product",
        entity_id=product.id,
        action="create",
        changes={
            "name": product.name,
            "sales_price": str(product.sales_price),
            "cost_price": str(product.cost_price),
        },
    )
    return product


def list_products(db: Session):
    return select(Product).order_by(Product.id)


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def update_product(db: Session, product: Product, data: ProductUpdate, *, actor: User) -> Product:
    changes: dict[str, list[str]] = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        old = getattr(product, field)
        if old != value:
            setattr(product, field, value)
            if field in _PRICE_FIELDS:
                changes[field] = [str(old), str(value)]
    db.flush()
    if changes:
        record_audit(
            db, actor=actor, entity_type="product", entity_id=product.id,
            action="update", changes=changes,
        )
    return product


def delete_product(db: Session, product: Product, *, actor: User) -> None:
    product_id = product.id
    db.delete(product)
    db.flush()
    record_audit(
        db, actor=actor, entity_type="product", entity_id=product_id, action="delete",
    )
