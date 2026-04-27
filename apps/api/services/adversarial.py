"""Adversarial testing and input sanitization for AI Act compliance (Fase 24.7).

Detects prompt injection, sanitizes dangerous input, and validates
that queries stay within the fiscal-regulatory domain.

Pattern-based detection: no LLM dependency to avoid circular calls.
"""

import logging
import re
from enum import Enum

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class InjectionType(str, Enum):
    DIRECT = "direct"
    INDIRECT = "ignore_prev"
    XML_TAG_INJECTION = "xml_injection"
    DELIMITER_BREAK = "delimiter_break"
    DAN = "dan"
    ROLE_PLAY = "role_play"
    LEET_SPEAK = "leet_speak"
    UNICODE_SPOOF = "unicode_spoof"
    CODE_INJECTION = "code_injection"
    SQL_INJECTION = "sql_injection"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    MULTILINGUAL_INJECTION = "multilingual_injection"


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[tuple[re.Pattern, InjectionType]] = [
    (re.compile(r"(?i)ignore\s+all\s+(previous|prior|above)", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)ignore\s+all\s+instructions", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)disregard\s+all", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)you\s+are\s+now\s+(a\s+)?(developer|admin|root|god)", re.MULTILINE), InjectionType.ROLE_PLAY),
    (re.compile(r"(?i)you\s+are\s+now\s+acting\s+as", re.MULTILINE), InjectionType.ROLE_PLAY),
    (re.compile(r"(?i)DAN\s*\(", re.MULTILINE), InjectionType.DAN),
    (re.compile(r"(?i)act\s+as\s+if\s+you\s+are", re.MULTILINE), InjectionType.ROLE_PLAY),
    (re.compile(r"(?i)DAN:\s", re.MULTILINE), InjectionType.DAN),
    (re.compile(r"(?i)begin\s+DAN", re.MULTILINE), InjectionType.DAN),
    (re.compile(r"(?i)previous\s+instructions?\s*(?:were|are|should\s+be)\s*(?:fake|not\s+real|ignore|wrong)", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)ignore\s+(the\s+)?(previous|above|prior|last)\s+(message|prompt|instruction|request|text|conversation)", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)new\s+rule:", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)override\s+your\s+(previous|original|system)", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)you\s+are\s+nolonger\s+a", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)<\s*system\s*>.*?<\s*/\s*system\s*>", re.DOTALL | re.IGNORECASE), InjectionType.XML_TAG_INJECTION),
    (re.compile(r"(?i)```(xml|html|json|yaml|system)\n.*?\n```", re.DOTALL | re.IGNORECASE), InjectionType.XML_TAG_INJECTION),
    (re.compile(r"(?i)system:\s*(?:prompt|instruction|directive)", re.MULTILINE), InjectionType.XML_TAG_INJECTION),
    (re.compile(r"(?i)BEGIN\s+SYSTEM\s*:", re.MULTILINE), InjectionType.XML_TAG_INJECTION),
    (re.compile(r"(?i)END\s+SYSTEM\s*:", re.MULTILINE), InjectionType.XML_TAG_INJECTION),
    (re.compile(r"(?i)TRANSLATE\s+TO\s+(?:SPANISH|ENGLISH|FRENCH|GERMAN):.*(?:ignore|disregard)", re.MULTILINE), InjectionType.MULTILINGUAL_INJECTION),
    (re.compile(r"(?i)EN:\s*(?:ignore|disregard|new\s+rule)", re.MULTILINE), InjectionType.MULTILINGUAL_INJECTION),
    (re.compile(r"(?i)ES:\s*(?:ignorar|ignora|nueva\s+regla)", re.MULTILINE), InjectionType.MULTILINGUAL_INJECTION),
    (re.compile(r"(?i)DEINE\s+ANWEISUNG\s+(?:ALLE|IGNORIERE|NEUE)", re.MULTILINE), InjectionType.MULTILINGUAL_INJECTION),
    (re.compile(r"(?i)FR:\s*(?:ignore|nouvelle\s+regle|ignore\s+les)", re.MULTILINE), InjectionType.MULTILINGUAL_INJECTION),
    (re.compile(r"(?i)begin\s+new\s+conversation", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)start\s+fresh\s+with", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)reset\s+your\s+(context|memory|instructions)", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)above\s+text\s+is\s+(?:your|your\s+own)", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)the\s+above\s+text\s+is\s+(?:a\s+)?(?:test|fake|simulation)", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)show\s+me\s+your\s+(system\s+)?(prompt|instructions|rules|config|settings)", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)reveal\s+your\s+(system\s+)?(prompt|instructions|rules)", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)print\s+your\s+(system\s+)?(prompt|instructions)", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)output\s+your\s+system\s+prompt", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)show\s+prompt", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)what\s+is\s+your\s+system\s+prompt", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)what\s+are\s+your\s+(system\s+)?(instructions|rules|prompts)", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)export\s+your\s+(system\s+)?(prompt|instructions)", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)copiar\s+(mi|tu)\s+(prompt|instruccion|sistema)", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)muéstrame\s+(tu|mi)\s+(prompt|instruccion|sistema)", re.IGNORECASE | re.UNICODE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)mostrame\s+(tu|mi)\s+(prompt|instruccion|sistema)", re.IGNORECASE | re.UNICODE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)show\s+me\s+the\s+(full|complete|original)\s+(prompt|instruction)", re.MULTILINE), InjectionType.SYSTEM_PROMPT_LEAK),
    (re.compile(r"(?i)```(?:python|py|bash|sh|js|javascript|sql|mysql)\n", re.MULTILINE), InjectionType.CODE_INJECTION),
    (re.compile(r"(?i)<code>.*?(?:import|exec|eval|system|os\.|subprocess)", re.DOTALL | re.IGNORECASE), InjectionType.CODE_INJECTION),
    (re.compile(r"(?i)(?:exec|eval|system|popen|compile)\s*\(", re.MULTILINE), InjectionType.CODE_INJECTION),
    (re.compile(r"(?i)(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|UNION)\s+", re.MULTILINE), InjectionType.SQL_INJECTION),
    (re.compile(r"(?i)(?:'|\")\s*(?:OR|AND)\s+(?:1|'1'|\"1\")\s*=\s*(?:1|'1'|\"1\")", re.MULTILINE), InjectionType.SQL_INJECTION),
    (re.compile(r"(?i)(?:--|;)\s*(?:DROP|DELETE|UPDATE|INSERT)", re.MULTILINE), InjectionType.SQL_INJECTION),
    (re.compile(r"(?i)(?:\b(?:chmod|chown|rm\s+-rf|mkfs|dd)\b)", re.MULTILINE), InjectionType.CODE_INJECTION),
    (re.compile(r"(?i)(?:__import__|importlib|getattr\s*\(\s*__builtins__)", re.MULTILINE), InjectionType.CODE_INJECTION),
    (re.compile(r"(?i)```(?:python|py)\n(?:import|exec|eval|os\.|subprocess)", re.DOTALL | re.IGNORECASE), InjectionType.CODE_INJECTION),
    (re.compile(r"(?i)(?:base64|b64decode|decodebase64)\s*\(", re.MULTILINE), InjectionType.CODE_INJECTION),
    (re.compile(r"(?i)\\x[0-9a-fA-F]{2}.*\\x[0-9a-fA-F]{2}", re.MULTILINE), InjectionType.UNICODE_SPOOF),
    (re.compile(r"(?i)(?:\u200b|\u200c|\u200d|\ufeff|\u2060)+", re.UNICODE), InjectionType.UNICODE_SPOOF),
    (re.compile(r"(?i)(?:l33t|l00t|1337|h4x|pwned|n00b)\s*(?:mode|on|activate|bypass)", re.MULTILINE), InjectionType.LEET_SPEAK),
    (re.compile(r"(?i)(?:injection|inject|exploit|bypass|hack|attack|crash|destroy|kill)\s*(?:this|the\s+(?:prompt|system|model))", re.MULTILINE), InjectionType.DIRECT),
    (re.compile(r"(?i)(?:ignore|disregard|override|bypass|skip|remove)\s+(?:the\s+)?(?:prompt|instruction|rule|policy|guideline|constraint)", re.MULTILINE), InjectionType.DIRECT),
]


