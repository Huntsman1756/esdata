"""AI content labeling and disclaimer service for AI Act compliance.

Adds AI-generated content markers and legal disclaimers to responses
from AI/ML components (semantic search, embeddings, hybrid search).

Aligned with EU AI Act high-risk system transparency requirements.
"""

DISCLAIMER_ES = (
    "AVISO: Esta respuesta fue generada o asistida por un sistema de IA. "
    "No constituye asesoramiento legal, financiero ni fiscal. "
    "Consulte siempre con un profesional cualificado antes de tomar decisiones."
)

DISCLAIMER_EN = (
    "DISCLAIMER: This response was generated or assisted by an AI system. "
    "It does not constitute legal, financial, or tax advice. "
    "Always consult a qualified professional before making decisions."
)

AI_VERSION = "esdata-ai-v1"


def get_ai_disclaimer(language: str = "es") -> str:
    """Return the AI disclaimer text in the requested language.

    Args:
        language: 'es' for Spanish (default), 'en' for English.

    Returns:
        Disclaimer string in the requested language.
    """
    if language.lower() == "en":
        return DISCLAIMER_EN
    return DISCLAIMER_ES


def get_ai_version() -> str:
    """Return the AI component version string for X-Generated-By header."""
    return AI_VERSION


def is_ai_component(headers: dict | None = None, path: str = "") -> bool:
    """Determine if a request/response involves an AI/ML component.

    Checks the request path and optional headers to identify AI-assisted
    endpoints (semantic_search, hybrid_search, consulta with vector mode).

    Args:
        headers: Request headers dict (optional).
        path: Request path to check.

    Returns:
        True if the request involves an AI component.
    """
    ai_paths = [
        "/v1/semantic_search",
        "/v1/hybrid_search",
        "/v1/consulta",
        "/mcp",
    ]
    return bool(
        any(ai_path in path for ai_path in ai_paths)
        or (headers and headers.get("x-ai-request", "").lower() == "true")
    )


def get_ai_headers(path: str = "", headers: dict | None = None) -> dict[str, str]:
    """Return AI labeling headers for AI-component responses.

    Args:
        path: Request path.
        headers: Request headers.

    Returns:
        Dict of headers to add: X-Generated-By and X-AI-Disclaimer.
    """
    if not is_ai_component(headers=headers, path=path):
        return {}

    lang = "es"
    if headers:
        accept_lang = headers.get("accept-language", "")
        if "en" in accept_lang.lower():
            lang = "en"

    disclaimer_text = get_ai_disclaimer(language=lang)

    return {
        "X-Generated-By": AI_VERSION,
        "X-AI-Disclaimer": disclaimer_text,
    }
