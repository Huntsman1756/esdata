"""Tests for human-in-the-loop AI decision review service."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.human_review import (
    ReviewAction,
    ReviewStatus,
    check_review_required,
    create_human_review,
    get_review_store,
    reset_review_store,
    review_ai_decision,
)


@pytest.fixture(autouse=True)
def _clean_store():
    reset_review_store()


class TestCreateReview:
    def test_create_basic_review(self):
        review = create_human_review(
            request_id="req-001",
            decision_type="tax_advice",
        )
        assert review.review_id
        assert review.request_id == "req-001"
        assert review.decision_type == "tax_advice"
        assert review.status == ReviewStatus.PENDING
        assert review.ai_confidence == 0.0
        assert review.reviewer_id is None
        assert review.action is None

    def test_create_review_with_confidence(self):
        review = create_human_review(
            request_id="req-002",
            decision_type="compliance_check",
            ai_confidence=0.35,
            confidence_threshold=0.5,
        )
        assert review.ai_confidence == 0.35
        assert review.confidence_threshold == 0.5
        assert review.status == ReviewStatus.PENDING

    def test_create_review_with_metadata(self):
        meta = {"source": "search", "query": "iva deducciones"}
        review = create_human_review(
            request_id="req-003",
            decision_type="data_retrieval",
            metadata=meta,
        )
        assert review.metadata == meta

    def test_create_review_with_required_for(self):
        review = create_human_review(
            request_id="req-004",
            decision_type="regulatory_filing",
            required_for="cnmv_compliance",
        )
        assert review.required_for == "cnmv_compliance"

    def test_create_multiple_reviews(self):
        r1 = create_human_review("req-001", "type_a")
        r2 = create_human_review("req-002", "type_b")
        assert r1.review_id != r2.review_id


class TestGetPending:
    def test_pending_returns_only_pending(self):
        create_human_review("req-001", "type_a")
        create_human_review("req-002", "type_b")
        review_c = create_human_review("req-003", "type_c")

        review_ai_decision(review_c.review_id, ReviewAction.APPROVE, "user-1")

        store = get_review_store()
        pending = store.get_pending()
        assert len(pending) == 2

    def test_pending_empty(self):
        store = get_review_store()
        assert len(store.get_pending()) == 0


class TestReviewDecision:
    def test_approve(self):
        review = create_human_review("req-001", "tax_advice", ai_confidence=0.4)
        result = review_ai_decision(review.review_id, ReviewAction.APPROVE, "user-1", "Looks correct")
        assert result.status == ReviewStatus.APPROVED
        assert result.action == ReviewAction.APPROVE
        assert result.reviewer_id == "user-1"
        assert result.notes == "Looks correct"
        assert result.reviewed_at is not None

    def test_reject(self):
        review = create_human_review("req-002", "compliance", ai_confidence=0.3)
        result = review_ai_decision(review.review_id, ReviewAction.REJECT, "user-2", "Incorrect data")
        assert result.status == ReviewStatus.REJECTED
        assert result.action == ReviewAction.REJECT

    def test_escalate(self):
        review = create_human_review("req-003", "legal_opinion", ai_confidence=0.2)
        result = review_ai_decision(review.review_id, ReviewAction.ESCALATE, "user-3", "Needs legal review")
        assert result.status == ReviewStatus.ESCALATED
        assert result.action == ReviewAction.ESCALATE

    def test_review_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            review_ai_decision("nonexistent-id", ReviewAction.APPROVE, "user-1")

    def test_review_changes_status_from_pending(self):
        review = create_human_review("req-001", "tax_advice")
        review_ai_decision(review.review_id, ReviewAction.APPROVE, "user-1")
        store = get_review_store()
        assert len(store.get_pending()) == 0
        assert len(store.get_by_status(ReviewStatus.APPROVED)) == 1


class TestCheckReviewRequired:
    def test_low_confidence_requires_review(self):
        result = check_review_required(0.3, 0.5, 0.95)
        assert result["requires_review"] is True
        assert result["reason"] == "low_confidence"
        assert result["confidence"] == 0.3

    def test_high_confidence_no_review(self):
        result = check_review_required(0.8, 0.5, 0.95)
        assert result["requires_review"] is False
        assert result["reason"] == "acceptable_confidence"

    def test_very_high_confidence_auto_approved(self):
        result = check_review_required(0.98, 0.5, 0.95)
        assert result["requires_review"] is False
        assert result["reason"] == "auto_approved"

    def test_zero_threshold_no_review(self):
        result = check_review_required(0.3, 0.0, 0.95)
        assert result["requires_review"] is False

    def test_boundary_confidence(self):
        result = check_review_required(0.5, 0.5, 0.95)
        assert result["requires_review"] is True

    def test_auto_threshold_boundary(self):
        result = check_review_required(0.95, 0.5, 0.95)
        assert result["requires_review"] is False
        assert result["reason"] == "auto_approved"


class TestStoreMethods:
    def test_get_by_id(self):
        review = create_human_review("req-001", "type_a")
        store = get_review_store()
        found = store.get_by_id(review.review_id)
        assert found is review

    def test_get_by_request_id(self):
        create_human_review("req-001", "type_a")
        create_human_review("req-001", "type_b")
        create_human_review("req-002", "type_c")
        store = get_review_store()
        results = store.get_by_request_id("req-001")
        assert len(results) == 2

    def test_count_by_status(self):
        create_human_review("req-001", "type_a")
        create_human_review("req-002", "type_b")
        review_c = create_human_review("req-003", "type_c")
        review_ai = create_human_review("req-004", "type_d")
        review_ai.ai_confidence = 0.99

        review_ai_decision(review_c.review_id, ReviewAction.APPROVE, "user-1")
        review_ai_decision(review_ai.review_id, ReviewAction.REJECT, "user-2")

        store = get_review_store()
        counts = store.count_by_status()
        assert counts.get("pending", 0) == 2
        assert counts.get("approved", 0) == 1
        assert counts.get("rejected", 0) == 1

    def test_get_by_status(self):
        create_human_review("req-001", "type_a")
        review_b = create_human_review("req-002", "type_b")
        review_ai = create_human_review("req-003", "type_c")
        review_ai.ai_confidence = 0.99

        review_ai_decision(review_b.review_id, ReviewAction.APPROVE, "user-1")

        store = get_review_store()
        approved = store.get_by_status(ReviewStatus.APPROVED)
        assert len(approved) == 1

    def test_clear(self):
        create_human_review("req-001", "type_a")
        store = get_review_store()
        store.clear()
        assert len(store.get_pending()) == 0


class TestShouldRequireReview:
    def test_below_threshold(self):
        store = get_review_store()
        assert store.should_require_review(0.3, 0.5) is True

    def test_above_threshold(self):
        store = get_review_store()
        assert store.should_require_review(0.8, 0.5) is False

    def test_zero_threshold(self):
        store = get_review_store()
        assert store.should_require_review(0.3, 0.0) is False


class TestAutoApprove:
    def test_above_auto_threshold(self):
        store = get_review_store()
        assert store.auto_approve_low_risk(0.99, 0.95) is True

    def test_below_auto_threshold(self):
        store = get_review_store()
        assert store.auto_approve_low_risk(0.9, 0.95) is False


class TestReviewEndpoints:
    def test_review_with_notes(self):
        review = create_human_review("req-001", "tax_advice", ai_confidence=0.4)
        result = review_ai_decision(review.review_id, ReviewAction.APPROVE, "auditor-1", "Verified against BOE")
        assert result.notes == "Verified against BOE"

    def test_review_without_notes(self):
        review = create_human_review("req-002", "data_query")
        result = review_ai_decision(review.review_id, ReviewAction.APPROVE, "auditor-2")
        assert result.notes is None

    def test_review_preserves_original_metadata(self):
        meta = {"endpoint": "/v1/search", "query": "iva"}
        review = create_human_review("req-001", "search", metadata=meta)
        review_ai_decision(review.review_id, ReviewAction.APPROVE, "user-1")
        store = get_review_store()
        found = store.get_by_id(review.review_id)
        assert found.metadata == meta


class TestDurablePersistence:
    def test_review_survives_new_store_instance(self):
        created = create_human_review(
            "req-durable-hr-001",
            "tax_advice",
            ai_confidence=0.42,
        )

        from services.human_review import HumanReviewStore

        fresh_store = HumanReviewStore()
        found = fresh_store.get_by_id(created.review_id)

        assert found is not None
        assert found.request_id == "req-durable-hr-001"
