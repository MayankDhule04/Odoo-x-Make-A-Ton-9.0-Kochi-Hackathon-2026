"""Tax rule business logic."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import Tax
from app.schemas.catalog import TaxCreate, TaxUpdate
from app.services.audit import record_audit


def create_tax(db: Session, data: TaxCreate, *, actor: User) -> Tax:
    tax = Tax(**data.model_dump())
    db.add(tax)
    db.flush()
    record_audit(
        db, actor=actor, entity_type="tax", entity_id=tax.id, action="create",
        changes={"name": tax.name, "percentage": str(tax.percentage)},
    )
    return tax


def list_taxes(db: Session):
    return select(Tax).order_by(Tax.id)


def get_tax(db: Session, tax_id: int) -> Tax | None:
    return db.get(Tax, tax_id)


def update_tax(db: Session, tax: Tax, data: TaxUpdate, *, actor: User) -> Tax:
    changes: dict[str, list[str]] = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        old = getattr(tax, field)
        if old != value:
            changes[field] = [str(old), str(value)]
            setattr(tax, field, value)
    db.flush()
    if changes:
        record_audit(
            db, actor=actor, entity_type="tax", entity_id=tax.id, action="update", changes=changes,
        )
    return tax


def delete_tax(db: Session, tax: Tax, *, actor: User) -> None:
    tax_id = tax.id
    db.delete(tax)
    db.flush()
    record_audit(db, actor=actor, entity_type="tax", entity_id=tax_id, action="delete")
