"""Seed demo data into the development database.

The API container runs this on every start. To run it by hand:
    docker compose exec api python /scripts/seed.py

Each workstream adds its step to app/seed/ and calls it from main() below. Every step
must be idempotent and fast.
"""

from app.core.db import SessionLocal
from app.seed.demo_users import seed_demo_users


def main() -> None:
    with SessionLocal() as session:
        created_users = seed_demo_users(session)
        session.commit()

    if created_users:
        print(f"Seed: created demo users {', '.join(created_users)}")
    else:
        print("Seed: demo users already exist")


if __name__ == "__main__":
    main()
