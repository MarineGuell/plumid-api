# api/db.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from settings import settings

from models.base import Base

DB_URL: str = settings.db_url

POOL_KW: Dict[str, Any] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
}

CONNECT_ARGS: Dict[str, Any] = {}

# SSL optionnel (si cert fourni)
ssl_ca = settings.mysql_ssl_ca
if ssl_ca and DB_URL.startswith("mysql"):
    CONNECT_ARGS["ssl"] = {"ca": ssl_ca}

# SQLite: connect_args spécifiques + pas de pool sizing
if DB_URL.startswith("sqlite"):
    CONNECT_ARGS.setdefault("check_same_thread", False)
    POOL_KW.pop("pool_size", None)
    POOL_KW.pop("max_overflow", None)
    POOL_KW.pop("pool_recycle", None)

engine = create_engine(
    DB_URL,
    connect_args=CONNECT_ARGS,
    **POOL_KW,
)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """
    FastAPI dependency that provides a SQLAlchemy session.
    It yields a database session and ensures it is closed after the request is completed.

    Yields:
        Session: A SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
