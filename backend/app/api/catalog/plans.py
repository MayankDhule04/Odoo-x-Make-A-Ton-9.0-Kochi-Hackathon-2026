"""Plan endpoints. Reads: staff or admin. Writes: admin only.

GET /api/plans/selectable returns only plans usable for a new subscription on a date.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser, StaffOrAdmin
from app.models.catalog import Plan
from app.schemas.catalog import PlanCreate, PlanRead, PlanUpdate
from app.services import catalog as catalog_service

router = APIRouter(prefix="/plans", tags=["catalog: plans"])


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(body: PlanCreate, db: DbSession, admin: AdminUser) -> Plan:
    plan = catalog_service.create_plan(db, body, actor=admin)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=Page[PlanRead])
def list_plans(db: DbSession, params: PaginationDep, _user: StaffOrAdmin) -> Page[PlanRead]:
    return paginate(db, catalog_service.list_plans(db), params)


@router.get("/selectable", response_model=list[PlanRead])
def selectable_plans(
    db: DbSession,
    _user: StaffOrAdmin,
    on: date | None = Query(default=None, description="Date to check availability for; defaults to today."),
) -> list[Plan]:
    return catalog_service.selectable_plans(db, on or date.today())


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: int, db: DbSession, _user: StaffOrAdmin) -> Plan:
    plan = catalog_service.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    return plan


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: int, body: PlanUpdate, db: DbSession, admin: AdminUser) -> Plan:
    plan = catalog_service.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    plan = catalog_service.update_plan(db, plan, body, actor=admin)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: int, db: DbSession, admin: AdminUser) -> None:
    plan = catalog_service.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    catalog_service.delete_plan(db, plan, actor=admin)
    db.commit()
