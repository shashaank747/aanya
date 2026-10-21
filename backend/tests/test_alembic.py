"""
Automated test verifying that Alembic can create and apply migrations programmatically.
"""
import os
import tempfile
from alembic.config import Config
from alembic import command


def test_alembic_upgrade_and_downgrade():
    """Verify that Alembic runs upgrade to head and downgrade to base without error."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        cfg = Config(ini_path)
        # Point to temporary SQLite database file
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

        # Execute upgrade
        command.upgrade(cfg, "head")

        # Execute downgrade
        command.downgrade(cfg, "base")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
