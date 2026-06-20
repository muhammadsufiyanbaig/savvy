"""Zakat and Qurbani API tests."""
from __future__ import annotations

import pytest
from datetime import date
from tests.conftest import VALID_ZAKAT


class TestNisab:
    def test_get_nisab_usd(self, client):
        resp = client.get("/api/v1/zakat/nisab?currency=USD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["currency"] == "USD"
        assert data["threshold"] > 0
        assert data["recommended_nisab"] == "silver"

    def test_get_nisab_pkr(self, client):
        resp = client.get("/api/v1/zakat/nisab?currency=PKR")
        assert resp.status_code == 200
        data = resp.json()
        assert data["currency"] == "PKR"
        assert data["threshold"] > 100000  # PKR equivalent much higher than USD


class TestZakatCalculation:
    def test_calculate_success(self, client):
        resp = client.post("/api/v1/zakat/calculate", json=VALID_ZAKAT)
        assert resp.status_code == 201
        data = resp.json()
        assert "zakatable_amount" in data
        assert "zakat_due" in data
        assert "nisab_met" in data
        assert data["currency"] == "PKR"

    def test_calculate_above_nisab(self, client):
        payload = {
            **VALID_ZAKAT,
            "bank_balance": "5000000.00",
            "cash_in_hand": "1000000.00",
        }
        resp = client.post("/api/v1/zakat/calculate", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["nisab_met"] is True
        assert float(data["zakat_due"]) > 0

    def test_calculate_zakat_is_2_5_percent(self, client):
        payload = {
            "calculation_date": date.today().isoformat(),
            "currency": "USD",
            "nisab_threshold": "476.00",
            "bank_balance": "10000.00",
            "cash_in_hand": "0.00",
            "immediate_debts": "0.00",
        }
        resp = client.post("/api/v1/zakat/calculate", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        if data["nisab_met"]:
            expected = round(10000 * 0.025, 2)
            assert abs(float(data["zakat_due"]) - expected) < 0.01

    def test_calculate_missing_nisab_threshold(self, client):
        payload = {k: v for k, v in VALID_ZAKAT.items() if k != "nisab_threshold"}
        resp = client.post("/api/v1/zakat/calculate", json=payload)
        assert resp.status_code == 422


class TestZakatList:
    def test_list(self, client):
        resp = client.get("/api/v1/zakat")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert "summary" in data

    def test_list_after_create(self, client):
        client.post("/api/v1/zakat/calculate", json=VALID_ZAKAT)
        resp = client.get("/api/v1/zakat")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_filter_paid(self, client):
        resp = client.get("/api/v1/zakat?paid=false")
        assert resp.status_code == 200


class TestZakatPayment:
    def test_mark_paid(self, client):
        create = client.post("/api/v1/zakat/calculate", json=VALID_ZAKAT)
        record_id = create.json()["id"]
        resp = client.patch(f"/api/v1/zakat/{record_id}/payment", json={
            "amount_paid": "5000.00",
            "payment_date": date.today().isoformat(),
            "payment_status": "paid",
        })
        assert resp.status_code == 200
        assert resp.json()["payment_status"] == "paid"

    def test_payment_not_found(self, client):
        resp = client.patch("/api/v1/zakat/999999/payment", json={
            "amount_paid": "100.00",
            "payment_date": date.today().isoformat(),
            "payment_status": "paid",
        })
        assert resp.status_code == 404


class TestQurbani:
    VALID_QURBANI = {
        "target_year": 2026,
        "animal_type": "goat",
        "animal_shares": 1,
        "target_amount": "25000.00",
        "currency": "PKR",
    }

    def test_get_prices(self, client):
        resp = client.get("/api/v1/qurbani/prices")
        assert resp.status_code == 200
        data = resp.json()
        assert "animals" in data
        assert "goat" in data["animals"]
        assert "cow" in data["animals"]

    def test_create_qurbani(self, client):
        resp = client.post("/api/v1/qurbani", json=self.VALID_QURBANI)
        assert resp.status_code == 201
        data = resp.json()
        assert data["animal_type"] == "goat"
        assert float(data["current_amount"]) == 0.0
        assert data["status"] == "saving"

    def test_create_missing_target_year(self, client):
        payload = {k: v for k, v in self.VALID_QURBANI.items() if k != "target_year"}
        resp = client.post("/api/v1/qurbani", json=payload)
        assert resp.status_code == 422

    def test_contribute(self, client):
        create = client.post("/api/v1/qurbani", json=self.VALID_QURBANI)
        record_id = create.json()["id"]
        resp = client.post(f"/api/v1/qurbani/{record_id}/contribute", json={"amount": "10000.00"})
        assert resp.status_code == 200
        assert float(resp.json()["current_amount"]) == 10000.0

    def test_contribute_reaches_target(self, client):
        create = client.post("/api/v1/qurbani", json=self.VALID_QURBANI)
        record_id = create.json()["id"]
        target = float(create.json()["target_amount"])
        client.post(f"/api/v1/qurbani/{record_id}/contribute", json={"amount": str(target)})
        resp = client.get(f"/api/v1/qurbani/{record_id}")
        assert resp.json()["status"] == "ready"

    def test_list_qurbani(self, client):
        resp = client.get("/api/v1/qurbani")
        assert resp.status_code == 200
        data = resp.json()
        assert "savings" in data
        assert "summary" in data

    def test_filter_by_year(self, client):
        resp = client.get("/api/v1/qurbani?target_year=2026")
        assert resp.status_code == 200

    def test_delete_qurbani(self, client):
        create = client.post("/api/v1/qurbani", json=self.VALID_QURBANI)
        record_id = create.json()["id"]
        resp = client.delete(f"/api/v1/qurbani/{record_id}")
        assert resp.status_code == 200
        resp2 = client.get(f"/api/v1/qurbani/{record_id}")
        assert resp2.status_code == 404
