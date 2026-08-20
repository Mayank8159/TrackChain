# SQLAlchemy engine/session factory for Postgres/TimescaleDB with SQLite dev/test fallback.

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from src.config import get_settings

settings = get_settings()

db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
engine = None

if "postgresql" in db_url:
    try:
        import psycopg2  # type: ignore
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    except Exception:
        engine = None

if engine is None:
    # Use shared file-based SQLite database for local dev / testing
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../trackchain_dev.db"))
    engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