# ---------------------------------------------------------------------------
# Domain vocabulary for out-of-domain detection
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: set[str] = {
    # Fiscal
    "fiscal", "impuesto", "iva", "ivd", "irpf", "sociedades", "hacienda", "aeap",
    "sri", "sii", "recargo", "equivalencia", "simplificado", "bonificacion",
    "deduccion", "retencion", "base_imponible", "cuota", "tarifa",
    "factura", "facturacion", "tesoreria", "tributo", "tributario",
    "afectado", "obligacion", "declaracion", "autoliquidacion",
    # Mercantil / societario
    "sociedad", "mercantil", "comercial", "sla", "sl", "sa", "saj",
    "registro", "mercantil", "mrc", "dwarf", "pacto", "estatuto",
    "consejo", "administracion", "gerente", "socio", "participacion",
    "capital", "social", "balance", "cuenta", "pqc", "pgc",
    # Valores / mercado
    "valores", "bolsa", "mercado", "trading", "inversion", "portfolio",
    "cnmv", "miFID", "mifid", "trlmv", "ley", "reglamento",
    "emisor", "cotizar", "ipo", "oferta", "publica", "prospecto",
    # Compliance / regulatory
    "compliance", "cumplimiento", "prevencion", "lavado", "aml", "cft",
    "pbc-ft", "pctb", "delito", "sancion", "infraccion", "leve",
    "grave", "muy_grave", "denuncia", "suspicion", "uef", "sepfi",
    # Legal
    "ley", "real_decreto", "rd", "real-decreto", "boe", "borrador",
    "normativa", "regulacion", "reglamento", "directiva", "directive",
    "instruccion", "circular", "resolucion", "orden", "decreto",
    # Contabilidad
    "contabilidad", "contable", "asiento", "partida", "mayor", "pqc",
    "nrv", "norma", "nic", "nif", "pgc", "plan_general_contable",
    # General
    "consulta", "busqueda", "search", "query", "resultado", "chunk",
    "embedding", "semantic", "hybrid", "vector", "legal", "juridico",
    "jurisprudencia", "tribunal", "sentencia", "auto", "recurso",
}


