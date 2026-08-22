# Async SQLAlchemy engine/session factory for AWS RDS Postgres / PostGIS
# (Dual Engine Pattern: Used by high-throughput async services like the Fargate Pipeline & WebSockets)

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import get_settings

settings = get_settings()

db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)

# Ensure the scheme is asyncpg for async connections
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

# Create the async engine with connection pooling optimized for AWS RDS
# pool_pre_ping=True automatically reconnects if RDS dropped the socket
async_engine = create_async_engine(
    db_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections every 30 mins
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_db():
    """FastAPI dependency for yielding an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
