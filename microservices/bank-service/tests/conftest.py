"""Bank service test configuration."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── SQLite engine — patch BEFORE importing app ────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

import app.core.database as _db_module
_db_module.engine = test_engine
_db_module.SessionLocal = TestingSessionLocal

# ── Now import app ─────────────────────────────────────────────────────────────
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.security import get_current_user_id
from app.main import app


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user_id():
    return 1


# ── Mock Kafka ─────────────────────────────────────────────────────────────────
_kafka_patcher = patch("app.events.producer._get_producer", return_value=None)


@pytest.fixture(scope="session", autouse=True)
def mock_kafka():
    _kafka_patcher.start()
    yield
    _kafka_patcher.stop()


# ── Mock S3 ────────────────────────────────────────────────────────────────────
_mock_s3 = MagicMock()
_mock_s3.upload_fileobj.return_value = None
_mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned/test.pdf?token=abc"
_mock_s3.delete_object.return_value = {}

_s3_patcher = patch("app.services.s3_service._get_s3", return_value=_mock_s3)


@pytest.fixture(scope="session", autouse=True)
def mock_s3():
    _s3_patcher.start()
    yield
    _s3_patcher.stop()


# ── App overrides ──────────────────────────────────────────────────────────────
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user_id] = override_get_current_user_id


@pytest.fixture(scope="session")
def db_tables():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def client(db_tables):
    with TestClient(app) as c:
        yield c


# ── Test data ─────────────────────────────────────────────────────────────────
VALID_ACCOUNT = {
    "account_name": "Main Checking",
    "bank_name": "HBL Bank",
    "account_type": "checking",
    "balance": "150000.00",
    "currency": "PKR",
    "purpose": "Primary daily account",
    "is_primary": True,
}

VALID_SAVINGS = {
    "account_name": "Emergency Fund",
    "bank_name": "MCB Bank",
    "account_type": "savings",
    "balance": "500000.00",
    "currency": "PKR",
    "interest_rate": "5.5",
}

VALID_CREDIT = {
    "account_name": "Visa Platinum",
    "bank_name": "Standard Chartered",
    "account_type": "credit_card",
    "balance": "-25000.00",
    "currency": "PKR",
    "credit_limit": "200000.00",
}


def make_pdf_upload(filename: str = "statement.pdf") -> dict:
    """Create a fake file upload dict for TestClient."""
    content = b"%PDF-1.4 fake pdf content for testing"
    return {"file": (filename, io.BytesIO(content), "application/pdf")}
