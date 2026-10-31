"""Customer CRUD endpoints.

Staff and admin can list, view, create and update customers.
A customer can only view their own record via GET /api/auth/customers/me.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import CurrentCustomer, StaffOrAdmin
from app.models.customers import Customer
from app.schemas.auth import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerRead])
def list_customers(db: DbSession, params: PaginationDep, _user: StaffOrAdmin) -> Page[CustomerRead]:
    query = select(Customer).order_by(Customer.id)
    return paginate(db, query, params)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, db: DbSession, _user: StaffOrAdmin) -> Customer:
    """Staff/admin can add a customer who doesn't have a login."""
    customer = Customer(name=body.name, email=body.email, phone=body.phone, billing_address=body.billing_address)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/me", response_model=CustomerRead)
def my_customer_profile(customer: CurrentCustomer) -> Customer:
    """The logged-in customer's own profile."""
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: DbSession, _user: StaffOrAdmin) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: int, body: CustomerUpdate, db: DbSession, _user: StaffOrAdmin) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer
