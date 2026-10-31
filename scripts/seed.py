"""Seed demo data into the development database.

The API container runs this on every start. To run it by hand:
    docker compose exec api python /scripts/seed.py

Each workstream adds its step to app/seed/ and calls it from main() below. Every step
must be idempotent and fast.
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path so 'app' is importable both inside containers and on host
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import SessionLocal
from app.seed.demo_billing import seed_demo_billing
from app.seed.demo_catalog import seed_demo_catalog
from app.seed.demo_users import seed_demo_users


def main() -> None:
    with SessionLocal() as session:
        created_users = seed_demo_users(session)
        created_catalog = seed_demo_catalog(session)
        created_billing = seed_demo_billing(session)
        session.commit()

    if created_users:
        print(f"Seed: created demo users {', '.join(created_users)}")
    else:
        print("Seed: demo users already exist")

    if created_catalog:
        print(f"Seed: created demo catalog {', '.join(created_catalog)}")
    else:
        print("Seed: demo catalog already exists")

    if created_billing:
        print(f"Seed: created demo billing {', '.join(created_billing)}")
    else:
        print("Seed: demo billing already exists")


if __name__ == "__main__":
    main()
