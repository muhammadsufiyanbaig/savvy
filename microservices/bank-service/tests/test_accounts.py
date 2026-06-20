"""Bank account API tests."""
from __future__ import annotations

import pytest
from tests.conftest import VALID_ACCOUNT, VALID_SAVINGS, VALID_CREDIT


class TestCreateAccount:
    def test_create_checking(self, client):
        resp = client.post("/api/v1/banks/accounts", json=VALID_ACCOUNT)
        assert resp.status_code == 201
        data = resp.json()
        assert data["account_type"] == "checking"
        assert data["bank_name"] == "HBL Bank"
        assert data["is_primary"] is True
        assert data["is_active"] is True
        assert "id" in data

    def test_create_savings(self, client):
        resp = client.post("/api/v1/banks/accounts", json=VALID_SAVINGS)
        assert resp.status_code == 201
        assert resp.json()["account_type"] == "savings"

    def test_create_credit_card(self, client):
        resp = client.post("/api/v1/banks/accounts", json=VALID_CREDIT)
        assert resp.status_code == 201
        data = resp.json()
        assert data["account_type"] == "credit_card"
        assert float(data["credit_limit"]) == 200000.0

    def test_create_invalid_type(self, client):
        payload = {**VALID_ACCOUNT, "account_type": "crypto"}
        resp = client.post("/api/v1/banks/accounts", json=payload)
        assert resp.status_code == 422

    def test_create_currency_uppercased(self, client):
        payload = {**VALID_ACCOUNT, "currency": "pkr", "is_primary": False}
        resp = client.post("/api/v1/banks/accounts", json=payload)
        assert resp.status_code == 201
        assert resp.json()["currency"] == "PKR"

    def test_single_primary_enforced(self, client):
        """Setting new account as primary demotes old primary."""
        second_primary = {**VALID_SAVINGS, "is_primary": True, "account_name": "Second Primary"}
        resp = client.post("/api/v1/banks/accounts", json=second_primary)
        assert resp.status_code == 201
        new_id = resp.json()["id"]

        # List all — only new one should be primary
        list_resp = client.get("/api/v1/banks/accounts?is_active=true")
        primaries = [a for a in list_resp.json()["accounts"] if a["is_primary"]]
        assert len(primaries) == 1
        assert primaries[0]["id"] == new_id


class TestListAccounts:
    def test_list(self, client):
        resp = client.get("/api/v1/banks/accounts")
        assert resp.status_code == 200
        data = resp.json()
        assert "accounts" in data
        assert "summary" in data
        assert "total" in data

    def test_list_filter_type(self, client):
        client.post("/api/v1/banks/accounts", json={**VALID_SAVINGS, "is_primary": False})
        resp = client.get("/api/v1/banks/accounts?account_type=savings")
        assert resp.status_code == 200
        for a in resp.json()["accounts"]:
            assert a["account_type"] == "savings"

    def test_summary_keys(self, client):
        resp = client.get("/api/v1/banks/accounts")
        summary = resp.json()["summary"]
        assert "total_balance" in summary
        assert "total_accounts" in summary


class TestGetAccount:
    def test_get_existing(self, client):
        create = client.post("/api/v1/banks/accounts", json={**VALID_ACCOUNT, "is_primary": False})
        acc_id = create.json()["id"]
        resp = client.get(f"/api/v1/banks/accounts/{acc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == acc_id
        assert "statement_count" in data

    def test_get_not_found(self, client):
        resp = client.get("/api/v1/banks/accounts/999999")
        assert resp.status_code == 404


class TestUpdateAccount:
    def test_update_balance(self, client):
        create = client.post("/api/v1/banks/accounts", json={**VALID_ACCOUNT, "is_primary": False})
        acc_id = create.json()["id"]
        resp = client.put(f"/api/v1/banks/accounts/{acc_id}", json={"balance": "200000.00"})
        assert resp.status_code == 200
        assert float(resp.json()["balance"]) == 200000.0

    def test_update_deactivate(self, client):
        create = client.post("/api/v1/banks/accounts", json={**VALID_ACCOUNT, "is_primary": False})
        acc_id = create.json()["id"]
        resp = client.put(f"/api/v1/banks/accounts/{acc_id}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_update_not_found(self, client):
        resp = client.put("/api/v1/banks/accounts/999999", json={"balance": "100.00"})
        assert resp.status_code == 404


class TestDeleteAccount:
    def test_delete_success(self, client):
        create = client.post("/api/v1/banks/accounts", json={**VALID_ACCOUNT, "is_primary": False})
        acc_id = create.json()["id"]
        resp = client.delete(f"/api/v1/banks/accounts/{acc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_account_id"] == acc_id
        assert "statements_deleted" in data

        # Confirm gone
        get_resp = client.get(f"/api/v1/banks/accounts/{acc_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/v1/banks/accounts/999999")
        assert resp.status_code == 404
