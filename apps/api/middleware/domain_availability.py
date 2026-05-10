"""Short-circuit empty regulatory list endpoints with explicit availability.

Some domain routers expose valid schemas before their backing tables have real
official or workflow rows. Returning a bare empty list would be unsafe for
legal/compliance consumers. This middleware only intercepts known list-style
GET paths when their table is empty and returns the shared Ralph availability
contract: `workflow_empty`, `allowed_empty`, or `configured_but_unavailable`.
"""

from __future__ import annotations

import time

from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from services.domain_availability import availability_envelope

# Path-prefix -> (table, domain_label, legacy_category)
# legacy_category is kept to preserve the original map shape; the response
# status now comes from the Ralph table registry.
DOMAIN_PATH_TABLE_MAP: list[tuple[str, str, str, str]] = [
    ("/v1/mica/casp", "casp", "MiCA", "public"),
    ("/v1/mica/crypto-assets", "crypto_asset", "MiCA", "public"),
    ("/v1/mica/tokenized-assets", "tokenized_asset", "MiCA", "public"),
    ("/v1/mica/wallet-custodians", "wallet_custodian", "MiCA", "operational"),
    ("/v1/mica/transactions", "crypto_transaction", "MiCA", "operational"),
    ("/v1/dora/ict-risk-registers", "dora_ict_risk_register", "DORA", "operational"),
    ("/v1/dora/incident-classification-frameworks", "dora_incident_classification_framework", "DORA", "operational"),
    ("/v1/dora/penetration-tests", "dora_penetration_test", "DORA", "operational"),
    ("/v1/dora/third-party-providers", "dora_third_party_provider", "DORA", "operational"),
    ("/v1/dora/tic-incidents", "dora_tic_incident", "DORA", "operational"),
    ("/v1/mifid/best-execution-records", "mifid_best_execution_record", "MiFID II", "operational"),
    ("/v1/mifid/client-categories", "mifid_client_category", "MiFID II", "operational"),
    ("/v1/mifid/compensation-policies", "mifid_compensation_policy", "MiFID II", "operational"),
    ("/v1/mifid/conflict-of-interest", "mifid_conflict_of_interest_registry", "MiFID II", "operational"),
    ("/v1/mifid/insider-lists", "mifid_insider_list", "MiFID II", "operational"),
    ("/v1/mifid/order-records", "mifid_order_record", "MiFID II", "operational"),
    ("/v1/mifid/product-governance", "mifid_product_governance", "MiFID II", "operational"),
    ("/v1/mifid/suitability-reports", "mifid_suitability_report", "MiFID II", "operational"),
    ("/v1/psd2/aisp", "psd2_aisp", "PSD2", "public"),
    ("/v1/psd2/aspsp", "psd2_aspsp", "PSD2", "public"),
    ("/v1/psd2/pisp", "psd2_pisp", "PSD2", "public"),
    ("/v1/psd2/consent", "psd2_consent", "PSD2", "operational"),
    ("/v1/psd2/incidents", "psd2_incident_report", "PSD2", "operational"),
    ("/v1/psd2/sepa-rules", "sepa_payment_rule", "PSD2", "public"),
    ("/v1/irs-fiscal/giin", "giin_registry", "IRS FATCA/GIIN", "public"),
    ("/v1/mar/insider-communications", "mar_insider_communication", "MAR", "operational"),
    ("/v1/mar/insider-transactions", "mar_insider_transaction", "MAR", "operational"),
    ("/v1/mar/manipulation-indicators", "mar_market_manipulation_indicator", "MAR", "operational"),
    ("/v1/mar/suspicious-reports", "mar_suspicious_transaction_report", "MAR", "operational"),
    ("/v1/priips/client-protections", "livmc_client_protection", "PRIIPs", "operational"),
    ("/v1/priips/kids", "priips_kid", "PRIIPs", "operational"),
    ("/v1/priips/products", "priips_product", "PRIIPs", "operational"),
    ("/v1/priips/voice-procedures", "livmc_voice_procedure", "PRIIPs", "operational"),
    ("/v1/csrd/double-materiality", "csrd_double_materiality", "CSRD", "operational"),
    ("/v1/csrd/entity-reports", "csrd_entity_report", "CSRD", "operational"),
    ("/v1/csrd/esg-data-points", "csrd_esg_data_point", "CSRD", "operational"),
    ("/v1/csrd/ess", "csrd_ess", "CSRD", "operational"),
    ("/v1/sfdr/annual-reports", "sfdr_annual_report", "SFDR", "operational"),
    ("/v1/sfdr/entity-paci", "sfdr_entity_paci", "SFDR", "operational"),
    ("/v1/sfdr/pacai-indicators", "sfdr_pacai_indicator", "SFDR", "public"),
    ("/v1/sfdr/pre-contractual", "sfdr_pre_contractual", "SFDR", "operational"),
    ("/v1/sfdr/products", "sfdr_product", "SFDR", "operational"),
    ("/v1/pbc/beneficial-owners", "beneficial_owner_record", "PBC/AML", "public"),
    ("/v1/pbc/internal-controls", "pbc_internal_control", "PBC/AML", "operational"),
    ("/v1/pbc/obligated-subjects", "pbc_obligated_subject", "PBC/AML", "operational"),
    ("/v1/pbc/suspicious-reports", "pbc_suspicious_report", "PBC/AML", "operational"),
    ("/v1/fraud/incidents", "fraud_incident", "Fraud prevention", "operational"),
    ("/v1/fraud/programs", "fraud_prevention_program", "Fraud prevention", "operational"),
    ("/v1/fraud/risk-assessments", "fraud_risk_assessment", "Fraud prevention", "operational"),
]

_CACHE: dict[str, tuple[float, bool]] = {}
_CACHE_TTL_SECONDS = 60.0


def _lookup(path: str) -> tuple[str, str, str] | None:
    for prefix, table, label, category in DOMAIN_PATH_TABLE_MAP:
        if path == prefix:
            return table, label, category
    return None


def _is_empty(engine, table: str) -> bool:
    now = time.monotonic()
    cached = _CACHE.get(table)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    try:
        with engine.connect() as conn:
            total = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
        empty = total == 0
    except Exception:
        empty = True
    _CACHE[table] = (now, empty)
    return empty


class DomainAvailabilityMiddleware(BaseHTTPMiddleware):
    """Short-circuit GET requests to known empty regulatory-domain listings."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "GET":
            return await call_next(request)
        mapping = _lookup(request.url.path)
        if mapping is None:
            return await call_next(request)
        table, label, _category = mapping
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            return await call_next(request)
        if not _is_empty(engine, table):
            return await call_next(request)
        return JSONResponse(status_code=200, content=availability_envelope(engine, table, label))


def invalidate_cache() -> None:
    """Clear the TTL cache after a worker ingests data for a domain."""
    _CACHE.clear()
