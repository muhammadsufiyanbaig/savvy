"""Mock all external deps before importing app; use SQLite in-memory DB."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── 1. Patch Kafka BEFORE app import ──────────────────────────────────────────
_mock_kafka_consumer = MagicMock()
_mock_kafka_consumer.__iter__ = MagicMock(return_value=iter([]))
_kafka_cons_patcher = patch("kafka.KafkaConsumer", return_value=_mock_kafka_consumer)
_kafka_cons_patcher.start()

_kafka_prod_patcher = patch(
    "app.events.producer._get_kafka_producer", return_value=None
)
_kafka_prod_patcher.start()

# ── 2. Patch Redis ─────────────────────────────────────────────────────────────
_cache_store: dict = {}
_mock_redis = MagicMock()


def _redis_get(key):
    val = _cache_store.get(key)
    return json.dumps(val) if val is not None else None


def _redis_setex(key, ttl, value):
    _cache_store[key] = json.loads(value)
    return True


def _redis_delete(key):
    _cache_store.pop(key, None)
    return True


_mock_redis.get.side_effect = _redis_get
_mock_redis.setex.side_effect = _redis_setex
_mock_redis.delete.side_effect = _redis_delete
_mock_redis.ping.return_value = True

_redis_patcher = patch(
    "app.integrations.redis_client._get_redis_client", return_value=_mock_redis
)
_redis_patcher.start()

# ── 3. Patch SMTP and OneSignal ────────────────────────────────────────────────
_smtp_patcher = patch("smtplib.SMTP", MagicMock())
_smtp_patcher.start()

_push_patcher = patch("app.services.push_service.send_push", return_value=None)
_push_patcher.start()

# ── 4. Set up SQLite in-memory DB ─────────────────────────────────────────────
from app.core import database as _db_module  # noqa: E402

_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_db_module.engine = _test_engine

_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)
_db_module.SessionLocal = _TestSessionLocal

# Create tables
from app.core.database import Base  # noqa: E402
from app.models.notification import Notification, NotificationPreference  # noqa: F401,E402

Base.metadata.create_all(bind=_test_engine)

# ── Import app AFTER all patches ──────────────────────────────────────────────
from app.main import app  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """Wipe tables and Redis cache between tests."""
    _cache_store.clear()
    yield
    _cache_store.clear()
    with _test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    from app.core.config import settings
    token = jwt.encode({"sub": "1", "user_id": 1}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2():
    from app.core.config import settings
    token = jwt.encode({"sub": "2", "user_id": 2}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_notification(db):
    """Create a test notification in DB."""
    from app.models.notification import Notification
    from datetime import datetime, timedelta
    n = Notification(
        user_id=1,
        notification_type="budget",
        channel="in_app",
        title="Budget Alert",
        message="You've exceeded 80% of your budget.",
        data={"category": "Food"},
        is_sent=True,
        is_read=False,
        priority=3,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n
