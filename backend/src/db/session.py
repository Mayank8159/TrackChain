# SQLAlchemy engine/session factory for Postgres/TimescaleDB with RDS Proxy and SQLite fallback (tc.v1 SOTA).

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from src.config import get_settings

settings = get_settings()

db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
is_lambda = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

# AWS RDS Proxy connection pooling support in serverless environments
if is_lambda and "rds.amazonaws.com" in db_url and "proxy-" not in db_url:
    # Route through RDS Proxy when provisioned
    proxy_host = os.getenv("RDS_PROXY_HOST")
    if proxy_host:
        db_url = db_url.replace(db_url.split("@")[1].split("/")[0], proxy_host)

engine = None

if "postgresql" in db_url:
    try:
        import psycopg2  # type: ignore
        # Optimize pool configuration for Lambda vs standard server container
        pool_size = 5 if is_lambda else 20
        max_overflow = 2 if is_lambda else 10
        pool_recycle = 300 if is_lambda else 3600

        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            echo=settings.DEBUG,
        )
    except Exception:
        engine = None

if engine is None:
    # Use SQLite for local development & instantaneous unit testing
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../trackchain_dev.db"))
    engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency for yielding database session with automatic commit / rollback."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
