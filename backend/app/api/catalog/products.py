"""Product endpoints. Reads: staff or admin. Writes: admin only."""

from fastapi import APIRouter, HTTPException, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser, StaffOrAdmin
from app.models.catalog import Product
from app.schemas.catalog import ProductCreate, ProductRead, ProductUpdate
from app.services import catalog as catalog_service

router = APIRouter(prefix="/products", tags=["catalog: products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductCreate, db: DbSession, admin: AdminUser) -> Product:
    product = catalog_service.create_product(db, body, actor=admin)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=Page[ProductRead])
def list_products(db: DbSession, params: PaginationDep, _user: StaffOrAdmin) -> Page[ProductRead]:
    return paginate(db, catalog_service.list_products(db), params)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: DbSession, _user: StaffOrAdmin) -> Product:
    product = catalog_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, body: ProductUpdate, db: DbSession, admin: AdminUser) -> Product:
    product = catalog_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    product = catalog_service.update_product(db, product, body, actor=admin)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession, admin: AdminUser) -> None:
    product = catalog_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    catalog_service.delete_product(db, product, actor=admin)
    db.commit()
