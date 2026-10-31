"""Quotation template business logic."""

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.subscriptions import QuotationTemplate, QuotationTemplateLine
from app.schemas.subscriptions import TemplateCreate, TemplateUpdate
from app.services.audit import record_audit


def _build_lines(data_lines) -> list[QuotationTemplateLine]:
    return [
        QuotationTemplateLine(
            product_id=line.product_id,
            variant_id=line.variant_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )
        for line in data_lines
    ]


def create_template(db: Session, data: TemplateCreate, *, actor: User) -> QuotationTemplate:
    template = QuotationTemplate(
        name=data.name,
        plan_id=data.plan_id,
        validity_days=data.validity_days,
        notes=data.notes,
        lines=_build_lines(data.lines),
    )
    db.add(template)
    db.flush()
    record_audit(
        db, actor=actor, entity_type="quotation_template", entity_id=template.id,
        action="create", changes={"name": template.name},
    )
    return template


def list_templates(db: Session) -> Select:
    return select(QuotationTemplate).order_by(QuotationTemplate.id)


def get_template(db: Session, template_id: int) -> QuotationTemplate | None:
    return db.get(QuotationTemplate, template_id)


def update_template(db: Session, template: QuotationTemplate, data: TemplateUpdate, *, actor: User) -> QuotationTemplate:
    fields = data.model_dump(exclude_unset=True)
    if "lines" in fields:
        template.lines.clear()
        db.flush()
        template.lines = _build_lines(data.lines or [])
    for field in ("name", "plan_id", "validity_days", "notes"):
        if field in fields:
            setattr(template, field, fields[field])
    db.flush()
    record_audit(
        db, actor=actor, entity_type="quotation_template", entity_id=template.id,
        action="update", changes={k: str(v) for k, v in fields.items() if k != "lines"},
    )
    return template


def delete_template(db: Session, template: QuotationTemplate, *, actor: User) -> None:
    template_id = template.id
    db.delete(template)
    db.flush()
    record_audit(
        db, actor=actor, entity_type="quotation_template", entity_id=template_id, action="delete",
    )
