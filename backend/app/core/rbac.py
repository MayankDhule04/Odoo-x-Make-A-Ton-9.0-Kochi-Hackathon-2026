"""Authentication and role-based access control for every API route.

Protect each route with one of these (all of them go through `require_role`):

    from app.core.rbac import AdminUser, StaffOrAdmin, CurrentUser, CurrentCustomer, CurrentPrincipal

    def create_plan(body: PlanCreate, db: DbSession, admin: AdminUser): ...          # ADMIN only
    def record_payment(body: PaymentIn, db: DbSession, user: StaffOrAdmin): ...      # STAFF or ADMIN
    def my_subscriptions(db: DbSession, customer: CurrentCustomer): ...              # CUSTOMER only
    def list_invoices(db: DbSession, principal: CurrentPrincipal):                   # any role,
        stmt = principal.scope(select(Invoice), Invoice.customer_id)                 # customers see
        ...                                                                          # only their own

A test (app/tests/test_rbac_guard.py) fails if any route outside its public allowlist
doesn't depend on `require_role`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, TypeVar

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select, select

from app.core.db import DbSession
from app.core.security import InvalidTokenError, decode_token
from app.models.auth import User, UserRole
from app.models.customers import Customer

# Attribute set on every function returned by require_role. The route guard test
# looks for it in each route's dependency tree.
RBAC_ROLES_ATTR = "__rbac_roles__"

_bearer = HTTPBearer(
    auto_error=False,
    description="Paste the access_token returned by POST /api/auth/login.",
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Resolve the user from the bearer access token.

    Don't use this directly in routes; use require_role or one of the aliases below.
    """
    if credentials is None:
        raise _unauthorized("Not authenticated.")
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError):
        raise _unauthorized("Your session is invalid or has expired. Please log in again.") from None

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != payload["ver"]:
        raise _unauthorized("Your session is invalid or has expired. Please log in again.")
    return user


def require_role(*roles: UserRole) -> Callable[..., User]:
    """Dependency that lets the request through only for users with one of `roles`.

    Use it as `Depends(require_role(UserRole.ADMIN))`, in a route's `dependencies=[...]`,
    or through the Annotated aliases in this module.
    """
    if not roles:
        raise ValueError("require_role needs at least one role.")
    allowed = frozenset(roles)

    def check_role(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to do this.",
            )
        return user

    setattr(check_role, RBAC_ROLES_ATTR, allowed)
    check_role.__name__ = "require_role_" + "_".join(sorted(role.value.lower() for role in allowed))
    return check_role


_any_role = require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.CUSTOMER)
_customer_role = require_role(UserRole.CUSTOMER)

SelectT = TypeVar("SelectT", bound=Select[Any])


@dataclass(frozen=True)
class Principal:
    """Who is calling, and which customer's rows they may see.

    customer_id is set for CUSTOMER users and None for STAFF and ADMIN.
    """

    user: User
    customer_id: int | None

    @property
    def role(self) -> UserRole:
        return self.user.role

    @property
    def is_customer(self) -> bool:
        return self.user.role is UserRole.CUSTOMER

    def scope(self, statement: SelectT, customer_id_column: Any) -> SelectT:
        """Restrict a query to the caller's own rows when the caller is a customer.

        Staff and admins get the statement back unchanged. Always pass the column that
        holds the owning customer's id, e.g. `Invoice.customer_id`.
        """
        if self.is_customer:
            return statement.where(customer_id_column == self.customer_id)
        return statement


def _customer_for(db: DbSession, user: User) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has no customer profile.",
        )
    return customer


def get_principal(db: DbSession, user: Annotated[User, Depends(_any_role)]) -> Principal:
    customer_id = _customer_for(db, user).id if user.role is UserRole.CUSTOMER else None
    return Principal(user=user, customer_id=customer_id)


def get_current_customer(db: DbSession, user: Annotated[User, Depends(_customer_role)]) -> Customer:
    """The customer record of the logged-in CUSTOMER. Never take a customer id from the client."""
    return _customer_for(db, user)


# Any logged-in user, whatever their role.
CurrentUser = Annotated[User, Depends(_any_role)]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
StaffOrAdmin = Annotated[User, Depends(require_role(UserRole.STAFF, UserRole.ADMIN))]
CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
