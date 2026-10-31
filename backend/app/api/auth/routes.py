"""Auth endpoints (Member 1): signup, login, token refresh, password reset, staff
creation and the audit log read API."""

from fastapi import APIRouter

router = APIRouter(tags=["auth"])
