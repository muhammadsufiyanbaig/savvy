"""Mock all external dependencies before importing app."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# ── 1. Kafka consumer ──────────────────────────────────────────────────────────
_mock_kafka_consumer = MagicMock()
_mock_kafka_consumer.__iter__ = MagicMock(return_value=iter([]))
_kafka_cons_patcher = patch("kafka.KafkaConsumer", return_value=_mock_kafka_consumer)
_kafka_cons_patcher.start()

# ── 2. Kafka producer ──────────────────────────────────────────────────────────
_kafka_prod_patcher = patch("app.events.producer._get_kafka_producer", return_value=None)
_kafka_prod_patcher.start()

# ── 3. Claude AI ───────────────────────────────────────────────────────────────
_claude_patcher = patch("app.integrations.claude_client._get_client", return_value=None)
_claude_patcher.start()

# ── 4. ChromaDB ────────────────────────────────────────────────────────────────
_chroma_patcher = patch("app.integrations.chroma_client._get_chroma_client", return_value=None)
_chroma_patcher.start()

# ── 5. Redis ───────────────────────────────────────────────────────────────────
_cache_store: dict = {}

_mock_redis = MagicMock()

def _redis_get(key):
    val = _cache_store.get(key)
    return json.dumps(val) if val else None

def _redis_setex(key, ttl, value):
    _cache_store[key] = json.loads(value)
    return True

_mock_redis.get.side_effect = _redis_get
_mock_redis.setex.side_effect = _redis_setex
_mock_redis.ping.return_value = True

_redis_patcher = patch("app.integrations.redis_client._get_redis_client", return_value=_mock_redis)
_redis_patcher.start()

# ── 6. yfinance ────────────────────────────────────────────────────────────────
_yfinance_patcher = patch("yfinance.Ticker")
_mock_yf_ticker = MagicMock()
import pandas as pd
_mock_yf_ticker.return_value.history.return_value = pd.DataFrame()  # empty → fallback
_yfinance_patcher.start()

# ── Import app after all patches ──────────────────────────────────────────────
from app.main import app  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    _cache_store.clear()
    yield
    _cache_store.clear()


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
def sample_expenses():
    return [
        {"id": 1, "category": "Food & Dining", "amount": 450.0, "description": "restaurants"},
        {"id": 2, "category": "Food & Dining", "amount": 320.0, "description": "groceries"},
        {"id": 3, "category": "Transportation", "amount": 180.0, "description": "uber"},
        {"id": 4, "category": "Entertainment", "amount": 200.0, "description": "netflix etc"},
        {"id": 5, "category": "Bills & Utilities", "amount": 300.0, "description": "rent portion"},
    ]


@pytest.fixture
def investment_request_dict():
    return {
        "user_id": 1,
        "available_amount": 5000.0,
        "risk_tolerance": "medium",
        "time_horizon": "long",
        "country": "USA",
        "shariah_compliant": False,
        "preferred_sectors": ["technology"],
    }


@pytest.fixture
def rec_request_dict():
    return {
        "user_id": 1,
        "recommendation_types": ["savings", "spending"],
        "context": {"monthly_income": 5000, "monthly_expenses": 4000},
    }
