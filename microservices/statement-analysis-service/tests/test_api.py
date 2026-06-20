"""API endpoint tests."""

import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest


# ── /health ────────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "statement-analysis-service"
    assert "dependencies" in data


# ── /formats ───────────────────────────────────────────────────────────────────

def test_get_formats(client):
    resp = client.get("/api/v1/statements/formats")
    assert resp.status_code == 200
    data = resp.json()
    assert "supported_formats" in data
    formats = {f["format"] for f in data["supported_formats"]}
    assert formats == {"PDF", "CSV", "Excel"}


# ── /analyze ───────────────────────────────────────────────────────────────────

def test_analyze_no_auth(client):
    resp = client.post(
        "/api/v1/statements/analyze",
        json={"statement_id": "stmt_001", "file_url": "s3://bucket/test.pdf", "user_id": 1},
    )
    assert resp.status_code == 401


def test_analyze_unsupported_format(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/analyze",
        headers=auth_headers,
        json={"statement_id": "stmt_bad", "file_url": "s3://bucket/test.zip", "user_id": 1},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["detail"]["error"] == "invalid_file_format"


def test_analyze_pdf_returns_202(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/analyze",
        headers=auth_headers,
        json={
            "statement_id": "stmt_pdf_001",
            "file_url": "s3://test-bucket/user_1/statement.pdf",
            "user_id": 1,
            "bank_name": "Chase",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "processing"
    assert data["statement_id"] == "stmt_pdf_001"
    assert "processing_id" in data
    assert data["processing_id"] != ""
    assert data["estimated_time_seconds"] > 0


def test_analyze_csv_returns_202(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/analyze",
        headers=auth_headers,
        json={"statement_id": "stmt_csv_001", "file_url": "s3://bucket/statement.csv", "user_id": 1},
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "processing"


def test_analyze_excel_returns_202(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/analyze",
        headers=auth_headers,
        json={"statement_id": "stmt_xlsx_001", "file_url": "s3://bucket/statement.xlsx", "user_id": 1},
    )
    assert resp.status_code == 202


# ── /{id}/status ───────────────────────────────────────────────────────────────

def test_status_no_auth(client):
    resp = client.get("/api/v1/statements/stmt_001/status")
    assert resp.status_code == 401


def test_status_not_found_returns_queued(client, auth_headers):
    resp = client.get("/api/v1/statements/nonexistent_stmt/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["statement_id"] == "nonexistent_stmt"


def test_status_after_analyze(client, auth_headers):
    stmt_id = "stmt_status_test"
    # Trigger analysis (sets Redis status)
    resp = client.post(
        "/api/v1/statements/analyze",
        headers=auth_headers,
        json={"statement_id": stmt_id, "file_url": "s3://bucket/test.pdf", "user_id": 1},
    )
    assert resp.status_code == 202
    processing_id = resp.json()["processing_id"]

    # Wait briefly for background thread to seed Redis
    time.sleep(0.1)

    status_resp = client.get(f"/api/v1/statements/{stmt_id}/status", headers=auth_headers)
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["statement_id"] == stmt_id
    assert data["status"] in ("processing", "failed", "completed", "queued")


def test_status_from_redis(client, auth_headers):
    """Directly seed Redis store and verify status endpoint reads it."""
    from tests.conftest import _status_store

    stmt_id = "stmt_redis_direct"
    _status_store[f"stmt_status:{stmt_id}"] = {
        "statement_id": stmt_id,
        "processing_id": "proc_abc",
        "status": "completed",
        "progress_percentage": 100,
        "started_at": "2026-02-01T10:00:00+00:00",
        "completed_at": "2026-02-01T10:00:45+00:00",
        "processing_time_seconds": 45,
        "results": {
            "total_transactions": 10,
            "successfully_extracted": 10,
            "failed_extractions": 0,
            "categories_assigned": 10,
            "confidence_scores": {"high": 8, "medium": 2, "low": 0},
        },
        "error": None,
    }

    resp = client.get(f"/api/v1/statements/{stmt_id}/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["results"]["total_transactions"] == 10
    assert data["processing_time_seconds"] == 45


# ── /categorize ────────────────────────────────────────────────────────────────

def test_categorize_no_auth(client):
    resp = client.post(
        "/api/v1/statements/categorize",
        json={"description": "STARBUCKS COFFEE", "amount": 5.75},
    )
    assert resp.status_code == 401


def test_categorize_starbucks(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/categorize",
        headers=auth_headers,
        json={"description": "STARBUCKS COFFEE #1234", "amount": 5.75, "date": "2026-02-01"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "Food & Dining"
    assert data["subcategory"] == "Coffee Shops"
    assert data["confidence_score"] > 0


def test_categorize_amazon(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/categorize",
        headers=auth_headers,
        json={"description": "AMAZON.COM*XY123456", "amount": 29.99},
    )
    assert resp.status_code == 200
    assert resp.json()["category"] == "Shopping"


def test_categorize_unknown(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/categorize",
        headers=auth_headers,
        json={"description": "XXXXXXXXX UNKNOWN MERCHANT 9999", "amount": 100.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "category" in data
    assert "confidence_score" in data
    assert 0 <= data["confidence_score"] <= 1


def test_categorize_gas_station(client, auth_headers):
    resp = client.post(
        "/api/v1/statements/categorize",
        headers=auth_headers,
        json={"description": "SHELL OIL 12345678 HOUSTON TX", "amount": 45.00},
    )
    assert resp.status_code == 200
    assert resp.json()["category"] == "Transportation"
