"""API endpoint tests."""

import pytest


# ── /health ────────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-recommendation-service"
    assert "dependencies" in data


# ── /recommendations ───────────────────────────────────────────────────────────

def test_recommendations_no_auth(client, rec_request_dict):
    resp = client.post("/api/v1/ai/recommendations", json=rec_request_dict)
    assert resp.status_code == 401


def test_recommendations_returns_200(client, auth_headers, rec_request_dict):
    resp = client.post("/api/v1/ai/recommendations", headers=auth_headers, json=rec_request_dict)
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert "total_count" in data
    assert "generated_at" in data
    assert data["total_count"] >= 1


def test_recommendations_low_savings_rate(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/recommendations",
        headers=auth_headers,
        json={
            "user_id": 1,
            "recommendation_types": ["savings"],
            "context": {"monthly_income": 3000, "monthly_expenses": 2900},
        },
    )
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert len(recs) >= 1
    priorities = [r["priority"] for r in recs]
    assert "high" in priorities


def test_recommendations_multiple_types(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/recommendations",
        headers=auth_headers,
        json={
            "user_id": 1,
            "recommendation_types": ["savings", "spending", "budget"],
            "context": {},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] >= 2


def test_recommendation_structure(client, auth_headers, rec_request_dict):
    resp = client.post("/api/v1/ai/recommendations", headers=auth_headers, json=rec_request_dict)
    rec = resp.json()["recommendations"][0]
    assert "id" in rec
    assert "type" in rec
    assert "title" in rec
    assert "description" in rec
    assert "recommended_action" in rec
    assert "confidence_score" in rec
    assert "priority" in rec


# ── /analyze-spending ──────────────────────────────────────────────────────────

def test_analyze_spending_no_auth(client):
    resp = client.post("/api/v1/ai/analyze-spending", json={"user_id": 1})
    assert resp.status_code == 401


def test_analyze_spending_empty(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/analyze-spending",
        headers=auth_headers,
        json={"user_id": 1, "period": "monthly", "expenses": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "analysis" in data
    assert "spending_trend" in data["analysis"]


def test_analyze_spending_with_expenses(client, auth_headers, sample_expenses):
    resp = client.post(
        "/api/v1/ai/analyze-spending",
        headers=auth_headers,
        json={"user_id": 1, "period": "last_3_months", "expenses": sample_expenses},
    )
    assert resp.status_code == 200
    analysis = resp.json()["analysis"]
    assert "top_categories" in analysis
    assert len(analysis["top_categories"]) >= 1
    assert "score" in analysis


# ── /recommendations/{id}/feedback ────────────────────────────────────────────

def test_feedback_no_auth(client):
    resp = client.post("/api/v1/ai/recommendations/rec_001/feedback", json={"rating": 4, "was_helpful": True})
    assert resp.status_code == 401


def test_feedback_valid(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/recommendations/rec_001/feedback",
        headers=auth_headers,
        json={"rating": 5, "was_helpful": True, "feedback_text": "Very useful", "is_implemented": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["feedback_recorded"] is True
    assert data["recommendation_id"] == "rec_001"


def test_feedback_invalid_rating(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/recommendations/rec_001/feedback",
        headers=auth_headers,
        json={"rating": 10, "was_helpful": True},
    )
    assert resp.status_code == 422


# ── /investments ───────────────────────────────────────────────────────────────

def test_investments_no_auth(client, investment_request_dict):
    resp = client.post("/api/v1/ai/investments", json=investment_request_dict)
    assert resp.status_code == 401


def test_investments_returns_200(client, auth_headers, investment_request_dict):
    resp = client.post("/api/v1/ai/investments", headers=auth_headers, json=investment_request_dict)
    assert resp.status_code == 200
    data = resp.json()
    assert "investments" in data
    assert "market_summary" in data
    assert "total_count" in data


def test_investments_structure(client, auth_headers, investment_request_dict):
    resp = client.post("/api/v1/ai/investments", headers=auth_headers, json=investment_request_dict)
    investments = resp.json()["investments"]
    assert len(investments) >= 1
    inv = investments[0]
    assert "id" in inv
    assert "investment_type" in inv
    assert "asset_name" in inv
    assert "expected_return" in inv
    assert "risk_level" in inv
    assert "confidence_score" in inv


def test_investments_market_summary(client, auth_headers, investment_request_dict):
    resp = client.post("/api/v1/ai/investments", headers=auth_headers, json=investment_request_dict)
    ms = resp.json()["market_summary"]
    assert "trend" in ms
    assert "sp500_ytd" in ms


def test_investments_invalid_risk_tolerance(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/investments",
        headers=auth_headers,
        json={
            "user_id": 1,
            "available_amount": 1000,
            "risk_tolerance": "extreme",   # invalid → normalised to "medium"
            "country": "USA",
        },
    )
    assert resp.status_code == 200


# ── /investments/shariah ───────────────────────────────────────────────────────

def test_shariah_investments_no_auth(client):
    resp = client.post(
        "/api/v1/ai/investments/shariah",
        json={"user_id": 1, "available_amount": 2000, "country": "Pakistan"},
    )
    assert resp.status_code == 401


def test_shariah_investments_returns_200(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/investments/shariah",
        headers=auth_headers,
        json={"user_id": 1, "available_amount": 2000, "country": "Pakistan", "risk_tolerance": "low"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "investments" in data
    assert "shariah_screening_note" in data
    assert "excluded_categories" in data
    assert len(data["excluded_categories"]) > 0


def test_shariah_all_compliant(client, auth_headers):
    resp = client.post(
        "/api/v1/ai/investments/shariah",
        headers=auth_headers,
        json={"user_id": 1, "available_amount": 3000, "country": "USA"},
    )
    assert resp.status_code == 200
    investments = resp.json()["investments"]
    for inv in investments:
        assert inv["is_shariah_compliant"] is True


# ── /insights ──────────────────────────────────────────────────────────────────

def test_insights_no_auth(client):
    resp = client.get("/api/v1/ai/insights")
    assert resp.status_code == 401


def test_insights_returns_200(client, auth_headers):
    resp = client.get("/api/v1/ai/insights", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "insights" in data
    assert "total_count" in data
    assert data["total_count"] >= 1


def test_insights_structure(client, auth_headers):
    resp = client.get("/api/v1/ai/insights", headers=auth_headers)
    insight = resp.json()["insights"][0]
    assert "id" in insight
    assert "type" in insight
    assert "title" in insight
    assert "message" in insight
    assert "priority" in insight
    assert "is_urgent" in insight
