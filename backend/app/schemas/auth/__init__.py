"""Request and response models for the auth endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.auth import UserRole


# --- Login / tokens -----------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the access token expires.")
    user: UserRead


# --- Signup -------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


# --- Password reset -----------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=1, max_length=128)


class MessageResponse(BaseModel):
    """Generic success message."""
    message: str


# --- Password policy ----------------------------------------------------------------

class PasswordPolicyResponse(BaseModel):
    """Rules the frontend shows as a checklist while the user types."""
    min_length: int
    max_length: int
    requires_uppercase: bool = True
    requires_lowercase: bool = True
    requires_special: bool = True


# --- Staff creation (admin only) ---------------------------------------------------

class CreateStaffRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


# --- Customer -----------------------------------------------------------------------

class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    name: str
    email: str
    phone: str | None
    billing_address: str | None
    is_active: bool


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    billing_address: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    billing_address: str | None = None
    is_active: bool | None = None
