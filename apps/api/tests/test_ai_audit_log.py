"""Tests for AI audit log service (Fase 24.2)."""

# ruff: noqa: E402

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services import ai_audit


@pytest.fixture(autouse=True)
def clean_audit_store():
    ai_audit.reset_audit_store()
    yield
    ai_audit.reset_audit_store()


class TestLogAiDecision:
    def test_basic_log(self):
        store = ai_audit.AIAuditLogStore()
        entry = store.log_ai_decision(
            componente="semantic_search",
            accion="query",
            request_id="req-001",
            latencia_ms=42.5,
        )
        assert entry.componente == "semantic_search"
        assert entry.accion == "query"
        assert entry.request_id == "req-001"
        assert entry.latencia_ms == 42.5
        assert entry.timestamp is not None
        assert store.count == 1

    def test_log_with_error(self):
        store = ai_audit.AIAuditLogStore()
        entry = store.log_ai_decision(
            componente="hybrid_search",
            accion="search",
            request_id="req-002",
            error="database timeout",
        )
        assert entry.error == "database timeout"

    def test_log_with_config(self):
        store = ai_audit.AIAuditLogStore()
        entry = store.log_ai_decision(
            componente="embedding",
            accion="embed",
            configuracion={"model": "mpnet", "dim": 768},
        )
        assert entry.configuracion == {"model": "mpnet", "dim": 768}

    def test_append_only_multiple_entries(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(componente="consulta", accion="query", request_id="r1")
        store.log_ai_decision(componente="consulta", accion="query", request_id="r2")
        assert store.count == 2
        assert store.entries[0].request_id == "r1"
        assert store.entries[1].request_id == "r2"

    def test_log_without_optional_fields(self):
        store = ai_audit.AIAuditLogStore()
        entry = store.log_ai_decision(componente="consulta", accion="query")
        assert entry.user_id is None
        assert entry.ip_address is None
        assert entry.error is None
        assert entry.latencia_ms is None


class TestGetEntries:
    def test_get_all_entries(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(componente="semantic_search", accion="query", request_id="r1")
        store.log_ai_decision(componente="hybrid_search", accion="search", request_id="r2")
        all_entries = store.get_entries()
        assert len(all_entries) == 2

    def test_filter_by_component(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(componente="semantic_search", accion="query", request_id="r1")
        store.log_ai_decision(componente="hybrid_search", accion="search", request_id="r2")
        store.log_ai_decision(componente="semantic_search", accion="fuse", request_id="r3")
        filtered = store.get_entries(componente="semantic_search")
        assert len(filtered) == 2
        assert all(e.componente == "semantic_search" for e in filtered)

    def test_filter_by_request_id(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(componente="consulta", accion="query", request_id="req-123")
        store.log_ai_decision(componente="consulta", accion="query", request_id="req-456")
        filtered = store.get_entries(request_id="req-123")
        assert len(filtered) == 1
        assert filtered[0].request_id == "req-123"

    def test_filter_by_date_range(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(
            componente="consulta", accion="query", request_id="r1",
            timestamp="2026-01-01T00:00:00Z",
        )
        store.log_ai_decision(
            componente="consulta", accion="query", request_id="r2",
            timestamp="2026-06-01T00:00:00Z",
        )
        store.log_ai_decision(
            componente="consulta", accion="query", request_id="r3",
            timestamp="2026-12-01T00:00:00Z",
        )
        filtered = store.get_entries(
            desde="2026-03-01T00:00:00Z",
            hasta="2026-09-01T00:00:00Z",
        )
        assert len(filtered) == 1
        assert filtered[0].request_id == "r2"


class TestGetByRequestId:
    def test_single_match(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(componente="consulta", accion="query", request_id="req-x")
        store.log_ai_decision(componente="hybrid_search", accion="search", request_id="req-y")
        results = store.get_by_request_id("req-x")
        assert len(results) == 1

    def test_no_match(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(componente="consulta", accion="query", request_id="req-a")
        results = store.get_by_request_id("nonexistent")
        assert len(results) == 0


class TestModuleFunctions:
    def test_get_audit_store_returns_singleton(self):
        s1 = ai_audit.get_audit_store()
        s2 = ai_audit.get_audit_store()
        assert s1 is s2

    def test_reset_audit_store(self):
        store = ai_audit.get_audit_store()
        store.log_ai_decision(componente="consulta", accion="query")
        assert store.count > 0
        ai_audit.reset_audit_store()
        new_store = ai_audit.get_audit_store()
        assert new_store.count == 0
        assert new_store is not store


class TestDurablePersistence:
    def test_audit_log_survives_new_store_instance(self):
        store = ai_audit.AIAuditLogStore()
        store.log_ai_decision(
            componente="consulta",
            accion="query",
            request_id="req-durable-001",
            resultado_resumen="persist me",
        )

        new_store = ai_audit.AIAuditLogStore()
        results = new_store.get_by_request_id("req-durable-001")

        assert len(results) == 1
        assert results[0].resultado_resumen == "persist me"
