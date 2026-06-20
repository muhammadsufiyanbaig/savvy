"""Budget and spending limit API tests."""
from __future__ import annotations

import pytest
from datetime import date

from tests.conftest import VALID_BUDGET, VALID_SPENDING_LIMIT


class TestCreateBudget:
    def test_create_success(self, client):
        resp = client.post("/api/v1/budgets", json=VALID_BUDGET)
        assert resp.status_code == 201
        data = resp.json()
        assert data["category"] == "Food"
        assert float(data["allocated_amount"]) == 20000.0
        assert float(data["spent_amount"]) == 0.0

    def test_create_invalid_period(self, client):
        payload = {**VALID_BUDGET, "period": "biweekly"}
        resp = client.post("/api/v1/budgets", json=payload)
        assert resp.status_code == 422

    def test_create_end_before_start(self, client):
        payload = {
            **VALID_BUDGET,
            "period_start_date": "2025-06-30",
            "period_end_date": "2025-06-01",
        }
        resp = client.post("/api/v1/budgets", json=payload)
        assert resp.status_code == 422


class TestListBudgets:
    def test_list(self, client):
        client.post("/api/v1/budgets", json=VALID_BUDGET)
        resp = client.get("/api/v1/budgets?current_period_only=false")
        assert resp.status_code == 200
        data = resp.json()
        assert "budgets" in data
        assert "total" in data


class TestBudgetStatus:
    def test_status(self, client):
        resp = client.get("/api/v1/budgets/status?period=monthly")
        assert resp.status_code == 200
        data = resp.json()
        assert "period" in data
        assert "total_allocated" in data


class TestGetBudget:
    def test_get_existing(self, client):
        create = client.post("/api/v1/budgets", json=VALID_BUDGET)
        budget_id = create.json()["id"]
        resp = client.get(f"/api/v1/budgets/{budget_id}")
        assert resp.status_code == 200

    def test_get_not_found(self, client):
        resp = client.get("/api/v1/budgets/999999")
        assert resp.status_code == 404


class TestUpdateBudget:
    def test_update_amount(self, client):
        create = client.post("/api/v1/budgets", json=VALID_BUDGET)
        budget_id = create.json()["id"]
        resp = client.put(f"/api/v1/budgets/{budget_id}", json={"allocated_amount": "25000.00"})
        assert resp.status_code == 200
        assert float(resp.json()["allocated_amount"]) == 25000.0


class TestDeleteBudget:
    def test_delete_success(self, client):
        create = client.post("/api/v1/budgets", json=VALID_BUDGET)
        budget_id = create.json()["id"]
        resp = client.delete(f"/api/v1/budgets/{budget_id}")
        assert resp.status_code == 200
        resp2 = client.get(f"/api/v1/budgets/{budget_id}")
        assert resp2.status_code == 404


# ── Spending Limits ────────────────────────────────────────────────────────────

class TestSpendingLimits:
    def test_create_limits(self, client):
        resp = client.post("/api/v1/spending-limits", json=VALID_SPENDING_LIMIT)
        assert resp.status_code == 201
        data = resp.json()
        assert float(data["daily_limit"]) == 2000.0
        assert float(data["weekly_limit"]) == 10000.0

    def test_get_limits(self, client):
        resp = client.get("/api/v1/spending-limits")
        assert resp.status_code == 200

    def test_get_status(self, client):
        resp = client.get("/api/v1/spending-limits/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_limit" in data
        assert "alerts" in data

    def test_patch_limits(self, client):
        client.post("/api/v1/spending-limits", json=VALID_SPENDING_LIMIT)
        resp = client.patch("/api/v1/spending-limits", json={"daily_limit": "3000.00"})
        assert resp.status_code == 200
        assert float(resp.json()["daily_limit"]) == 3000.0

    def test_delete_limits(self, client):
        client.post("/api/v1/spending-limits", json=VALID_SPENDING_LIMIT)
        resp = client.delete("/api/v1/spending-limits")
        assert resp.status_code == 200
