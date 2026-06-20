"""Savings goals API tests."""
from __future__ import annotations

import pytest
from tests.conftest import VALID_SAVINGS_GOAL


class TestCreateGoal:
    def test_create_success(self, client):
        resp = client.post("/api/v1/savings", json=VALID_SAVINGS_GOAL)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Emergency Fund"
        assert data["status"] == "active"
        assert float(data["progress"]) == 0.0

    def test_create_missing_name(self, client):
        payload = {k: v for k, v in VALID_SAVINGS_GOAL.items() if k != "name"}
        resp = client.post("/api/v1/savings", json=payload)
        assert resp.status_code == 422

    def test_create_zero_target(self, client):
        payload = {**VALID_SAVINGS_GOAL, "target_amount": "0"}
        resp = client.post("/api/v1/savings", json=payload)
        assert resp.status_code == 422


class TestListGoals:
    def test_list(self, client):
        client.post("/api/v1/savings", json=VALID_SAVINGS_GOAL)
        resp = client.get("/api/v1/savings")
        assert resp.status_code == 200
        data = resp.json()
        assert "goals" in data
        assert "summary" in data


class TestDeposit:
    def test_deposit_success(self, client):
        create = client.post("/api/v1/savings", json=VALID_SAVINGS_GOAL)
        goal_id = create.json()["id"]
        resp = client.post(f"/api/v1/savings/{goal_id}/deposit", json={"amount": "5000.00"})
        assert resp.status_code == 201
        assert resp.json()["transaction_type"] == "deposit"

        # Check goal updated
        goal_resp = client.get(f"/api/v1/savings/{goal_id}")
        assert float(goal_resp.json()["current_amount"]) == 5000.0

    def test_deposit_completes_goal(self, client):
        payload = {**VALID_SAVINGS_GOAL, "target_amount": "1000.00", "name": "SmallGoal"}
        create = client.post("/api/v1/savings", json=payload)
        goal_id = create.json()["id"]
        client.post(f"/api/v1/savings/{goal_id}/deposit", json={"amount": "1000.00"})
        goal_resp = client.get(f"/api/v1/savings/{goal_id}")
        assert goal_resp.json()["status"] == "completed"

    def test_deposit_completed_goal(self, client):
        payload = {**VALID_SAVINGS_GOAL, "target_amount": "100.00", "name": "TinyGoal"}
        create = client.post("/api/v1/savings", json=payload)
        goal_id = create.json()["id"]
        client.post(f"/api/v1/savings/{goal_id}/deposit", json={"amount": "100.00"})
        # Try deposit again — completed goal
        resp = client.post(f"/api/v1/savings/{goal_id}/deposit", json={"amount": "50.00"})
        assert resp.status_code == 400


class TestWithdraw:
    def test_withdraw_success(self, client):
        create = client.post("/api/v1/savings", json=VALID_SAVINGS_GOAL)
        goal_id = create.json()["id"]
        client.post(f"/api/v1/savings/{goal_id}/deposit", json={"amount": "10000.00"})
        resp = client.post(f"/api/v1/savings/{goal_id}/withdraw", json={"amount": "3000.00"})
        assert resp.status_code == 201
        assert resp.json()["transaction_type"] == "withdrawal"

    def test_withdraw_insufficient_balance(self, client):
        create = client.post("/api/v1/savings", json=VALID_SAVINGS_GOAL)
        goal_id = create.json()["id"]
        resp = client.post(f"/api/v1/savings/{goal_id}/withdraw", json={"amount": "999999.00"})
        assert resp.status_code == 400

    def test_withdraw_goal_not_found(self, client):
        resp = client.post("/api/v1/savings/999999/withdraw", json={"amount": "100.00"})
        assert resp.status_code == 404


class TestDeleteGoal:
    def test_delete_success(self, client):
        create = client.post("/api/v1/savings", json=VALID_SAVINGS_GOAL)
        goal_id = create.json()["id"]
        resp = client.delete(f"/api/v1/savings/{goal_id}")
        assert resp.status_code == 200
        # Should 404 now
        resp2 = client.get(f"/api/v1/savings/{goal_id}")
        assert resp2.status_code == 404
