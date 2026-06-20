"""Finance service test configuration."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── Set up SQLite engine BEFORE importing app modules ────────────────────────
# StaticPool: all connections share the same in-memory DB (required for `:memory:`).
# Must happen before any app imports so lifespan uses the test engine.
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch app.core.database BEFORE importing FastAPI app
import app.core.database as _db_module
_db_module.engine = test_engine
_db_module.SessionLocal = TestingSessionLocal

# ── Now import app ────────────────────────────────────────────────────────────
from fastapi.testclient import TestClient

from app.core.database import Base
from app.core.security import get_current_user_id
from app.core.database import get_db
from app.main import app


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user_id():
    return 1


# ── Mock Kafka producer (session-wide) ────────────────────────────────────────
_kafka_patcher = patch("app.events.producer._get_producer", return_value=None)


@pytest.fixture(scope="session", autouse=True)
def mock_kafka():
    _kafka_patcher.start()
    yield
    _kafka_patcher.stop()


# ── App dependency overrides ──────────────────────────────────────────────────
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user_id] = override_get_current_user_id


@pytest.fixture(scope="session")
def db_tables():
    """Create all tables once for the session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def client(db_tables):
    with TestClient(app) as c:
        yield c


# ── Common test payload fixtures ──────────────────────────────────────────────
VALID_EXPENSE = {
    "amount": "150.00",
    "currency": "PKR",
    "category": "Food",
    "expense_type": "variable",
    "description": "Lunch",
    "payment_method": "cash",
    "transaction_date": datetime.utcnow().isoformat(),
}

VALID_SAVINGS_GOAL = {
    "name": "Emergency Fund",
    "goal_type": "emergency_fund",
    "target_amount": "100000.00",
    "currency": "PKR",
}

VALID_BUDGET = {
    "category": "Food",
    "allocated_amount": "20000.00",
    "currency": "PKR",
    "period": "monthly",
    "period_start_date": date.today().replace(day=1).isoformat(),
    "period_end_date": date.today().replace(day=28).isoformat(),
}

VALID_SPENDING_LIMIT = {
    "daily_limit": "2000.00",
    "weekly_limit": "10000.00",
    "monthly_limit": "50000.00",
    "currency": "PKR",
}

VALID_ZAKAT = {
    "calculation_date": date.today().isoformat(),
    "currency": "PKR",
    "nisab_threshold": "133613.00",   # silver nisab in PKR approx
    "cash_in_hand": "50000.00",
    "bank_balance": "200000.00",
    "gold_value": "100000.00",
    "silver_value": "0.00",
    "investments": "0.00",
    "immediate_debts": "10000.00",
}
