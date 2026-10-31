"""Quotation template endpoints. Staff or admin manage templates."""

from fastapi import APIRouter, HTTPException, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import StaffOrAdmin
from app.models.subscriptions import QuotationTemplate
from app.schemas.subscriptions import TemplateCreate, TemplateRead, TemplateUpdate
from app.services import subscriptions as sub_service

router = APIRouter(prefix="/quotation-templates", tags=["subscriptions: quotation templates"])


def _require(db: DbSession, template_id: int) -> QuotationTemplate:
    template = sub_service.get_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    return template


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateCreate, db: DbSession, user: StaffOrAdmin) -> QuotationTemplate:
    template = sub_service.create_template(db, body, actor=user)
    db.commit()
    db.refresh(template)
    return template


@router.get("", response_model=Page[TemplateRead])
def list_templates(db: DbSession, params: PaginationDep, _user: StaffOrAdmin) -> Page[TemplateRead]:
    return paginate(db, sub_service.list_templates(db), params)


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(template_id: int, db: DbSession, _user: StaffOrAdmin) -> QuotationTemplate:
    return _require(db, template_id)


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(template_id: int, body: TemplateUpdate, db: DbSession, user: StaffOrAdmin) -> QuotationTemplate:
    template = _require(db, template_id)
    template = sub_service.update_template(db, template, body, actor=user)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: DbSession, user: StaffOrAdmin) -> None:
    template = _require(db, template_id)
    sub_service.delete_template(db, template, actor=user)
    db.commit()
