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
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

WEBHOOK_SECRET_ENV: Final = "WEBHOOK_SECRET"
WEBHOOK_IDEMPOTENCY_TABLE: Final = "webhook_events"


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

    Creates idempotency tracking table if it does not exist.
    """
    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {WEBHOOK_IDEMPOTENCY_TABLE} (
            event_id    TEXT PRIMARY KEY,
            event_type  TEXT NOT NULL,
            processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))

    result = db.execute(
        text(f"SELECT 1 FROM {WEBHOOK_IDEMPOTENCY_TABLE} WHERE event_id = :eid"),
        {"eid": event_id},
    ).fetchone()

    if result:
        logger.info("Duplicate webhook event rejected: event_id=%s", event_id)
        return True

    return False


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
