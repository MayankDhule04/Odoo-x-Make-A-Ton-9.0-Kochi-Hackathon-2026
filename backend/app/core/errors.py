"""One consistent error format for every endpoint.

Every error response has:
    {"detail": "Human-readable message.", "errors": [...optional field-level details...]}

Install with `register_error_handlers(app)` in main.py.
"""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorResponse(BaseModel):
    detail: str
    errors: list[dict[str, str]] = []


def register_error_handlers(app: FastAPI) -> None:
    """Replace FastAPI's default error responses with a consistent shape."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(ErrorResponse(detail=str(exc.detail))),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        field_errors = []
        for err in exc.errors():
            loc = " → ".join(str(part) for part in err.get("loc", ()))
            field_errors.append({"field": loc, "message": err.get("msg", "")})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                ErrorResponse(detail="Validation failed.", errors=field_errors)
            ),
        )
