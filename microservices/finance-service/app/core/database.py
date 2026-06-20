from contextvars import ContextVar

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Set by rls_user_id_middleware in main.py; read by get_db to configure RLS
_current_user_id: ContextVar[str] = ContextVar("rls_user_id", default="0")

_url = settings.DATABASE_URL
_pool_kwargs: dict = {}
if not _url.startswith("sqlite"):
    _pool_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }

engine = create_engine(_url, pool_pre_ping=True, **_pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        # Set PostgreSQL session variable for Row-Level Security policies.
        # `SET LOCAL` scopes to the current transaction — safe with connection pooling.
        uid = _current_user_id.get("0")
        try:
            uid_int = int(uid) if uid and uid.isdigit() else 0
        except (ValueError, TypeError):
            uid_int = 0
        db.execute(text(f"SET LOCAL app.user_id = '{uid_int}'"))
        yield db
    finally:
        db.close()
