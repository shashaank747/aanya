"""
Unit tests for database session lifecycle and AppSetting baseline model.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.database import Base, AppSetting, check_db_connection, get_db


def test_app_setting_persistence():
    """Verify AppSetting CRUD lifecycle on SQLite test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    db = TestingSession()
    try:
        # Create
        setting = AppSetting(key="system_init", value="completed")
        db.add(setting)
        db.commit()

        # Read
        retrieved = db.query(AppSetting).filter_by(key="system_init").first()
        assert retrieved is not None
        assert retrieved.value == "completed"
        assert retrieved.updated_at is not None

        # Update
        retrieved.value = "v1_ready"
        db.commit()

        # Verify update
        updated = db.query(AppSetting).filter_by(key="system_init").first()
        assert updated.value == "v1_ready"
    finally:
        db.close()


def test_get_db_generator():
    """Verify get_db generator yields and closes without exception."""
    gen = get_db()
    session = next(gen)
    assert session is not None
    # Closing generator
    try:
        next(gen)
    except StopIteration:
        pass
