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

DOCUMENTO_VOCAB_FIELDS = frozenset(
    {
        "tipo_documento",
        "organismo_emisor",
        "jurisdiccion",
        "tipo_fuente",
        "ambito",
        "estado_vigencia",
    }
)

# Workers may produce values not yet in the controlled vocabulary.
# These mappings translate heuristic values to the closest vocabulary entry.
#
# Key: value the worker actually produces
# Value: vocabulary fallback to use instead
WORKER_FALLBACKS: dict[str, dict[str, str]] = {
    # CENDOJ organism fallbacks
    "organismo_emisor": {
        "TSJ": "Tribunal Supremo",  # TSJ is not in vocab, map to closest
        "Banco de España": "Banco de Espana",
    },
    "tipo_documento": {
        "resolucion_cnmv": "documento_cnmv",
        "codigo_conducta_cnmv": "documento_cnmv",
        "codigo_autoregulacion_cnmv": "documento_cnmv",
        "informe_anual_cnmv": "documento_cnmv",
        "informe_cnmv": "documento_cnmv",
        "instruccion_tecnica_cnmv": "documento_cnmv",
        "dictamen_cnmv": "documento_cnmv",
        "modelo_comunicacion_cnmv": "documento_cnmv",
        "decision_supervision_cnmv": "documento_cnmv",
        "estadistica_mercado_cnmv": "documento_cnmv",
        "reglamento_cnmv": "documento_cnmv",
        "circ_asesoramiento_cnmv": "circular_cnmv",
    },
    "ambito": {
        "general_cnmv": "mercados",
        "mercados_cnmv": "mercados",
        "reporting_regulatorio_cnmv": "reporting_regulatorio",
        "reporting_financiero_cnmv": "reporting_financiero",
        "infraestructuras_cnmv": "infraestructuras_mercado",
        "gobierno_corporativo": "mercados",
        "proteccion_inversor_cnmv": "mercados",
        "sanciones_cnmv": "mercados",
        "pgc_cnmv": "reporting_financiero",
        "transparencia_emisores": "disclosure_ue",
        "mifid_ii": "mercados_financieros_ue",
        "mifir": "mercados_financieros_ue",
        "mar": "abuso_mercado_ue",
        "dora": "resiliencia_digital_ue",
        "priips": "mercados_financieros_ue",
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
        if validate_field(field, new_value):
            logger.warning(
                "Worker fallback: %s=%r -> %r", field, value, new_value
            )
            return new_value

    if fallback is not None and validate_field(field, fallback):
        logger.warning("Explicit fallback: %s=%r -> %r", field, value, fallback)
        return fallback

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
    field_fallbacks: dict[str, str] | None = None,
) -> dict:
    """Sanitize a worker payload dict against the controlled vocabulary.

    Returns a new dict with invalid values replaced by vocabulary-compatible
    values (using fallbacks where available, or keeping the original as last
    resort).
    """
    fields = (
        frozenset(VOCABULARY.keys())
        if vocabulary_fields is None
        else vocabulary_fields
    )
    fallback_values = field_fallbacks or {}
    sanitized = dict(payload)
    for field in fields:
        if field in sanitized and isinstance(sanitized[field], str):
            sanitized[field] = safe_payload_value(
                field,
                sanitized[field],
                fallback=fallback_values.get(field),
            )
    return sanitized


def sanitize_documento_payload(
    payload: dict,
    field_fallbacks: dict[str, str] | None = None,
) -> dict:
    """Sanitize documento_interpretativo vocabulary fields only."""
    return sanitize_payload(payload, DOCUMENTO_VOCAB_FIELDS, field_fallbacks)
