"""Plan business logic, including the availability-window rule for new subscriptions."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import Plan
from app.schemas.catalog import PlanCreate, PlanUpdate
from app.services.audit import record_audit


def create_plan(db: Session, data: PlanCreate, *, actor: User) -> Plan:
    plan = Plan(**data.model_dump())
    db.add(plan)
    db.flush()
    record_audit(
        db, actor=actor, entity_type="plan", entity_id=plan.id, action="create",
        changes={"name": plan.name, "price": str(plan.price), "billing_period": plan.billing_period.value},
    )
    return plan


def list_plans(db: Session):
    return select(Plan).order_by(Plan.id)


def selectable_plans(db: Session, on: date) -> list[Plan]:
    """Only plans whose availability window includes `on` can be used for new
    subscriptions. Plans outside their window are excluded."""
    stmt = (
        select(Plan)
        .where(Plan.available_from <= on, Plan.available_to >= on)
        .order_by(Plan.id)
    )
    return list(db.scalars(stmt))


def get_plan(db: Session, plan_id: int) -> Plan | None:
    return db.get(Plan, plan_id)


def update_plan(db: Session, plan: Plan, data: PlanUpdate, *, actor: User) -> Plan:
    changes: dict[str, list[str]] = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        old = getattr(plan, field)
        if old != value:
            changes[field] = [str(old), str(value)]
            setattr(plan, field, value)
    db.flush()
    if changes:
        record_audit(
            db, actor=actor, entity_type="plan", entity_id=plan.id, action="update", changes=changes,
        )
    return plan


def delete_plan(db: Session, plan: Plan, *, actor: User) -> None:
    plan_id = plan.id
    db.delete(plan)
    db.flush()
    record_audit(db, actor=actor, entity_type="plan", entity_id=plan_id, action="delete")
