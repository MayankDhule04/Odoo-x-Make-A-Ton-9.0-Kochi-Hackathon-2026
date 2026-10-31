"""Discount rule endpoints. Admin only, including reads (pricing policy is sensitive)."""

from fastapi import APIRouter, HTTPException, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser
from app.models.catalog import Discount
from app.schemas.catalog import (
    DiscountCreate,
    DiscountRead,
    DiscountSimulateRequest,
    DiscountSimulationResult,
    DiscountUpdate,
)
from app.services import catalog as catalog_service

router = APIRouter(prefix="/discounts", tags=["catalog: discounts"])


@router.post("/simulate", response_model=DiscountSimulationResult)
def simulate_discount(body: DiscountSimulateRequest, db: DbSession, _admin: AdminUser) -> DiscountSimulationResult:
    """Preview a discount rule's reach before saving it."""
    return catalog_service.simulate_discount(db, body)


@router.post("", response_model=DiscountRead, status_code=status.HTTP_201_CREATED)
def create_discount(body: DiscountCreate, db: DbSession, admin: AdminUser) -> Discount:
    discount = catalog_service.create_discount(db, body, actor=admin)
    db.commit()
    db.refresh(discount)
    return discount


@router.get("", response_model=Page[DiscountRead])
def list_discounts(db: DbSession, params: PaginationDep, _admin: AdminUser) -> Page[DiscountRead]:
    return paginate(db, catalog_service.list_discounts(db), params)


@router.patch("/{discount_id}", response_model=DiscountRead)
def update_discount(discount_id: int, body: DiscountUpdate, db: DbSession, admin: AdminUser) -> Discount:
    discount = catalog_service.get_discount(db, discount_id)
    if discount is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found.")
    discount = catalog_service.update_discount(db, discount, body, actor=admin)
    db.commit()
    db.refresh(discount)
    return discount


@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount(discount_id: int, db: DbSession, admin: AdminUser) -> None:
    discount = catalog_service.get_discount(db, discount_id)
    if discount is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found.")
    catalog_service.delete_discount(db, discount, actor=admin)
    db.commit()
