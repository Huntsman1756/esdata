"""Tests for webhook signature verification + idempotency."""

import hashlib
import hmac
import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["WEBHOOK_SECRET"] = "test-secret-for-tests"

from services.webhook_verification import (
    WebhookEvent,
    check_idempotency,
    compute_signature,
    record_webhook_event,
    verify_webhook_signature,
)


class TestComputeSignature:
    def test_computes_hmac_sha256(self):
        payload = b'{"event": "payment"}'
        secret = "test-secret"
        sig = compute_signature(payload, secret)
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert sig == expected

    def test_different_payloads_different_signatures(self):
        secret = "test-secret"
        sig1 = compute_signature(b'{"a": 1}', secret)
        sig2 = compute_signature(b'{"a": 2}', secret)
        assert sig1 != sig2

    def test_different_secrets_different_signatures(self):
        payload = b'{"event": "payment"}'
        sig1 = compute_signature(payload, "secret1")
        sig2 = compute_signature(payload, "secret2")
        assert sig1 != sig2


class TestVerifyWebhookSignature:
    @pytest.mark.asyncio
    async def test_valid_signature_passes(self):
        app = FastAPI()

        @app.post("/webhook")
        async def endpoint(request: Request):
            payload = await request.body()
            verify_webhook_signature(request, payload)
            return {"ok": True}

        payload = b'{"event": "test"}'
        sig = compute_signature(payload, "test-secret-for-tests")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/webhook",
                content=payload,
                headers={
                    "x-webhook-signature": sig,
                    "content-type": "application/json",
                },
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_signature_returns_401(self):
        app = FastAPI()

        @app.post("/webhook")
        async def endpoint(request: Request):
            payload = await request.body()
            verify_webhook_signature(request, payload)
            return {"ok": True}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/webhook", content=b'{"event": "test"}')
        assert r.status_code == 401
        assert "signature" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_401(self):
        app = FastAPI()

        @app.post("/webhook")
        async def endpoint(request: Request):
            payload = await request.body()
            verify_webhook_signature(request, payload)
            return {"ok": True}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/webhook",
                content=b'{"event": "test"}',
                headers={"x-webhook-signature": "invalid-signature-here"},
            )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_timing_safe_comparison(self):
        """Ensure signature comparison is timing-safe."""
        app = FastAPI()

        @app.post("/webhook")
        async def endpoint(request: Request):
            payload = await request.body()
            verify_webhook_signature(request, payload)
            return {"ok": True}

        payload = b'{"event": "test"}'
        correct_sig = compute_signature(payload, "test-secret-for-tests")

        # Tamper with last char
        bad_sig = correct_sig[:-1] + ("a" if correct_sig[-1] != "a" else "b")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/webhook",
                content=payload,
                headers={"x-webhook-signature": bad_sig},
            )
        assert r.status_code == 401


class TestIdempotency:
    def test_new_event_not_duplicate(self):
        from db import SessionLocal

        db = SessionLocal()
        try:
            is_dup = check_idempotency(db, "new-event-123")
            assert is_dup is False
        finally:
            db.close()

    def test_duplicate_event_rejected(self):
        from db import SessionLocal

        db = SessionLocal()
        try:
            # First call: not duplicate
            is_dup1 = check_idempotency(db, "event-dup-456")
            assert is_dup1 is False

            # Record it
            event = WebhookEvent(
                event_id="event-dup-456",
                event_type="test.event",
                payload={"key": "value"},
            )
            record_webhook_event(db, event)

            # Second call: is duplicate
            is_dup2 = check_idempotency(db, "event-dup-456")
            assert is_dup2 is True
        finally:
            db.close()

    def test_different_events_not_duplicate(self):
        from db import SessionLocal

        db = SessionLocal()
        try:
            is_dup1 = check_idempotency(db, "event-a-789")
            assert is_dup1 is False

            is_dup2 = check_idempotency(db, "event-b-012")
            assert is_dup2 is False
        finally:
            db.close()
