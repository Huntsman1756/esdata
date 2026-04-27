"""Human review router for AI decision review workflows."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from services.human_review import (
    ReviewAction,
    ReviewStatus,
    check_review_required,
    get_review_store,
    review_ai_decision,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["human-review"])


@router.get("/v1/ai/human-review/pending")
def list_pending_reviews(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    store = get_review_store()
    pending = store.get_pending()
    return pending[offset : offset + limit]


@router.get("/v1/ai/human-review/stats")
def get_review_stats():
    store = get_review_store()
    counts = store.count_by_status()
    pending = store.get_pending()
    return {
        "total": len(store.get_pending()) + len(store.get_by_status(ReviewStatus.APPROVED)) + len(store.get_by_status(ReviewStatus.REJECTED)) + len(store.get_by_status(ReviewStatus.ESCALATED)),
        "by_status": counts,
        "pending_count": len(pending),
    }


@router.get("/v1/ai/human-review/by-status/{status}")
def get_reviews_by_status(
    status: ReviewStatus,
    limit: int = Query(50, ge=1, le=200),
):
    store = get_review_store()
    entries = store.get_by_status(status)
    return entries[:limit]


@router.get("/v1/ai/human-review/by-request/{request_id}")
def get_reviews_by_request(request_id: str):
    store = get_review_store()
    entries = store.get_by_request_id(request_id)
    return entries


@router.get("/v1/ai/human-review/{review_id}")
def get_review(review_id: str):
    store = get_review_store()
    review = store.get_by_id(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    return review


@router.post("/v1/ai/human-review/{review_id}/decide")
def submit_review_decision(
    review_id: str,
    action: ReviewAction,
    reviewer_id: str = Query(..., min_length=1),
    notes: str | None = Query(None, max_length=1000),
):
    try:
        result = review_ai_decision(review_id, action, reviewer_id, notes)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/v1/ai/human-review/check")
def check_if_review_needed(
    ai_confidence: float = Query(..., ge=0.0, le=1.0),
    confidence_threshold: float = Query(0.5, ge=0.0, le=1.0),
    auto_threshold: float = Query(0.95, ge=0.0, le=1.0),
):
    return check_review_required(ai_confidence, confidence_threshold, auto_threshold)
