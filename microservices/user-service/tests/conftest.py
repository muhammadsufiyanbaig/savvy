"""
Pytest configuration and shared fixtures.

Uses an in-memory SQLite database so tests run without Docker.
Kafka and Redis are mocked to avoid external dependencies.
"""
from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# --------------------------------------------------------------------------- #
# In-memory SQLite engine for tests
# --------------------------------------------------------------------------- #
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db() -> Generator:
    """Fresh DB session per test, rolled back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db) -> Generator:
    """FastAPI TestClient with DB dependency overridden."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock Redis so token blacklist doesn't need a real Redis
    with patch("app.core.security.get_redis", return_value=None):
        # Mock Kafka so events don't fail
        with patch("app.services.user_service._get_producer", return_value=None):
            with TestClient(app) as c:
                yield c

    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Reusable data factories
# --------------------------------------------------------------------------- #
VALID_USER = {
    "email": "test@savvy.io",
    "username": "testuser",
    "password": "SecurePass1",
    "full_name": "Test User",
    "country": "Pakistan",
    "city": "Karachi",
    "currency": "PKR",
}


@pytest.fixture()
def registered_user(client):
    """Register a user and return the response JSON."""
    resp = client.post("/api/v1/users/register", json=VALID_USER)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def auth_headers(client, registered_user):
    """Login and return Authorization headers."""
    resp = client.post(
        "/api/v1/users/login",
        data={"username": VALID_USER["username"], "password": VALID_USER["password"]},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
