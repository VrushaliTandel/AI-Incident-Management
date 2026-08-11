"""
Database connection and session management.
Uses a single, absolute-path SQLite database to avoid path confusion.
"""
import logging
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from backend.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Use the resolved absolute path to prevent multiple DB files
DATABASE_URL = settings.absolute_db_path

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


# Enable WAL mode for better concurrent reads
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Must be called after models are imported."""
    from backend.database import models  # noqa: F401 - registers all models
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified at: %s", DATABASE_URL)
