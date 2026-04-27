"""Grounding hard — per-claim citation validation and abstention.

Ensures every factual claim returned by /v1/consulta has at least one
citation whose rerank_score meets the minimum grounding threshold.
Claims that fail this check are marked `grounded: false` and the
response abstains when no claim is grounded.

Rules enforced:
- Rule 15 (AGENTS.md): respuestas factuales con citas exactas por claim
- Rule 15 (AGENTS.md): abstencion cuando falte evidencia suficiente
- Rule 15 (AGENTS.md): chunks recuperados como input no confiable
"""

from __future__ import annotations

import re

GROUNDING_THRESHOLD = 0.4
GROUNDING_REVIEW_THRESHOLD = 0.5

# Patterns commonly found in injected / adversarial chunks that should
# be treated as untrusted regardless of their rerank score.
_CHUNK_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|guidance)"),
    re.compile(r"(?i)disregard\s+all"),
    re.compile(r"(?i)you\s+are\s+now\s+(a\s+)?(developer|admin|root|god)"),
    re.compile(r"(?i)DAN\s*(?:[:\s]|$)"),
    re.compile(r"(?i)<\s*system\s*>.*?<\s*/\s*system\s*>", re.DOTALL),
    re.compile(r"(?i)```(?:python|py|bash|sh|system|xml)\n", re.MULTILINE),
    re.compile(r"(?i)(?:exec|eval|system|popen)\s*\(", re.MULTILINE),
    re.compile(r"(?i)(?:SELECT|DROP|DELETE|UPDATE|INSERT)\s+", re.MULTILINE),
    re.compile(r"(?i)show\s+me\s+your\s+(system\s+)?(prompt|instructions)"),
    re.compile(r"(?i)(?:l33t|l00t|1337|h4x)\s*(?:mode|on|bypass)"),
    re.compile(r"(?i)(?:base64decode|b64decode)\s*\(", re.MULTILINE),
    re.compile(r"(?i)(?:__import__|importlib|getattr\s*\(\s*__builtins__)", re.MULTILINE),
    re.compile(r"(?i)DEINE\s+ANWEISUNG\s+ALLE\s+IGNORIERE"),
    re.compile(r"(?i)(?:ignorar|desconectar|omitir)\s+(todas?\s+)?(las?\s+)?(instrucciones|reglas|directivas)", re.UNICODE),
]


def _is_chunk_clean(chunk_text: str) -> bool:
    """Return True if the chunk text does not match injection patterns."""
    if not chunk_text:
        return True
    return all(not pattern.search(chunk_text) for pattern in _CHUNK_INJECTION_PATTERNS)


def _has_sufficient_evidence(
    citations: list[dict],
    threshold: float = GROUNDING_THRESHOLD,
) -> bool:
    """Return True if at least one citation meets the grounding threshold."""
    for citation in citations:
        score = citation.get("rerank_score", 0.0)
        if score >= threshold:
            return True
    return False


def validate_claim_grounding(
    claim_citations: list[dict],
    query: str,
) -> tuple[list[dict], dict]:
    """Validate grounding for each claim and return enriched citations + summary.

    Args:
        claim_citations: list of {"claim": {...}, "citations": [...]} dicts
            as produced by _build_claim_citations().
        query: the original user query (for audit logging).

    Returns:
        Tuple of (enriched_claim_citations, grounding_summary).
        Each citation dict gets a "grounded" bool field.
        The summary contains counts and the grounding status.
    """
    if not claim_citations:
        summary = {
            "total_claims": 0,
            "grounded_claims": 0,
            "ungrounded_claims": 0,
            "grounding_status": "empty",
            "all_claims_have_evidence": True,
        }
        return [], summary

    enriched: list[dict] = []
    grounded_count = 0
    ungrounded_count = 0
    all_clean = True
    injection_flags: list[dict] = []

    for item in claim_citations:
        claim = item.get("claim", {})
        citations = item.get("citations", [])

        enriched_citations: list[dict] = []
        claim_has_evidence = False

        for citation in citations:
            chunk_text = citation.get("excerpt", "")
            chunk_clean = _is_chunk_clean(chunk_text)
            citation_score = citation.get("rerank_score", 0.0)
            is_grounded = chunk_clean and (citation_score >= GROUNDING_THRESHOLD)

            enriched_citation = dict(citation)
            enriched_citation["grounded"] = is_grounded
            enriched_citation["chunk_clean"] = chunk_clean

            if not chunk_clean:
                all_clean = False
                injection_flags.append({
                    "chunk_id": citation.get("chunk_id"),
                    "source_document": citation.get("source_document"),
                    "reason": "suspicious_pattern",
                })

            if is_grounded:
                claim_has_evidence = True

            enriched_citations.append(enriched_citation)

        if claim_has_evidence:
            grounded_count += 1
        else:
            ungrounded_count += 1

        enriched.append({
            "claim": claim,
            "citations": enriched_citations,
            "grounded": claim_has_evidence,
        })

    total = grounded_count + ungrounded_count
    grounding_summary = {
        "total_claims": total,
        "grounded_claims": grounded_count,
        "ungrounded_claims": ungrounded_count,
        "grounding_status": "full" if grounded_count == total and all_clean else (
            "partial" if grounded_count > 0 else "none"
        ),
        "all_claims_have_evidence": grounded_count == total,
        "all_chunks_clean": all_clean,
        "injection_flags": injection_flags,
        "query": query,
    }

    return enriched, grounding_summary


def apply_claim_level_abstention(
    resultados: list[dict],
    grounding_summary: dict,
    confianza: dict,
) -> tuple[list[dict], dict]:
    """Remove ungrounded claims from results when grounding is insufficient.

    Args:
        resultados: original list of result dicts.
        grounding_summary: output from validate_claim_grounding().
        confianza: confidence dict to update.

    Returns:
        Tuple of (filtered_results, updated_confianza).
    """
    status = grounding_summary.get("grounding_status", "none")

    if status == "full":
        # All claims grounded — keep everything
        return resultados, confianza

    # Filter out results whose claims are not grounded
    grounded_result_ids: set[str] = set()
    for item in grounding_summary.get("_enriched_items", []):
        if item.get("grounded"):
            claim = item.get("claim", {})
            key = f"{claim.get('tipo')}:{claim.get('codigo')}:{claim.get('articulo')}"
            grounded_result_ids.add(key)

    if not grounded_result_ids:
        # No claims are grounded — abstain entirely
        confianza = dict(confianza)
        aviso = grounding_summary.get("aviso") or (
            "evidencia insuficiente para responder con fiabilidad; revise la fuente oficial antes de tomar decisiones"
        )
        confianza["aviso"] = aviso
        return [], confianza

    # Keep only grounded results
    filtered = []
    for r in resultados:
        key = f"{r.get('tipo')}:{r.get('codigo', r.get('referencia', r.get('norma', '')) or '')}:{r.get('articulo', '') or ''}"
        if key in grounded_result_ids:
            filtered.append(r)

    confianza = dict(confianza)
    if grounding_summary.get("ungrounded_claims", 0) > 0:
        confianza["aviso"] = (
            f"algunos resultados no cuentan con evidencia suficiente "
            f"({grounding_summary['ungrounded_claims']} claim{'s' if grounding_summary['ungrounded_claims'] > 1 else ''} sin grounding); "
            "considere revisar la fuente oficial"
        )

    return filtered, confianza
