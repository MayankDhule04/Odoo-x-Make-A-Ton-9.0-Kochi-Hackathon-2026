"""Guards for the migration history that all four members share."""

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Engine

from app.models import Base


def test_single_alembic_head(alembic_cfg: Config) -> None:
    heads = ScriptDirectory.from_config(alembic_cfg).get_heads()

    assert len(heads) == 1, (
        f"Alembic has {len(heads)} heads {heads}: two migrations share a parent. Fix with: "
        'docker compose run --rm api alembic merge heads -m "merge heads"'
    )


def test_models_match_migrations(engine: Engine) -> None:
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert diff == [], (
        f"Models and migrations differ: {diff}. Create a migration with: "
        'docker compose exec api alembic revision --autogenerate -m "<domain>: <change>"'
    )
