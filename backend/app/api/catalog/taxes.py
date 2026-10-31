"""Tax rule endpoints. Reads: staff or admin. Writes: admin only."""

from fastapi import APIRouter, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser, StaffOrAdmin
from app.models.catalog import Tax
from app.schemas.catalog import TaxCreate, TaxRead
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
