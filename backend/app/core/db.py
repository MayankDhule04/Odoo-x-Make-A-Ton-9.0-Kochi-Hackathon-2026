"""Database engine, sessions and the FastAPI session dependency."""

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def create_db_engine(url: str | URL, **kwargs: Any) -> Engine:
    """Create an engine whose connections always use the UTC time zone."""
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=UTC"},
        **kwargs,
    )


engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Yield one session per request and close it when the request ends."""
    with SessionLocal() as session:
        yield session


# Use in route signatures: `def handler(db: DbSession): ...`
DbSession = Annotated[Session, Depends(get_db)]
