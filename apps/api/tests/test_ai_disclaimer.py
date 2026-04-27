"""Tests for AI content labeling and disclaimer service (Fase 24.5)."""

from apps.api.services import ai_disclaimer


class TestGetAiDisclaimer:
    def test_default_spanish(self):
        result = ai_disclaimer.get_ai_disclaimer()
        assert "AVISO" in result
        assert "asesoramiento legal" in result
        assert "IA" in result

    def test_explicit_spanish(self):
        result = ai_disclaimer.get_ai_disclaimer("es")
        assert "AVISO" in result
        assert "asesoramiento legal" in result

    def test_english(self):
        result = ai_disclaimer.get_ai_disclaimer("en")
        assert "DISCLAIMER" in result
        assert "legal, financial, or tax advice" in result
        assert "AI system" in result

    def test_english_uppercase(self):
        result = ai_disclaimer.get_ai_disclaimer("EN")
        assert "DISCLAIMER" in result


class TestGetAiVersion:
    def test_returns_version_string(self):
        result = ai_disclaimer.get_ai_version()
        assert result == "esdata-ai-v1"


class TestIsAiComponent:
    def test_semantic_search_path(self):
        assert ai_disclaimer.is_ai_component(path="/v1/semantic_search") is True

    def test_hybrid_search_path(self):
        assert ai_disclaimer.is_ai_component(path="/v1/hybrid_search") is True

    def test_consulta_path(self):
        assert ai_disclaimer.is_ai_component(path="/v1/consulta") is True

    def test_mcp_path(self):
        assert ai_disclaimer.is_ai_component(path="/mcp/chat") is True

    def test_legislacion_path_not_ai(self):
        assert ai_disclaimer.is_ai_component(path="/v1/legislacion/buscar") is False

    def test_obligaciones_path_not_ai(self):
        assert ai_disclaimer.is_ai_component(path="/v1/obligaciones") is False

    def test_x_ai_request_header(self):
        headers = {"x-ai-request": "true"}
        assert ai_disclaimer.is_ai_component(headers=headers, path="/v1/consulta") is True

    def test_headers_not_passed(self):
        assert ai_disclaimer.is_ai_component(path="/v1/consulta") is True


class TestGetAiHeaders:
    def test_returns_headers_for_ai_path(self):
        headers = ai_disclaimer.get_ai_headers(path="/v1/semantic_search")
        assert "X-Generated-By" in headers
        assert "X-AI-Disclaimer" in headers
        assert headers["X-Generated-By"] == "esdata-ai-v1"

    def test_spanish_disclaimer_by_default(self):
        headers = ai_disclaimer.get_ai_headers(path="/v1/consulta")
        assert "AVISO" in headers["X-AI-Disclaimer"]

    def test_english_disclaimer_when_accept_language_en(self):
        headers = ai_disclaimer.get_ai_headers(
            path="/v1/consulta",
            headers={"accept-language": "en-US,en;q=0.9"},
        )
        assert "DISCLAIMER" in headers["X-AI-Disclaimer"]

    def test_no_headers_for_non_ai_path(self):
        headers = ai_disclaimer.get_ai_headers(path="/v1/legislacion/buscar")
        assert len(headers) == 0

    def test_no_headers_for_obligaciones_path(self):
        headers = ai_disclaimer.get_ai_headers(path="/v1/obligaciones")
        assert len(headers) == 0
