"""
Routing tests — verify each path prefix resolves to the correct upstream service.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.proxy.router import _resolve_service


# ── Unit: _resolve_service ────────────────────────────────────────────────────

class TestResolveService:
    def test_user_service(self):
        assert _resolve_service("/api/v1/users/1") == settings.USER_SERVICE_URL

    def test_user_login(self):
        assert _resolve_service("/api/v1/users/login") == settings.USER_SERVICE_URL

    def test_expenses(self):
        assert _resolve_service("/api/v1/expenses") == settings.FINANCE_SERVICE_URL

    def test_savings(self):
        assert _resolve_service("/api/v1/savings/goals") == settings.FINANCE_SERVICE_URL

    def test_budgets(self):
        assert _resolve_service("/api/v1/budgets/1") == settings.FINANCE_SERVICE_URL

    def test_spending_limits(self):
        assert _resolve_service("/api/v1/spending-limits") == settings.FINANCE_SERVICE_URL

    def test_zakat(self):
        assert _resolve_service("/api/v1/zakat/calculate") == settings.FINANCE_SERVICE_URL

    def test_qurbani(self):
        assert _resolve_service("/api/v1/qurbani/goals") == settings.FINANCE_SERVICE_URL

    def test_cash_savings(self):
        assert _resolve_service("/api/v1/cash-savings") == settings.FINANCE_SERVICE_URL

    def test_banks(self):
        assert _resolve_service("/api/v1/banks/accounts") == settings.BANK_SERVICE_URL

    def test_statements(self):
        assert _resolve_service("/api/v1/statements/analyze") == settings.STATEMENT_SERVICE_URL

    def test_ai(self):
        assert _resolve_service("/api/v1/ai/recommendations") == settings.AI_SERVICE_URL

    def test_ai_investments(self):
        assert _resolve_service("/api/v1/ai/investments") == settings.AI_SERVICE_URL

    def test_notifications(self):
        assert _resolve_service("/api/v1/notifications") == settings.NOTIFICATION_SERVICE_URL

    def test_unknown_prefix_returns_none(self):
        assert _resolve_service("/api/v1/unknown-service") is None

    def test_root_returns_none(self):
        assert _resolve_service("/health") is None


# ── Integration: HTTP routing via TestClient ──────────────────────────────────

class TestHTTPRouting:
    def test_health_endpoint(self, client, mock_http_client):
        """Gateway /health aggregates all services — mock returns 200 for each."""
        mock_http_client.get = AsyncMock(
            return_value=type("R", (), {"status_code": 200})()
        )
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["gateway"] == "healthy"
        assert "services" in data

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "Savvy API Gateway" in data["service"]
        assert len(data["upstream_services"]) == 6

    def test_unknown_path_returns_404(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/nonexistent-service/test", headers=auth_headers)
        assert resp.status_code == 404

    def test_request_id_injected_in_response(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert "x-request-id" in resp.headers

    def test_custom_request_id_preserved(self, client, mock_http_client, auth_headers):
        custom_id = "test-req-12345"
        headers = {**auth_headers, "X-Request-ID": custom_id}
        resp = client.get("/api/v1/users/me", headers=headers)
        assert resp.headers.get("x-request-id") == custom_id

    def test_process_time_header_present(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert "x-process-time" in resp.headers
        # Value should end with "ms"
        assert resp.headers["x-process-time"].endswith("ms")

    def test_upstream_status_code_propagated(self, client, mock_http_client, auth_headers):
        """If upstream returns 422, gateway must relay it unchanged."""
        from httpx import Response as HResp
        mock_upstream = AsyncMock()
        mock_upstream.__aenter__ = AsyncMock(
            return_value=HResp(
                status_code=422,
                content=b'{"detail":"Validation error"}',
                headers={"content-type": "application/json"},
            )
        )
        mock_upstream.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.stream.return_value = mock_upstream
        resp = client.post("/api/v1/expenses", headers=auth_headers, json={})
        assert resp.status_code == 422

    def test_upstream_503_propagated(self, client, mock_http_client, auth_headers):
        import httpx
        mock_http_client.stream.side_effect = httpx.ConnectError("refused")
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 503

    def test_upstream_timeout_returns_504(self, client, mock_http_client, auth_headers):
        import httpx
        mock_http_client.stream.side_effect = httpx.TimeoutException("timeout")
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 504

    def test_get_request_forwarded(self, client, mock_http_client, auth_headers):
        resp = client.get("/api/v1/ai/insights", headers=auth_headers)
        assert mock_http_client.stream.called
        call_args = mock_http_client.stream.call_args
        assert call_args.kwargs.get("method") == "GET" or call_args.args[0] == "GET"

    def test_post_body_forwarded(self, client, mock_http_client, auth_headers):
        client.post(
            "/api/v1/expenses",
            headers=auth_headers,
            json={"amount": 50, "category": "Food"},
        )
        assert mock_http_client.stream.called
        call_kwargs = mock_http_client.stream.call_args.kwargs
        assert call_kwargs.get("content") is not None

    def test_query_params_forwarded(self, client, mock_http_client, auth_headers):
        client.get("/api/v1/notifications?page=2&limit=10", headers=auth_headers)
        call_kwargs = mock_http_client.stream.call_args.kwargs
        url = call_kwargs.get("url", "")
        assert "page=2" in url

    def test_authorization_header_forwarded_downstream(self, client, mock_http_client, auth_headers):
        client.get("/api/v1/users/me", headers=auth_headers)
        call_kwargs = mock_http_client.stream.call_args.kwargs
        forwarded_headers = call_kwargs.get("headers", {})
        assert "authorization" in {k.lower() for k in forwarded_headers}
