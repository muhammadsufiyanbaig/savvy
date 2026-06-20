"""Bank statement API tests."""
from __future__ import annotations

import io
import pytest

from tests.conftest import VALID_ACCOUNT, make_pdf_upload


def _create_account(client, is_primary=False):
    resp = client.post("/api/v1/banks/accounts", json={**VALID_ACCOUNT, "is_primary": is_primary})
    assert resp.status_code == 201
    return resp.json()["id"]


class TestUploadStatement:
    def test_upload_pdf(self, client):
        acc_id = _create_account(client)
        resp = client.post(
            "/api/v1/banks/statements/upload",
            files=make_pdf_upload("jan_statement.pdf"),
            data={
                "account_id": acc_id,
                "statement_period_start": "2026-01-01",
                "statement_period_end": "2026-01-31",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_name"] == "jan_statement.pdf"
        assert data["file_type"] == "pdf"
        assert data["processing_status"] == "uploaded"
        assert data["statement_month"] == "2026-01"
        assert "id" in data

    def test_upload_csv(self, client):
        acc_id = _create_account(client)
        csv_content = b"date,description,amount\n2026-01-15,Grocery,-500\n"
        resp = client.post(
            "/api/v1/banks/statements/upload",
            files={"file": ("transactions.csv", io.BytesIO(csv_content), "text/csv")},
            data={"account_id": acc_id},
        )
        assert resp.status_code == 201
        assert resp.json()["file_type"] == "csv"

    def test_upload_invalid_type(self, client):
        acc_id = _create_account(client)
        resp = client.post(
            "/api/v1/banks/statements/upload",
            files={"file": ("virus.exe", io.BytesIO(b"bad"), "application/x-msdownload")},
            data={"account_id": acc_id},
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]

    def test_upload_empty_file(self, client):
        acc_id = _create_account(client)
        resp = client.post(
            "/api/v1/banks/statements/upload",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
            data={"account_id": acc_id},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_upload_account_not_found(self, client):
        resp = client.post(
            "/api/v1/banks/statements/upload",
            files=make_pdf_upload(),
            data={"account_id": 999999},
        )
        assert resp.status_code == 404

    def test_upload_inactive_account(self, client):
        acc_id = _create_account(client)
        client.put(f"/api/v1/banks/accounts/{acc_id}", json={"is_active": False})
        resp = client.post(
            "/api/v1/banks/statements/upload",
            files=make_pdf_upload(),
            data={"account_id": acc_id},
        )
        assert resp.status_code == 400

    def test_download_url_present(self, client):
        """S3 mock returns presigned URL — should appear in upload response."""
        acc_id = _create_account(client)
        resp = client.post(
            "/api/v1/banks/statements/upload",
            files=make_pdf_upload(),
            data={"account_id": acc_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        # S3 is mocked — download_url populated
        assert data.get("download_url") is not None


class TestListStatements:
    def test_list_empty(self, client):
        resp = client.get("/api/v1/banks/statements?offset=999999")
        assert resp.status_code == 200
        data = resp.json()
        assert "statements" in data
        assert "total" in data

    def test_list_after_upload(self, client):
        acc_id = _create_account(client)
        client.post(
            "/api/v1/banks/statements/upload",
            files=make_pdf_upload("list_test.pdf"),
            data={"account_id": acc_id},
        )
        resp = client.get(f"/api/v1/banks/statements?account_id={acc_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_filter_status(self, client):
        resp = client.get("/api/v1/banks/statements?status=uploaded")
        assert resp.status_code == 200

    def test_list_pagination(self, client):
        resp = client.get("/api/v1/banks/statements?limit=5&offset=0")
        assert resp.status_code == 200


class TestGetStatement:
    def test_get_existing(self, client):
        acc_id = _create_account(client)
        upload = client.post(
            "/api/v1/banks/statements/upload",
            files=make_pdf_upload("get_test.pdf"),
            data={"account_id": acc_id},
        )
        stmt_id = upload.json()["id"]
        resp = client.get(f"/api/v1/banks/statements/{stmt_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == stmt_id

    def test_get_not_found(self, client):
        resp = client.get("/api/v1/banks/statements/999999")
        assert resp.status_code == 404


class TestDeleteStatement:
    def test_delete_success(self, client):
        acc_id = _create_account(client)
        upload = client.post(
            "/api/v1/banks/statements/upload",
            files=make_pdf_upload("delete_test.pdf"),
            data={"account_id": acc_id},
        )
        stmt_id = upload.json()["id"]
        resp = client.delete(f"/api/v1/banks/statements/{stmt_id}")
        assert resp.status_code == 200

        # Confirm gone
        get_resp = client.get(f"/api/v1/banks/statements/{stmt_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/v1/banks/statements/999999")
        assert resp.status_code == 404


class TestCascadeDeleteWithStatements:
    def test_delete_account_removes_statements(self, client):
        """Deleting account should cascade-delete its statements."""
        acc_id = _create_account(client)

        # Upload 2 statements
        for i in range(2):
            client.post(
                "/api/v1/banks/statements/upload",
                files=make_pdf_upload(f"cascade_test_{i}.pdf"),
                data={"account_id": acc_id},
            )

        # Confirm statements exist
        list_resp = client.get(f"/api/v1/banks/statements?account_id={acc_id}")
        assert list_resp.json()["total"] >= 2

        # Delete account
        del_resp = client.delete(f"/api/v1/banks/accounts/{acc_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["statements_deleted"] >= 2

        # Statements should be gone
        list_resp2 = client.get(f"/api/v1/banks/statements?account_id={acc_id}")
        assert list_resp2.json()["total"] == 0
