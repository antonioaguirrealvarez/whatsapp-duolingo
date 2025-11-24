"""Data module for database operations."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import get_settings

# Global engine and session factory
engine = None
SessionLocal = None


def init_db():
    """Initialize the database engine and session factory."""
    global engine, SessionLocal
    if engine is None:
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Get a database session."""
    global SessionLocal
    if SessionLocal is None:
        init_db()
    return SessionLocal()


__all__ = ["get_db_session", "init_db"]