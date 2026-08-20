# Shared FastAPI dependencies: DB session, auth, pagination.

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.core.security import verify_api_key


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


class PaginationParams:
    def __init__(self, limit: int = 100, offset: int = 0):
        self.limit = min(limit, 1000)
        self.offset = max(offset, 0)
