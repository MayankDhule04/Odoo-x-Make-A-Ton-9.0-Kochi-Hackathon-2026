"""Tax rule business logic."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import Tax
from app.schemas.catalog import TaxCreate
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
