"""Seed demo data into the development database.

Run inside the API container:
    docker compose exec api python /scripts/seed.py

Each workstream adds its seed step here once its models exist. The auth work adds the
demo admin, staff and customer users first.
"""

from sqlalchemy import text

from app.core.db import SessionLocal


def main() -> None:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    print("Database reachable. Nothing to seed yet.")


if __name__ == "__main__":
    main()
