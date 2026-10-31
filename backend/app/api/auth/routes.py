"""Auth endpoints (Member 1).

Login returns a short-lived access token in the body and puts the refresh token in an
httpOnly cookie that JavaScript can't read. Signup, refresh, password reset, staff
creation and the audit log API are added next.
"""

from fastapi import APIRouter, HTTPException, Response, status

from app.core.config import settings
from app.core.db import DbSession
from app.core.rbac import CurrentUser
from app.core.security import IssuedToken, create_access_token, create_refresh_token
from app.models.auth import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "brightloop_refresh"
REFRESH_COOKIE_PATH = "/api/auth"


def _set_refresh_cookie(response: Response, refresh: IssuedToken) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh.token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=not settings.is_development,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession, response: Response) -> TokenResponse:
    user = authenticate(db, body.email, body.password)
    if user is None:
        # One message for unknown email, wrong password and deactivated account.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")

    access = create_access_token(user_id=user.id, token_version=user.token_version)
    refresh = create_refresh_token(user_id=user.id, token_version=user.token_version)
    db.commit()  # persists an upgraded password hash, if authenticate() rehashed it
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access.token,
        expires_in=settings.access_token_ttl_minutes * 60,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
