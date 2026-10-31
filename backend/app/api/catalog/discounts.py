"""Discount rule endpoints. Admin only, including reads (pricing policy is sensitive)."""

from fastapi import APIRouter, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser
from app.models.catalog import Discount
from app.schemas.catalog import DiscountCreate, DiscountRead
from app.services import catalog as catalog_service

router = APIRouter(prefix="/discounts", tags=["catalog: discounts"])


@router.post("", response_model=DiscountRead, status_code=status.HTTP_201_CREATED)
def create_discount(body: DiscountCreate, db: DbSession, admin: AdminUser) -> Discount:
    discount = catalog_service.create_discount(db, body, actor=admin)
    db.commit()
    db.refresh(discount)
    return discount


@router.get("", response_model=Page[DiscountRead])
def list_discounts(db: DbSession, params: PaginationDep, _admin: AdminUser) -> Page[DiscountRead]:
    return paginate(db, catalog_service.list_discounts(db), params)
