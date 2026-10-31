"""Auth endpoints (Member 1): signup, login, refresh, password reset, staff creation,
password policy rules, and the current-user endpoint."""

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status

from app.core.config import settings
from app.core.db import DbSession
from app.core.rate_limit import LoginRateLimit, ResetRateLimit
from app.core.rbac import AdminUser, CurrentUser
from app.core.security import (
    IssuedToken,
    InvalidTokenError,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.auth import User, UserRole
from app.schemas.auth import (
    CreateStaffRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordPolicyResponse,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserRead,
)
from app.services.auth import (
    EmailAlreadyRegisteredError,
    PasswordPolicyError,
    authenticate,
    create_user,
)
from app.services.auth.password_reset import (
    InvalidResetTokenError,
    request_password_reset,
    reset_password,
)

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


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _issue_tokens(user: User, response: Response) -> TokenResponse:
    access = create_access_token(user_id=user.id, token_version=user.token_version)
    refresh = create_refresh_token(user_id=user.id, token_version=user.token_version)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access.token,
        expires_in=settings.access_token_ttl_minutes * 60,
        user=UserRead.model_validate(user),
    )


# --- Public endpoints ---------------------------------------------------------------


@router.get("/password-policy", response_model=PasswordPolicyResponse)
def password_policy() -> PasswordPolicyResponse:
    """The rules the frontend shows as a live checklist while the user types."""
    return PasswordPolicyResponse(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DbSession, response: Response) -> TokenResponse:
    """Create a CUSTOMER account and log them in."""
    try:
        user = create_user(db, email=body.email, password=body.password, full_name=body.full_name, role=UserRole.CUSTOMER)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=" ".join(exc.errors)) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return _issue_tokens(user, response)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession, response: Response, _rate: LoginRateLimit) -> TokenResponse:
    user = authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    db.commit()
    return _issue_tokens(user, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    db: DbSession,
    response: Response,
    brightloop_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> TokenResponse:
    """Exchange a valid refresh token (from the httpOnly cookie) for a new token pair."""
    if not brightloop_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token.")
    try:
        payload = decode_token(brightloop_refresh, expected_type="refresh")
        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError):
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.") from None

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != payload["ver"]:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    return _issue_tokens(user, response)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest, db: DbSession, request: Request, _rate: ResetRateLimit) -> MessageResponse:
    """Send a reset link.  Always returns success so it never reveals whether the email exists."""
    base_url = str(request.base_url).rstrip("/")
    request_password_reset(db, email=body.email, base_url=base_url)
    db.commit()
    return MessageResponse(message="If that email is registered, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def do_reset_password(body: ResetPasswordRequest, db: DbSession, _rate: ResetRateLimit) -> MessageResponse:
    """Validate the token and set a new password."""
    try:
        reset_password(db, raw_token=body.token, new_password=body.new_password)
    except InvalidResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=" ".join(exc.errors)) from exc
    db.commit()
    return MessageResponse(message="Your password has been reset. You can now log in.")


# --- Protected endpoints ------------------------------------------------------------


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user


@router.post("/staff", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_staff(body: CreateStaffRequest, db: DbSession, admin: AdminUser) -> User:
    """Admin-only: create a STAFF user."""
    try:
        user = create_user(db, email=body.email, password=body.password, full_name=body.full_name, role=UserRole.STAFF)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=" ".join(exc.errors)) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return user
