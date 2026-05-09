"""Intercept requests to regulatory domains whose backing tables are empty.

For multi-framework routers (MiCA, DORA, MiFID, PSD2, MAR, PRIIPs, CSRD,
SFDR, PBC, fraud, XBRL, AIFMD/UCITS) the DB may have the schema but no data.
Returning `[]` from the underlying router would mislead legal/compliance
consumers into concluding "no applicable regulation". This middleware
short-circuits those paths with an explicit not_available envelope.

Scoped narrowly: only list-style GET paths that are known to be data-less
in this deployment. One DB count per (table, time_window) amortised by a
short TTL cache to avoid latency regression.

To add a new mapping: append to `DOMAIN_PATH_TABLE_MAP` below. Keys are
path prefixes (matched with startswith); values are (table_name, label).
"""

from __future__ import annotations

import logging
import time

from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Path-prefix → (table, domain_label) — narrow to known empty regulatory domains.
# Detail-style endpoints (/{id}) are intentionally NOT included: they should
# return 404, not a bulk not-available envelope.
DOMAIN_PATH_TABLE_MAP: list[tuple[str, str, str]] = [
    ("/v1/mica/casp", "casp", "MiCA"),
    ("/v1/mica/crypto-assets", "crypto_asset", "MiCA"),
    ("/v1/mica/tokenized-assets", "tokenized_asset", "MiCA"),
    ("/v1/mica/wallet-custodians", "wallet_custodian", "MiCA"),
    ("/v1/mica/transactions", "crypto_transaction", "MiCA"),
    ("/v1/dora/ict-risk-registers", "dora_ict_risk_register", "DORA"),
    ("/v1/dora/incident-classification-frameworks", "dora_incident_classification_framework", "DORA"),
    ("/v1/dora/penetration-tests", "dora_penetration_test", "DORA"),
    ("/v1/dora/third-party-providers", "dora_third_party_provider", "DORA"),
    ("/v1/dora/tic-incidents", "dora_tic_incident", "DORA"),
    ("/v1/mifid/best-execution-records", "mifid_best_execution_record", "MiFID II"),
    ("/v1/mifid/client-categories", "mifid_client_category", "MiFID II"),
    ("/v1/mifid/compensation-policies", "mifid_compensation_policy", "MiFID II"),
    ("/v1/mifid/conflict-of-interest", "mifid_conflict_of_interest", "MiFID II"),
    ("/v1/mifid/insider-lists", "mifid_insider_list", "MiFID II"),
    ("/v1/mifid/order-records", "mifid_order_record", "MiFID II"),
    ("/v1/mifid/product-governance", "mifid_product_governance", "MiFID II"),
    ("/v1/mifid/suitability-reports", "mifid_suitability_report", "MiFID II"),
    ("/v1/psd2/aisp", "psd2_aisp", "PSD2"),
    ("/v1/psd2/aspsp", "psd2_aspsp", "PSD2"),
    ("/v1/psd2/consent", "psd2_consent", "PSD2"),
    ("/v1/psd2/incidents", "psd2_incident", "PSD2"),
    ("/v1/psd2/pisp", "psd2_pisp", "PSD2"),
    ("/v1/psd2/sepa-rules", "sepa_payment_rule", "PSD2"),
    ("/v1/mar/insider-communications", "mar_insider_communication", "MAR"),
    ("/v1/mar/insider-transactions", "mar_insider_transaction", "MAR"),
    ("/v1/mar/manipulation-indicators", "mar_manipulation_indicator", "MAR"),
    ("/v1/mar/suspicious-reports", "mar_suspicious_report", "MAR"),
    ("/v1/priips/client-protections", "priips_client_protection", "PRIIPs"),
    ("/v1/priips/kids", "priips_kid", "PRIIPs"),
    ("/v1/priips/products", "priips_product", "PRIIPs"),
    ("/v1/priips/voice-procedures", "priips_voice_procedure", "PRIIPs"),
    ("/v1/csrd/double-materiality", "csrd_double_materiality", "CSRD"),
    ("/v1/csrd/entity-reports", "csrd_entity_report", "CSRD"),
    ("/v1/csrd/esg-data-points", "csrd_esg_data_point", "CSRD"),
    ("/v1/csrd/ess", "csrd_ess", "CSRD"),
    ("/v1/sfdr/annual-reports", "sfdr_annual_report", "SFDR"),
    ("/v1/sfdr/entity-paci", "sfdr_entity_paci", "SFDR"),
    ("/v1/sfdr/pacai-indicators", "sfdr_pacai_indicator", "SFDR"),
    ("/v1/sfdr/pre-contractual", "sfdr_pre_contractual", "SFDR"),
    ("/v1/sfdr/products", "sfdr_product", "SFDR"),
    ("/v1/pbc/beneficial-owners", "beneficial_owner_record", "PBC/AML"),
    ("/v1/pbc/internal-controls", "pbc_internal_control", "PBC/AML"),
    ("/v1/pbc/obligated-subjects", "pbc_obligated_subject", "PBC/AML"),
    ("/v1/pbc/suspicious-reports", "pbc_suspicious_report", "PBC/AML"),
    ("/v1/fraud/incidents", "fraud_incident", "Fraud prevention"),
    ("/v1/fraud/programs", "fraud_program", "Fraud prevention"),
    ("/v1/fraud/risk-assessments", "fraud_risk_assessment", "Fraud prevention"),
]

_CACHE: dict[str, tuple[float, bool]] = {}
_CACHE_TTL_SECONDS = 60.0


def _lookup(path: str) -> tuple[str, str] | None:
    for prefix, table, label in DOMAIN_PATH_TABLE_MAP:
        if path == prefix or path.startswith(prefix + "?"):
            return table, label
    return None


def _is_empty(engine, table: str) -> bool:
    now = time.monotonic()
    cached = _CACHE.get(table)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    try:
        with engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        empty = total == 0
    except Exception as exc:
        logger.debug("domain_availability count failed for %s: %s", table, exc)
        empty = True
    _CACHE[table] = (now, empty)
    return empty


class DomainAvailabilityMiddleware(BaseHTTPMiddleware):
    """Short-circuit GET requests to known empty regulatory-domain listings.

    Requires the ASGI app to expose the SQLAlchemy engine via `app.state.engine`.
    Falls through silently if the engine is not configured.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "GET":
            return await call_next(request)
        mapping = _lookup(request.url.path)
        if mapping is None:
            return await call_next(request)
        table, label = mapping
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            return await call_next(request)
        if not _is_empty(engine, table):
            return await call_next(request)
        return JSONResponse(
            status_code=200,
            content={
                "status": "not_available",
                "reason": "source_not_yet_ingested",
                "domain": label,
                "table": table,
                "message": (
                    f"Datos de {label} no disponibles. Fuente pendiente de ingesta "
                    "oficial. Endpoint registrado pero tabla backing vacía."
                ),
                "items": [],
                "total": 0,
            },
        )


def invalidate_cache() -> None:
    """Clear the TTL cache (e.g. after a worker finishes ingesting a domain)."""
    _CACHE.clear()
