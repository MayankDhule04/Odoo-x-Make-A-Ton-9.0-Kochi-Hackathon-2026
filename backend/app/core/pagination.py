"""Server-side pagination shared by every list endpoint.

Usage in a route:
    from app.core.pagination import Page, PaginationParams

    @router.get("/invoices", response_model=Page[InvoiceRead])
    def list_invoices(db: DbSession, params: PaginationParams, ...):
        query = select(Invoice).order_by(Invoice.id)
        return paginate(db, query, params)
"""

from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")

# Hard ceiling that clients can't exceed.
MAX_PAGE_SIZE = 100


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = 1
    page_size: int = 25

    def offset(self) -> int:
        return (max(1, self.page) - 1) * self.effective_page_size()

    def effective_page_size(self) -> int:
        return min(max(1, self.page_size), MAX_PAGE_SIZE)


def _pagination_params(
    page: Annotated[int, Query(ge=1, description="1-indexed page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page.")] = 25,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


# Use this in route signatures: `params: PaginationDep`
PaginationDep = Annotated[PaginationParams, Depends(_pagination_params)]


class Page(BaseModel, Generic[T]):
    """Envelope returned by every paginated endpoint."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def paginate(db: Session, query: Select, params: PaginationParams) -> Page:  # type: ignore[type-arg]
    """Run `query` with a count and an offset/limit, and wrap the result in a Page."""
    size = params.effective_page_size()

    total: int = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.offset(params.offset()).limit(size)).all()

    pages = max(1, -(-total // size))  # ceiling division
    return Page(items=list(rows), total=total, page=params.page, page_size=size, pages=pages)
