"""Shared vocabulary validation for workers.

Workers import this module to validate payload fields against the
controlled vocabulary before writing to the database.

Invalid values are logged and replaced with a fallback value
instead of raising — workers must never crash because of an
unknown taxonomy value.
"""

from __future__ import annotations

import logging

from vocabulary import VOCABULARY, validate_field

logger = logging.getLogger(__name__)

# Workers may produce values not yet in the controlled vocabulary.
# These mappings translate heuristic values to the closest vocabulary entry.
#
# Key: value the worker actually produces
# Value: vocabulary fallback to use instead
WORKER_FALLBACKS: dict[str, dict[str, str]] = {
    # CENDOJ organism fallbacks
    "organismo_emisor": {
        "TSJ": "Tribunal Supremo",  # TSJ is not in vocab, map to closest
    },
    # EUR-Lex document type fallbacks
    "tipo_documento": {
        # "directiva" and "directiva_ue" are both in vocab — no fallback needed
        # "reglamento" is in both LEGISLACION and UE groups — no fallback needed
    },
}


def safe_payload_value(
    field: str,
    value: str,
    fallback: str | None = None,
) -> str:
    """Validate a single payload value against the controlled vocabulary.

    If the value is invalid, log a warning and return `fallback` if provided,
    otherwise return the original value (graceful degradation).
    """
    if validate_field(field, value):
        return value

    # Check worker-specific fallbacks
    field_fallbacks = WORKER_FALLBACKS.get(field, {})
    if value in field_fallbacks:
        new_value = field_fallbacks[value]
        logger.warning(
            "Worker fallback: %s=%r -> %r", field, value, new_value
        )
        return new_value

    # No fallback available — log and keep original to avoid data loss
    logger.warning(
        "Vocabulary violation (no fallback): %s=%r. Allowed: %s",
        field,
        value,
        sorted(VOCABULARY.get(field, set())),
    )
    return value


def sanitize_payload(
    payload: dict,
    vocabulary_fields: frozenset[str] | None = None,
) -> dict:
    """Sanitize a worker payload dict against the controlled vocabulary.

    Returns a new dict with invalid values replaced by vocabulary-compatible
    values (using fallbacks where available, or keeping the original as last
    resort).
    """
    fields = vocabulary_fields or frozenset(VOCABULARY.keys())
    sanitized = dict(payload)
    for field in fields:
        if field in sanitized and isinstance(sanitized[field], str):
            sanitized[field] = safe_payload_value(
                field, sanitized[field], fallback=None
            )
    return sanitized
