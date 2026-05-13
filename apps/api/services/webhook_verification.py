"""Webhook signature verification (HMAC-SHA256) + idempotency by event.id.

Regla 5 de AGENTS.md: "Verificacion criptografica de firma + idempotencia por event.id"
"""

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import Final

from fastapi import HTTPException, Request, status
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

WEBHOOK_SECRET_ENV: Final = "WEBHOOK_SECRET"
WEBHOOK_IDEMPOTENCY_TABLE: Final = "webhook_events"
WEBHOOK_REQUIRED_COLUMNS: Final = {"event_id", "event_type", "processed_at"}


def _get_webhook_secret() -> str:
    secret = os.environ.get(WEBHOOK_SECRET_ENV, "")
    if not secret:
        raise RuntimeError(f"{WEBHOOK_SECRET_ENV} is required for webhook verification")
    return secret


def compute_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(
    request: Request,
    payload: bytes,
    signature_header: str = "x-webhook-signature",
) -> None:
    """Verify HMAC-SHA256 signature. Raises HTTPException 401 on failure."""
    secret = _get_webhook_secret()
    received_sig = request.headers.get(signature_header, "")
    expected_sig = compute_signature(payload, secret)

    if not received_sig or not hmac.compare_digest(received_sig, expected_sig):
        logger.warning(
            "Webhook signature verification failed: "
            "missing header=%s, length=%d",
            signature_header,
            len(received_sig),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


@dataclass
class WebhookEvent:
    """Parsed webhook event with idempotency key."""

    event_id: str
    event_type: str
    payload: dict


def check_idempotency(db: Session, event_id: str) -> bool:
    """Check if webhook event was already processed.

    Returns True if event is a duplicate (already processed).
    Returns False if event is new (should be processed).

    Requires the Alembic-owned idempotency tracking table to exist.
    """
    _assert_webhook_events_table(db)

    result = db.execute(
        text(f"SELECT 1 FROM {WEBHOOK_IDEMPOTENCY_TABLE} WHERE event_id = :eid"),
        {"eid": event_id},
    ).fetchone()

    if result:
        logger.info("Duplicate webhook event rejected: event_id=%s", event_id)
        return True

    return False


def _assert_webhook_events_table(db: Session) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(WEBHOOK_IDEMPOTENCY_TABLE):
        raise RuntimeError(
            f"Required table missing: {WEBHOOK_IDEMPOTENCY_TABLE}. Run Alembic migrations."
        )
    existing = {column["name"] for column in inspector.get_columns(WEBHOOK_IDEMPOTENCY_TABLE)}
    missing = sorted(WEBHOOK_REQUIRED_COLUMNS - existing)
    if missing:
        raise RuntimeError(
            f"Required columns missing on {WEBHOOK_IDEMPOTENCY_TABLE}: {', '.join(missing)}. "
            "Run Alembic migrations."
        )


def record_webhook_event(db: Session, event: WebhookEvent) -> None:
    """Record webhook event for idempotency tracking."""
    db.execute(
        text(f"""
            INSERT INTO {WEBHOOK_IDEMPOTENCY_TABLE} (event_id, event_type)
            VALUES (:eid, :etype)
        """),
        {"eid": event.event_id, "etype": event.event_type},
    )
    db.commit()
    logger.info("Webhook event recorded: event_id=%s type=%s", event.event_id, event.event_type)
