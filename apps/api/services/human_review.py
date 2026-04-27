"""Human-in-the-loop AI decision review service backed by durable SQL storage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from db import engine
from pydantic import BaseModel, Field
from services.persistence import (
    dumps_json,
    ensure_governance_tables,
    loads_json,
    rows_to_dicts,
)
from sqlalchemy import text


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    AUTO_APPROVED = "auto_approved"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"


class HumanReviewEntry(BaseModel):
    review_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str
    decision_type: str
    ai_response_id: str | None = None
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_id: str | None = None
    action: ReviewAction | None = None
    notes: str | None = None
    confidence_threshold: float = 0.0
    ai_confidence: float = 0.0
    required_for: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HumanReviewStore:
    def __init__(self) -> None:
        ensure_governance_tables()
        self._cache: dict[str, HumanReviewEntry] = {}

    def _map_entry(self, row: dict) -> HumanReviewEntry:
        cached = self._cache.get(row["review_id"])
        if cached is not None:
            cached.request_id = row["request_id"]
            cached.decision_type = row["decision_type"]
            cached.ai_response_id = row["ai_response_id"]
            cached.status = ReviewStatus(row["status"])
            cached.reviewer_id = row["reviewer_id"]
            cached.action = ReviewAction(row["action"]) if row["action"] else None
            cached.notes = row["notes"]
            cached.confidence_threshold = row["confidence_threshold"]
            cached.ai_confidence = row["ai_confidence"]
            cached.required_for = row["required_for"]
            cached.created_at = datetime.fromisoformat(row["created_at"])
            cached.reviewed_at = datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None
            cached.metadata = loads_json(row["metadata"], {})
            return cached
        return HumanReviewEntry(
            review_id=row["review_id"],
            request_id=row["request_id"],
            decision_type=row["decision_type"],
            ai_response_id=row["ai_response_id"],
            status=ReviewStatus(row["status"]),
            reviewer_id=row["reviewer_id"],
            action=ReviewAction(row["action"]) if row["action"] else None,
            notes=row["notes"],
            confidence_threshold=row["confidence_threshold"],
            ai_confidence=row["ai_confidence"],
            required_for=row["required_for"],
            created_at=datetime.fromisoformat(row["created_at"]),
            reviewed_at=datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None,
            metadata=loads_json(row["metadata"], {}),
        )

    def create_review(
        self,
        request_id: str,
        decision_type: str,
        ai_response_id: str | None = None,
        ai_confidence: float = 0.0,
        confidence_threshold: float = 0.0,
        required_for: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HumanReviewEntry:
        entry = HumanReviewEntry(
            request_id=request_id,
            decision_type=decision_type,
            ai_response_id=ai_response_id,
            ai_confidence=ai_confidence,
            confidence_threshold=confidence_threshold,
            required_for=required_for,
            metadata=metadata or {},
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO human_review
                    (review_id, request_id, decision_type, ai_response_id, status, reviewer_id, action, notes, confidence_threshold, ai_confidence, required_for, created_at, reviewed_at, metadata)
                    VALUES
                    (:review_id, :request_id, :decision_type, :ai_response_id, :status, :reviewer_id, :action, :notes, :confidence_threshold, :ai_confidence, :required_for, :created_at, :reviewed_at, :metadata)
                    """
                ),
                {
                    "review_id": entry.review_id,
                    "request_id": entry.request_id,
                    "decision_type": entry.decision_type,
                    "ai_response_id": entry.ai_response_id,
                    "status": entry.status.value,
                    "reviewer_id": entry.reviewer_id,
                    "action": entry.action.value if entry.action else None,
                    "notes": entry.notes,
                    "confidence_threshold": entry.confidence_threshold,
                    "ai_confidence": entry.ai_confidence,
                    "required_for": entry.required_for,
                    "created_at": entry.created_at.isoformat(),
                    "reviewed_at": None,
                    "metadata": dumps_json(entry.metadata),
                },
            )
        self._cache[entry.review_id] = entry
        return entry

    def _query(self, sql: str, params: dict[str, Any] | None = None) -> list[HumanReviewEntry]:
        with engine.begin() as conn:
            rows = rows_to_dicts(conn.execute(text(sql), params or {}))
        return [self._map_entry(row) for row in rows]

    def get_pending(self) -> list[HumanReviewEntry]:
        return self.get_by_status(ReviewStatus.PENDING)

    def get_by_id(self, review_id: str) -> HumanReviewEntry | None:
        entries = self._query("SELECT * FROM human_review WHERE review_id = :review_id", {"review_id": review_id})
        if entries:
            self._cache[review_id] = entries[0]
            return entries[0]
        return None

    def review_decision(
        self,
        review_id: str,
        action: ReviewAction,
        reviewer_id: str,
        notes: str | None = None,
    ) -> HumanReviewEntry:
        entry = self.get_by_id(review_id)
        if entry is None:
            raise ValueError(f"Review {review_id} not found")
        status = ReviewStatus.APPROVED if action == ReviewAction.APPROVE else (
            ReviewStatus.REJECTED if action == ReviewAction.REJECT else ReviewStatus.ESCALATED
        )
        reviewed_at = datetime.now(UTC).isoformat()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE human_review
                    SET status = :status, action = :action, reviewer_id = :reviewer_id, notes = :notes, reviewed_at = :reviewed_at
                    WHERE review_id = :review_id
                    """
                ),
                {
                    "status": status.value,
                    "action": action.value,
                    "reviewer_id": reviewer_id,
                    "notes": notes,
                    "reviewed_at": reviewed_at,
                    "review_id": review_id,
                },
            )
        return self.get_by_id(review_id)

    def should_require_review(self, ai_confidence: float, confidence_threshold: float) -> bool:
        return ai_confidence <= confidence_threshold and confidence_threshold > 0.0

    def auto_approve_low_risk(self, ai_confidence: float, auto_threshold: float) -> bool:
        return ai_confidence >= auto_threshold

    def get_by_status(self, status: ReviewStatus) -> list[HumanReviewEntry]:
        return self._query("SELECT * FROM human_review WHERE status = :status ORDER BY created_at ASC", {"status": status.value})

    def get_by_request_id(self, request_id: str) -> list[HumanReviewEntry]:
        return self._query("SELECT * FROM human_review WHERE request_id = :request_id ORDER BY created_at ASC", {"request_id": request_id})

    def count_by_status(self) -> dict[str, int]:
        with engine.begin() as conn:
            rows = rows_to_dicts(conn.execute(text("SELECT status, COUNT(*) AS total FROM human_review GROUP BY status")))
        return {row["status"]: row["total"] for row in rows}

    def clear(self) -> None:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM human_review"))
        self._cache.clear()


_store: HumanReviewStore | None = None


def get_review_store() -> HumanReviewStore:
    global _store
    if _store is None:
        _store = HumanReviewStore()
    return _store


def reset_review_store() -> None:
    global _store
    ensure_governance_tables()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM human_review"))
    _store = None


def create_human_review(
    request_id: str,
    decision_type: str,
    ai_response_id: str | None = None,
    ai_confidence: float = 0.0,
    confidence_threshold: float = 0.0,
    required_for: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> HumanReviewEntry:
    store = get_review_store()
    return store.create_review(
        request_id=request_id,
        decision_type=decision_type,
        ai_response_id=ai_response_id,
        ai_confidence=ai_confidence,
        confidence_threshold=confidence_threshold,
        required_for=required_for,
        metadata=metadata,
    )


def review_ai_decision(
    review_id: str,
    action: ReviewAction,
    reviewer_id: str,
    notes: str | None = None,
) -> HumanReviewEntry:
    store = get_review_store()
    return store.review_decision(review_id, action, reviewer_id, notes)


def check_review_required(
    ai_confidence: float,
    confidence_threshold: float = 0.5,
    auto_threshold: float = 0.95,
) -> dict[str, Any]:
    store = get_review_store()
    if store.auto_approve_low_risk(ai_confidence, auto_threshold):
        return {"requires_review": False, "reason": "auto_approved", "confidence": ai_confidence}
    if store.should_require_review(ai_confidence, confidence_threshold):
        return {"requires_review": True, "reason": "low_confidence", "confidence": ai_confidence}
    return {"requires_review": False, "reason": "acceptable_confidence", "confidence": ai_confidence}
