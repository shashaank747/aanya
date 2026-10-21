"""
Database engine, session management, and Base model for SQLAlchemy 2.x.
"""
from typing import Generator, Tuple
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Engine creation parameters
connect_args = {}
engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,  # Clean stale connections automatically
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
    if ":memory:" in settings.DATABASE_URL:
        engine_kwargs["poolclass"] = StaticPool
else:
    # Set a reasonable connection timeout (3 seconds) to avoid blocking health checks
    connect_args["connect_timeout"] = 3
    engine_kwargs["connect_args"] = connect_args
    # PostgreSQL connection pooling defaults
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 1800  # Recycle connections every 30 mins

try:
    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
except Exception as e:
    logger.error("Failed to create SQLAlchemy engine with URL: %s. Error: %s", settings.DATABASE_URL, e)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime, timezone

# SQLAlchemy 2.0 Declarative Base
Base = declarative_base()


class AppSetting(Base):
    """
    Core metadata/settings table used to store configuration state
    and verify database migrations/persistence.
    """
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy session.
    Ensures safe closing of sessions on request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Tuple[bool, str]:
    """
    Verify database connectivity by executing a lightweight query ('SELECT 1').
    Returns (True, 'connected') if healthy, or (False, error_details) if failing.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as exc:
        error_msg = f"Database unreachable: {type(exc).__name__} - {str(exc)}"
        logger.warning(error_msg)
        return False, error_msg
