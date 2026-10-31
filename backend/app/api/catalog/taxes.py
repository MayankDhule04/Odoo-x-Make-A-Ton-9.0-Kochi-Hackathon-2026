"""Tax rule endpoints. Reads: staff or admin. Writes: admin only."""

from fastapi import APIRouter, HTTPException, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser, StaffOrAdmin
from app.models.catalog import Tax
from app.schemas.catalog import TaxCreate, TaxRead, TaxUpdate
from app.services import catalog as catalog_service

router = APIRouter(prefix="/taxes", tags=["catalog: taxes"])


@router.post("", response_model=TaxRead, status_code=status.HTTP_201_CREATED)
def create_tax(body: TaxCreate, db: DbSession, admin: AdminUser) -> Tax:
    tax = catalog_service.create_tax(db, body, actor=admin)
    db.commit()
    db.refresh(tax)
    return tax


@router.get("", response_model=Page[TaxRead])
def list_taxes(db: DbSession, params: PaginationDep, _user: StaffOrAdmin) -> Page[TaxRead]:
    return paginate(db, catalog_service.list_taxes(db), params)


@router.patch("/{tax_id}", response_model=TaxRead)
def update_tax(tax_id: int, body: TaxUpdate, db: DbSession, admin: AdminUser) -> Tax:
    tax = catalog_service.get_tax(db, tax_id)
    if tax is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax not found.")
    tax = catalog_service.update_tax(db, tax, body, actor=admin)
    db.commit()
    db.refresh(tax)
    return tax


@router.delete("/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax(tax_id: int, db: DbSession, admin: AdminUser) -> None:
    tax = catalog_service.get_tax(db, tax_id)
    if tax is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax not found.")
    catalog_service.delete_tax(db, tax, actor=admin)
    db.commit()
