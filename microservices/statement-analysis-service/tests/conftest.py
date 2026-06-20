"""Test configuration: mock all external services before importing the app."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# ── 1. Mock Kafka consumer ─────────────────────────────────────────────────────
_mock_kafka_consumer = MagicMock()
_mock_kafka_consumer.__iter__ = MagicMock(return_value=iter([]))
_kafka_cons_patcher = patch("kafka.KafkaConsumer", return_value=_mock_kafka_consumer)
_kafka_cons_patcher.start()

# ── 2. Mock Kafka producer ─────────────────────────────────────────────────────
_kafka_prod_patcher = patch("app.events.producer._get_kafka_producer", return_value=None)
_kafka_prod_patcher.start()

# ── 3. Mock S3 ────────────────────────────────────────────────────────────────
_mock_s3 = MagicMock()
_mock_s3.download_fileobj.return_value = None
_mock_s3.upload_fileobj.return_value = None
_s3_patcher = patch("app.services.s3_service._get_s3", return_value=_mock_s3)
_s3_patcher.start()

# ── 4. Mock Claude AI ─────────────────────────────────────────────────────────
_claude_patcher = patch("app.ai.claude_client._get_client", return_value=None)
_claude_patcher.start()

# ── 5. Mock OpenAI ────────────────────────────────────────────────────────────
_openai_patcher = patch("app.ai.openai_client._get_client", return_value=None)
_openai_patcher.start()

# ── 6. Mock ChromaDB ──────────────────────────────────────────────────────────
_chroma_patcher = patch("app.services.chroma_service._get_chroma_client", return_value=None)
_chroma_patcher.start()

# ── 7. Mock Redis ─────────────────────────────────────────────────────────────
_status_store: dict = {}

_mock_redis = MagicMock()

def _mock_redis_get(key):
    val = _status_store.get(key)
    return json.dumps(val) if val else None

def _mock_redis_setex(key, ttl, value):
    _status_store[key] = json.loads(value)
    return True

_mock_redis.get.side_effect = _mock_redis_get
_mock_redis.setex.side_effect = _mock_redis_setex
_mock_redis.ping.return_value = True

_redis_patcher = patch("app.services.redis_service._get_redis_client", return_value=_mock_redis)
_redis_patcher.start()

# ── 8. Now import app ─────────────────────────────────────────────────────────
from app.main import app  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_redis_store():
    """Reset in-memory Redis store between tests."""
    _status_store.clear()
    yield
    _status_store.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    from app.core.config import settings

    token = jwt.encode(
        {"sub": "1", "user_id": 1},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_pdf_bytes():
    """Minimal 'PDF' bytes — enough for our fake parser tests."""
    return b"%PDF-1.4 fake content for testing purposes only"


@pytest.fixture
def sample_csv_bytes():
    csv_text = (
        "Date,Description,Amount,Type\n"
        "2026-02-01,STARBUCKS COFFEE #1234,5.75,debit\n"
        "2026-02-02,AMAZON.COM*AB1234567,49.99,debit\n"
        "2026-02-03,DIRECT DEPOSIT PAYROLL,2500.00,credit\n"
    )
    return csv_text.encode("utf-8")


@pytest.fixture
def sample_transactions():
    return [
        {
            "date": "2026-02-01",
            "description": "STARBUCKS COFFEE #1234",
            "amount": 5.75,
            "transaction_type": "debit",
            "merchant": "Starbucks",
            "category_hint": "Food & Dining",
        },
        {
            "date": "2026-02-02",
            "description": "AMAZON.COM*AB1234567",
            "amount": 49.99,
            "transaction_type": "debit",
            "merchant": "Amazon",
            "category_hint": "Shopping",
        },
        {
            "date": "2026-02-03",
            "description": "DIRECT DEPOSIT PAYROLL",
            "amount": 2500.00,
            "transaction_type": "credit",
            "merchant": None,
            "category_hint": "Income",
        },
    ]
