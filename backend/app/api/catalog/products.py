"""Product endpoints. Reads: staff or admin. Writes: admin only."""

from fastapi import APIRouter, HTTPException, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser, StaffOrAdmin
from app.models.catalog import Product
from app.schemas.catalog import (
    ProductAttributeIn,
    ProductAttributeRead,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductVariantIn,
    ProductVariantRead,
    ProductVariantUpdate,
)
from app.services import catalog as catalog_service

router = APIRouter(prefix="/products", tags=["catalog: products"])


def _require_product(db: DbSession, product_id: int) -> Product:
    product = catalog_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


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
    product = _require_product(db, product_id)
    catalog_service.delete_product(db, product, actor=admin)
    db.commit()


# --- Variants ------------------------------------------------------------------------

@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantRead,
    status_code=status.HTTP_201_CREATED,
)
def add_variant(product_id: int, body: ProductVariantIn, db: DbSession, admin: AdminUser):
    product = _require_product(db, product_id)
    variant = catalog_service.add_variant(db, product, body, actor=admin)
    db.commit()
    db.refresh(variant)
    return variant


@router.patch("/{product_id}/variants/{variant_id}", response_model=ProductVariantRead)
def update_variant(
    product_id: int, variant_id: int, body: ProductVariantUpdate, db: DbSession, admin: AdminUser
):
    variant = catalog_service.get_variant(db, variant_id)
    if variant is None or variant.product_id != product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found.")
    variant = catalog_service.update_variant(db, variant, body, actor=admin)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete(
    "/{product_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_variant(product_id: int, variant_id: int, db: DbSession, admin: AdminUser) -> None:
    variant = catalog_service.get_variant(db, variant_id)
    if variant is None or variant.product_id != product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found.")
    catalog_service.delete_variant(db, variant, actor=admin)
    db.commit()


# --- Attributes ----------------------------------------------------------------------

@router.post(
    "/{product_id}/attributes",
    response_model=ProductAttributeRead,
    status_code=status.HTTP_201_CREATED,
)
def add_attribute(product_id: int, body: ProductAttributeIn, db: DbSession, admin: AdminUser):
    product = _require_product(db, product_id)
    attribute = catalog_service.add_attribute(db, product, body, actor=admin)
    db.commit()
    db.refresh(attribute)
    return attribute


@router.delete(
    "/{product_id}/attributes/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_attribute(product_id: int, attribute_id: int, db: DbSession, admin: AdminUser) -> None:
    attribute = catalog_service.get_attribute(db, attribute_id)
    if attribute is None or attribute.product_id != product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found.")
    catalog_service.delete_attribute(db, attribute, actor=admin)
    db.commit()
