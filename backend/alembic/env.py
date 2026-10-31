from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.core.config import settings
from app.core.db import create_db_engine
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging. disable_existing_loggers=False keeps
# the app's loggers working when migrations run inside the test suite.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Every domain's models are registered on this metadata via app.models.
target_metadata = Base.metadata


def database_url() -> str:
    # The test suite sets sqlalchemy.url; everything else uses DATABASE_URL.
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a database connection)."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database."""
    connectable = create_db_engine(database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
