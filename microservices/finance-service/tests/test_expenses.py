"""Expense API tests."""
from __future__ import annotations

import pytest
from datetime import datetime, date

from tests.conftest import VALID_EXPENSE


class TestCreateExpense:
    def test_create_success(self, client):
        resp = client.post("/api/v1/expenses", json=VALID_EXPENSE)
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == "150.00"
        assert data["category"] == "Food"
        assert data["id"] is not None

    def test_create_invalid_category(self, client):
        payload = {**VALID_EXPENSE, "category": "InvalidCat"}
        resp = client.post("/api/v1/expenses", json=payload)
        assert resp.status_code == 422

    def test_create_negative_amount(self, client):
        payload = {**VALID_EXPENSE, "amount": "-100"}
        resp = client.post("/api/v1/expenses", json=payload)
        assert resp.status_code == 422

    def test_create_recurring(self, client):
        payload = {**VALID_EXPENSE, "is_recurring": True, "recurrence_pattern": "monthly"}
        resp = client.post("/api/v1/expenses", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_recurring"] is True
        assert data["next_occurrence_date"] is not None


class TestListExpenses:
    def test_list_empty(self, client):
        # Use fresh state from fixture isolation (no cross-test bleed in real run)
        resp = client.get("/api/v1/expenses?limit=1&offset=999999")
        assert resp.status_code == 200
        data = resp.json()
        assert "expenses" in data
        assert "total" in data

    def test_list_with_category_filter(self, client):
        # Create one first
        client.post("/api/v1/expenses", json=VALID_EXPENSE)
        resp = client.get("/api/v1/expenses?category=Food")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["category"] == "Food" for e in data["expenses"])

    def test_list_pagination(self, client):
        resp = client.get("/api/v1/expenses?limit=5&offset=0")
        assert resp.status_code == 200


class TestGetExpense:
    def test_get_existing(self, client):
        create = client.post("/api/v1/expenses", json=VALID_EXPENSE)
        expense_id = create.json()["id"]
        resp = client.get(f"/api/v1/expenses/{expense_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == expense_id

    def test_get_not_found(self, client):
        resp = client.get("/api/v1/expenses/999999")
        assert resp.status_code == 404


class TestUpdateExpense:
    def test_update_amount(self, client):
        create = client.post("/api/v1/expenses", json=VALID_EXPENSE)
        expense_id = create.json()["id"]
        resp = client.put(f"/api/v1/expenses/{expense_id}", json={"amount": "200.00"})
        assert resp.status_code == 200
        assert resp.json()["amount"] == "200.00"

    def test_update_not_found(self, client):
        resp = client.put("/api/v1/expenses/999999", json={"amount": "200.00"})
        assert resp.status_code == 404


class TestDeleteExpense:
    def test_delete_success(self, client):
        create = client.post("/api/v1/expenses", json=VALID_EXPENSE)
        expense_id = create.json()["id"]
        resp = client.delete(f"/api/v1/expenses/{expense_id}")
        assert resp.status_code == 200
        # Soft deleted — should 404 on get
        resp2 = client.get(f"/api/v1/expenses/{expense_id}")
        assert resp2.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/v1/expenses/999999")
        assert resp.status_code == 404


class TestExpenseSummary:
    def test_summary_requires_dates(self, client):
        resp = client.get("/api/v1/expenses/summary")
        assert resp.status_code == 422  # missing required query params

    def test_summary_success(self, client):
        start = date.today().replace(day=1).isoformat()
        end = date.today().isoformat()
        resp = client.get(f"/api/v1/expenses/summary?start_date={start}&end_date={end}")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_expenses" in data
        assert "by_category" in data

    def test_summary_invalid_date_range(self, client):
        resp = client.get("/api/v1/expenses/summary?start_date=2025-12-31&end_date=2025-01-01")
        assert resp.status_code == 400
