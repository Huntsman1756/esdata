"""Tests for AI risk management framework (Fase 24.1)."""

from apps.api.services import ai_risk


def _fresh():
    ai_risk.reset_risk_framework()
    return ai_risk.get_risk_framework()


class TestSeedData:
    def setup_method(self):
        self.fw = _fresh()

    def test_seed_risks_count(self):
        fw = ai_risk.get_risk_framework()
        assert fw.register_count == 8

    def test_seed_has_critical_risks(self):
        fw = ai_risk.get_risk_framework()
        risks = fw.get_risk_register()
        critical = [r for r in risks if r.severity == "critical"]
        assert len(critical) == 2

    def test_seed_has_all_categories(self):
        fw = ai_risk.get_risk_framework()
        risks = fw.get_risk_register()
        categories = {r.category for r in risks}
        expected = {
            "bias_retrieval",
            "hallucination",
            "data_leakage",
            "prompt_injection",
            "model_degradation",
            "stale_data",
            "geographic_bias",
            "provider_dependency",
        }
        assert categories == expected

    def test_risk_scores_computed(self):
        fw = ai_risk.get_risk_framework()
        risks = fw.get_risk_register()
        for r in risks:
            assert 0 <= r.risk_score <= 1
            assert r.risk_score > 0


class TestAssessRisk:
    def setup_method(self):
        self.fw = _fresh()

    def test_known_category(self):
        assessment = self.fw.assess_risk("hallucination", "test context")
        assert assessment.risk_id == "RISK-002"
        assert assessment.severity == "critical"
        assert assessment.probability == 0.3
        assert assessment.impact == 0.9
        assert assessment.context == "test context"

    def test_unknown_category(self):
        assessment = self.fw.assess_risk("unknown_category_xyz")
        assert assessment.risk_id.startswith("UNKNOWN-")
        assert assessment.severity == "medium"
        assert assessment.probability == 0.5
        assert assessment.impact == 0.5

    def test_assess_with_empty_context(self):
        assessment = self.fw.assess_risk("data_leakage", "")
        assert assessment.risk_id == "RISK-003"
        assert assessment.context == "Data leakage: datos sensibles o PII filtrados en respuestas o logs"

    def test_risk_score_computation(self):
        """Verify risk_score = prob*0.4 + impact*0.6."""
        score = ai_risk._compute_risk_score(0.6, 0.7)
        expected = round(0.6 * 0.4 + 0.7 * 0.6, 4)
        assert score == expected


class TestRiskRegister:
    def setup_method(self):
        self.fw = _fresh()

    def test_get_all_risks(self):
        all_risks = self.fw.get_risk_register()
        assert len(all_risks) == 8

    def test_get_by_status_active(self):
        active = self.fw.get_risk_register(status="active")
        assert len(active) > 0
        assert all(r.status == "active" for r in active)

    def test_get_by_status_closed(self):
        closed = self.fw.get_risk_register(status="closed")
        assert len(closed) == 0

    def test_get_risk_by_id(self):
        risk = self.fw.get_risk_by_id("RISK-001")
        assert risk is not None
        assert risk.risk_id == "RISK-001"
        assert risk.category == "bias_retrieval"

    def test_get_risk_by_id_not_found(self):
        risk = self.fw.get_risk_by_id("NONEXISTENT")
        assert risk is None


class TestUpdateRiskStatus:
    def setup_method(self):
        self.fw = _fresh()

    def test_update_to_mitigated(self):
        result = self.fw.update_risk_status("RISK-001", "mitigated", "equipo seguridad")
        assert result is not None
        assert result.status == "mitigated"
        assert result.responsible == "equipo seguridad"
        assert result.updated_at is not None

    def test_update_nonexistent_risk(self):
        result = self.fw.update_risk_status("NONEXISTENT", "closed")
        assert result is None

    def test_update_preserves_other_fields(self):
        original = self.fw.get_risk_by_id("RISK-001")
        assert original is not None
        orig_category = original.category
        orig_severity = original.severity

        self.fw.update_risk_status("RISK-001", "mitigated")
        updated = self.fw.get_risk_by_id("RISK-001")
        assert updated.category == orig_category
        assert updated.severity == orig_severity
        assert updated.status == "mitigated"


class TestLogRiskEvent:
    def setup_method(self):
        self.fw = _fresh()

    def test_log_basic_event(self):
        event = self.fw.log_risk_event(
            risk_id="RISK-001",
            severity="high",
            description="Sesgo geografico detectado en resultados",
        )
        assert event.event_id.startswith("EVT-")
        assert event.risk_id == "RISK-001"
        assert event.severity == "high"
        assert event.resolved is False
        assert self.fw.event_count > 0

    def test_log_resolved_event(self):
        event = self.fw.log_risk_event(
            risk_id="RISK-002",
            severity="critical",
            description="Hallucinacion detectada",
            resolved=True,
            resolution_notes="Se aplico filtro de evidencia",
        )
        assert event.resolved is True
        assert event.resolution_notes == "Se aplico filtro de evidencia"

    def test_event_updates_risk_status(self):
        risk_before = self.fw.get_risk_by_id("RISK-001")
        assert risk_before.status == "active"

        self.fw.log_risk_event(
            risk_id="RISK-001",
            severity="high",
            description="Test event",
        )

        risk_after = self.fw.get_risk_by_id("RISK-001")
        assert risk_after.status == "monitoring"

    def test_event_count_increases(self):
        initial_count = self.fw.event_count
        self.fw.log_risk_event(
            risk_id="RISK-003",
            severity="medium",
            description="Test",
        )
        assert self.fw.event_count == initial_count + 1


class TestGetRiskEvents:
    def setup_method(self):
        self.fw = _fresh()

    def test_get_all_events(self):
        self.fw.log_risk_event(risk_id="RISK-001", severity="high", description="e1")
        self.fw.log_risk_event(risk_id="RISK-002", severity="critical", description="e2")
        events = self.fw.get_risk_events()
        assert len(events) >= 2

    def test_filter_by_risk_id(self):
        self.fw.log_risk_event(risk_id="RISK-001", severity="high", description="e1")
        self.fw.log_risk_event(risk_id="RISK-002", severity="critical", description="e2")
        filtered = self.fw.get_risk_events(risk_id="RISK-001")
        assert len(filtered) >= 1
        assert all(e.risk_id == "RISK-001" for e in filtered)

    def test_filter_by_resolved(self):
        self.fw.log_risk_event(risk_id="RISK-001", severity="high", description="e1", resolved=False)
        self.fw.log_risk_event(risk_id="RISK-002", severity="critical", description="e2", resolved=True)
        unresolved = self.fw.get_risk_events(resolved=False)
        assert all(not e.resolved for e in unresolved)
        resolved = self.fw.get_risk_events(resolved=True)
        assert all(e.resolved for e in resolved)
