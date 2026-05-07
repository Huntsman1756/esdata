"""Unit tests for request_logging middleware."""

import asyncio
from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from middleware.request_logging import RequestLoggingMiddleware


class TestRequestLoggingMiddleware:
    """Verify request logging middleware behavior."""

    def test_client_ip_from_forwarded_for(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock()
        request.client.host = "local"
        assert RequestLoggingMiddleware._client_ip(request) == "1.2.3.4"

    def test_client_ip_from_client_host(self):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        assert RequestLoggingMiddleware._client_ip(request) == "192.168.1.1"

    def test_client_ip_unknown_when_no_client(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert RequestLoggingMiddleware._client_ip(request) == "unknown"

    def test_client_ip_trims_forwarded_for(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": " 10.0.0.1 , 10.0.0.2 "}
        request.client = None
        assert RequestLoggingMiddleware._client_ip(request) == "10.0.0.1"

    def test_dispatch_uses_uuid_for_missing_request_id(self):
        middleware = RequestLoggingMiddleware(app=MagicMock())
        request = MagicMock()
        request.url.path = "/v1/cambios"
        request.method = "GET"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.1.1.1"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def next_fn(req):
            return mock_response

        asyncio.run(middleware.dispatch(request, next_fn))
        assert "x-request-id" in mock_response.headers
        assert len(mock_response.headers["x-request-id"]) > 0

    def test_dispatch_preserves_incoming_request_id(self):
        middleware = RequestLoggingMiddleware(app=MagicMock())
        request = MagicMock()
        request.url.path = "/v1/cambios"
        request.method = "GET"
        request.headers = {"x-request-id": "my-id-123"}
        request.client = MagicMock()
        request.client.host = "1.1.1.1"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def next_fn(req):
            return mock_response

        asyncio.run(middleware.dispatch(request, next_fn))
        assert mock_response.headers["x-request-id"] == "my-id-123"

    def test_dispatch_injects_new_request_id_when_missing(self):
        middleware = RequestLoggingMiddleware(app=MagicMock())
        request = MagicMock()
        request.url.path = "/v1/cambios"
        request.method = "GET"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.1.1.1"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def next_fn(req):
            return mock_response

        asyncio.run(middleware.dispatch(request, next_fn))
        rid = mock_response.headers["x-request-id"]
        assert len(rid) == 8
        assert all(c in "0123456789abcdef" for c in rid)  # hex truncated UUID
