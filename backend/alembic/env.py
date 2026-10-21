import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ensure workspace root and backend dir are in python path
current_dir = os.path.abspath(os.path.dirname(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(backend_dir, ".."))

for path in [project_root, backend_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.core.config import get_settings
from backend.core.database import Base
# Register all module models so Alembic metadata detects them
import backend.modules.finance.models  # noqa: F401
import backend.modules.health.models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Determine database URL dynamically
def get_db_url() -> str:
    x_args = context.get_x_argument(as_dictionary=True)
    if "url" in x_args:
        return x_args["url"]
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    return get_settings().DATABASE_URL

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}

    url = get_db_url()
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