def detect_prompt_injection(text: str) -> dict:
    """Detect if the given text contains prompt injection attempts.

    Uses pattern-based detection (no LLM dependency).

    Args:
        text: The input text to analyze.

    Returns:
        dict with 'injection' (bool), 'types' (list), 'score' (float 0-1),
        and 'matched_patterns' (list).
    """
    if not text or not text.strip():
        return {"injection": False, "types": [], "score": 0.0, "matched_patterns": []}

    types_found: list[InjectionType] = []
    matched_patterns: list[str] = []

    for pattern, injection_type in _INJECTION_PATTERNS:
        if pattern.search(text):
            if injection_type not in types_found:
                types_found.append(injection_type)
            matched_patterns.append(injection_type.value)

    score = min(len(types_found) * 0.25, 1.0)
    # Minimum 1 pattern = at least 0.25 score
    if len(types_found) == 1 and score == 0:
        score = 0.25

    return {
        "injection": len(types_found) > 0,
        "types": [t.value for t in types_found],
        "score": round(score, 4),
        "matched_patterns": matched_patterns,
    }


def sanitize_input(text: str, max_length: int = 4000) -> dict:
    """Sanitize input for AI components.

    Removes or flags dangerous patterns. Conservative: rejects on doubt.

    Args:
        text: The input text to sanitize.
        max_length: Maximum allowed length.

    Returns:
        dict with 'cleaned' (str), 'blocked' (bool),
        'reason' (str or None), 'length_truncated' (bool), 'warnings' (list).
    """
    warnings: list[str] = []
    blocked = False
    reason = None

    if not text:
        return {
            "cleaned": "",
            "blocked": False,
            "reason": None,
            "length_truncated": False,
            "warnings": [],
        }

    # Check length
    length_truncated = False
    if len(text) > max_length:
        warnings.append(f"Input truncated to {max_length} chars (was {len(text)})")
        text = text[:max_length]
        length_truncated = True

    # Strip zero-width characters early (before injection check to avoid spoof bypass)
    has_zero_width = bool(re.search(r"[\u200b\u200c\u200d\ufeff\u2060]", text))
    if has_zero_width:
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u2060]", "", text)
        warnings.append("Removed zero-width characters")

    # Strip raw XML system tags (before injection check to avoid false negatives)
    has_xml = bool(re.search(r"<\s*system\s*>", text, re.IGNORECASE))
    text = re.sub(
        r"<\s*system\s*>.*?<\s*/\s*system\s*>",
        "[SYSTEM INSTRUCTION STRIPPED]",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if has_xml:
        warnings.append("Stripped system tags")

    # Check for injection after stripping XML tags
    injection = detect_prompt_injection(text)
    if injection["injection"] and injection["score"] >= 0.25:
        blocked = True
        reason = f"Prompt injection detected: {', '.join(injection['types'])}"
        return {
            "cleaned": text,
            "blocked": True,
            "reason": reason,
            "length_truncated": length_truncated,
            "warnings": warnings + ["blocked"],
        }

    # Block raw code blocks with system-like content
    code_block_match = re.search(
        r"```(?:python|py|bash|sh|system|xml|html)\n.*?(?:exec|eval|import\s+os|subprocess|os\.system)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if code_block_match:
        blocked = True
        reason = "Dangerous code pattern in code block"
        return {
            "cleaned": text,
            "blocked": True,
            "reason": reason,
            "length_truncated": length_truncated,
            "warnings": warnings + ["blocked"],
        }

    # Strip raw XML system tags
    cleaned = re.sub(
        r"<\s*system\s*>.*?<\s*/\s*system\s*>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Also strip single-line XML system tags
    cleaned = re.sub(
        r"<\s*system\s*>[^<]*<\s*/\s*system\s*>",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Remove zero-width characters
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff\u2060]", "", cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Check if we modified the text and add appropriate warnings
    if cleaned != text:
        has_zero_width = bool(re.search(r"[\u200b\u200c\u200d\ufeff\u2060]", text))
        has_extra_ws = bool(re.search(r"\s{2,}", text))
        has_xml = bool(re.search(r"<\s*system\s*>", text, re.IGNORECASE))
        if has_zero_width:
            warnings.append("Removed zero-width characters")
        if has_extra_ws:
            warnings.append("Normalized whitespace")
        if has_xml:
            warnings.append("Removed system tags")

    return {
        "cleaned": cleaned,
        "blocked": False,
        "reason": None,
        "length_truncated": length_truncated,
        "warnings": warnings,
    }


def is_out_of_domain(query: str) -> dict:
    """Check if a query is outside the fiscal-regulatory domain.

    Args:
        query: The query text to check.

    Returns:
        dict with 'out_of_domain' (bool), 'domain_score' (float 0-1),
        'matched_keywords' (list), and 'reason' (str).
    """
    if not query or not query.strip():
        return {
            "out_of_domain": True,
            "domain_score": 0.0,
            "matched_keywords": [],
            "reason": "Empty query",
        }

    query_lower = query.lower()
    matched = [kw for kw in _DOMAIN_KEYWORDS if kw in query_lower]
    total = len(_DOMAIN_KEYWORDS)

    domain_score = len(matched) / total if total > 0 else 0.0

    # Threshold: if less than 1.5% of domain keywords match, flag as out of domain
    out_of_domain = domain_score < 0.015

    reasons = []
    if out_of_domain:
        reasons.append("No domain keywords found")
    if len(query) < 3:
        reasons.append("Query too short")

    return {
        "out_of_domain": out_of_domain,
        "domain_score": round(domain_score, 4),
        "matched_keywords": matched[:10],
        "reason": "; ".join(reasons) if reasons else "Within domain",
    }


class AdversarialResult(BaseModel):
    """Result of an adversarial test."""

    test_name: str = Field(description="Name of the adversarial test")
    input_text: str = Field(description="Input text used")
    injection_detected: bool = Field(description="Whether injection was detected")
    injection_types: list[str] = Field(default_factory=list, description="Types of injection found")
    injection_score: float = Field(ge=0, le=1, default=0.0, description="Injection confidence score")
    blocked: bool = Field(description="Whether the input was blocked")
    out_of_domain: bool = Field(description="Whether the query is out of domain")
    domain_score: float = Field(ge=0, le=1, default=0.0, description="Domain relevance score")
    passed: bool = Field(description="Whether the test passed (no injection or properly blocked)")


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def run_adversarial_test(test_name: str, input_text: str) -> AdversarialResult:
    """Run a single adversarial test against the input.

    Args:
        test_name: Name of the test for reporting.
        input_text: The adversarial input to test.

    Returns:
        AdversarialResult with detection results.
    """
    injection = detect_prompt_injection(input_text)
    sanitized = sanitize_input(input_text)
    domain = is_out_of_domain(input_text)

    passed = not injection["injection"] or (injection["injection"] and sanitized["blocked"])

    return AdversarialResult(
        test_name=test_name,
        input_text=input_text,
        injection_detected=injection["injection"],
        injection_types=injection["types"],
        injection_score=injection["score"],
        blocked=sanitized["blocked"],
        out_of_domain=domain["out_of_domain"],
        domain_score=domain["domain_score"],
        passed=passed,
    )
