"""Intercept requests to regulatory domains whose backing tables are empty.

For multi-framework routers (MiCA, DORA, MiFID, PSD2, MAR, PRIIPs, CSRD,
SFDR, PBC, fraud, XBRL, AIFMD/UCITS) the DB may have the schema but no data.
Returning `[]` from the underlying router would mislead legal/compliance
consumers into concluding "no applicable regulation". This middleware
short-circuits those paths with an explicit signal.

Two response shapes distinguish the nature of the emptiness:

- **status: "not_available"** — backing data is public (registro ESMA, EBA,
  Registro Central Titularidades Reales, etc.) but this deployment has not
  ingested it yet. Consumer should expect data eventually.

- **status: "operational_data"** — backing data is proprietary to each
  obligated entity (MiFID insider lists, DORA ICT risk registers, MAR
  insider transactions, fraud incident reports, PBC suspicious reports).
  No public source exists; the endpoint is a schema for callers to plug
  their own internal data pipeline. Returning "not_available" here would
  be wrong — the MCP will never populate this on its own.

This distinction is critical for the Spanish tax/compliance domain: a
compliance officer must be told the difference between "we have not
scraped the public registry yet" and "this is your internal data, not ours
to provide".

Scoped narrowly: only list-style GET paths are intercepted. One DB count
per (table, time_window) amortised by a short TTL cache.
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

# Path-prefix → (table, domain_label, category)
# category: "public"       -> response status=not_available (ingesta pendiente)
#           "operational"  -> response status=operational_data (propietario)
DOMAIN_PATH_TABLE_MAP: list[tuple[str, str, str, str]] = [
    # --- MiCA: CASP registry is PUBLIC (ESMA); others are operational ---
    ("/v1/mica/casp", "casp", "MiCA", "public"),
    ("/v1/mica/crypto-assets", "crypto_asset", "MiCA", "public"),
    ("/v1/mica/tokenized-assets", "tokenized_asset", "MiCA", "public"),
    ("/v1/mica/wallet-custodians", "wallet_custodian", "MiCA", "operational"),
    ("/v1/mica/transactions", "crypto_transaction", "MiCA", "operational"),
    # --- DORA: all operational (ICT risk = internal) ---
    ("/v1/dora/ict-risk-registers", "dora_ict_risk_register", "DORA", "operational"),
    ("/v1/dora/incident-classification-frameworks", "dora_incident_classification_framework", "DORA", "operational"),
    ("/v1/dora/penetration-tests", "dora_penetration_test", "DORA", "operational"),
    ("/v1/dora/third-party-providers", "dora_third_party_provider", "DORA", "operational"),
    ("/v1/dora/tic-incidents", "dora_tic_incident", "DORA", "operational"),
    # --- MiFID II: all operational (insider lists, order records, etc. are per-entity) ---
    ("/v1/mifid/best-execution-records", "mifid_best_execution_record", "MiFID II", "operational"),
    ("/v1/mifid/client-categories", "mifid_client_category", "MiFID II", "operational"),
    ("/v1/mifid/compensation-policies", "mifid_compensation_policy", "MiFID II", "operational"),
    ("/v1/mifid/conflict-of-interest", "mifid_conflict_of_interest", "MiFID II", "operational"),
    ("/v1/mifid/insider-lists", "mifid_insider_list", "MiFID II", "operational"),
    ("/v1/mifid/order-records", "mifid_order_record", "MiFID II", "operational"),
    ("/v1/mifid/product-governance", "mifid_product_governance", "MiFID II", "operational"),
    ("/v1/mifid/suitability-reports", "mifid_suitability_report", "MiFID II", "operational"),
    # --- PSD2: ASPSP/AISP/PISP registries are PUBLIC (EBA); consent/incidents are operational ---
    ("/v1/psd2/aisp", "psd2_aisp", "PSD2", "public"),
    ("/v1/psd2/aspsp", "psd2_aspsp", "PSD2", "public"),
    ("/v1/psd2/pisp", "psd2_pisp", "PSD2", "public"),
    ("/v1/psd2/consent", "psd2_consent", "PSD2", "operational"),
    ("/v1/psd2/incidents", "psd2_incident", "PSD2", "operational"),
    ("/v1/psd2/sepa-rules", "sepa_payment_rule", "PSD2", "public"),
    # --- MAR: all operational (insider lists/transactions are per-entity) ---
    ("/v1/mar/insider-communications", "mar_insider_communication", "MAR", "operational"),
    ("/v1/mar/insider-transactions", "mar_insider_transaction", "MAR", "operational"),
    ("/v1/mar/manipulation-indicators", "mar_manipulation_indicator", "MAR", "operational"),
    ("/v1/mar/suspicious-reports", "mar_suspicious_report", "MAR", "operational"),
    # --- PRIIPs: KIDs are operational (issued by each entity) ---
    ("/v1/priips/client-protections", "priips_client_protection", "PRIIPs", "operational"),
    ("/v1/priips/kids", "priips_kid", "PRIIPs", "operational"),
    ("/v1/priips/products", "priips_product", "PRIIPs", "operational"),
    ("/v1/priips/voice-procedures", "priips_voice_procedure", "PRIIPs", "operational"),
    # --- CSRD: entity reports are operational; data points mixed ---
    ("/v1/csrd/double-materiality", "csrd_double_materiality", "CSRD", "operational"),
    ("/v1/csrd/entity-reports", "csrd_entity_report", "CSRD", "operational"),
    ("/v1/csrd/esg-data-points", "csrd_esg_data_point", "CSRD", "operational"),
    ("/v1/csrd/ess", "csrd_ess", "CSRD", "operational"),
    # --- SFDR: PACI/PAI indicators can be public (RTS); products are entity disclosures ---
    ("/v1/sfdr/annual-reports", "sfdr_annual_report", "SFDR", "operational"),
    ("/v1/sfdr/entity-paci", "sfdr_entity_paci", "SFDR", "operational"),
    ("/v1/sfdr/pacai-indicators", "sfdr_pacai_indicator", "SFDR", "public"),
    ("/v1/sfdr/pre-contractual", "sfdr_pre_contractual", "SFDR", "operational"),
    ("/v1/sfdr/products", "sfdr_product", "SFDR", "operational"),
    # --- PBC/AML: beneficial_owner is PUBLIC (Registro Central); rest operational ---
    ("/v1/pbc/beneficial-owners", "beneficial_owner_record", "PBC/AML", "public"),
    ("/v1/pbc/internal-controls", "pbc_internal_control", "PBC/AML", "operational"),
    ("/v1/pbc/obligated-subjects", "pbc_obligated_subject", "PBC/AML", "operational"),
    ("/v1/pbc/suspicious-reports", "pbc_suspicious_report", "PBC/AML", "operational"),
    # --- Fraud: all operational (incident/STR reports per-entity) ---
    ("/v1/fraud/incidents", "fraud_incident", "Fraud prevention", "operational"),
    ("/v1/fraud/programs", "fraud_program", "Fraud prevention", "operational"),
    ("/v1/fraud/risk-assessments", "fraud_risk_assessment", "Fraud prevention", "operational"),
]

_CACHE: dict[str, tuple[float, bool]] = {}
_CACHE_TTL_SECONDS = 60.0


def _lookup(path: str) -> tuple[str, str, str] | None:
    for prefix, table, label, category in DOMAIN_PATH_TABLE_MAP:
        if path == prefix or path.startswith(prefix + "?"):
            return table, label, category
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


def _public_envelope(table: str, label: str) -> dict:
    return {
        "status": "not_available",
        "reason": "source_not_yet_ingested",
        "domain": label,
        "table": table,
        "message": (
            f"Datos de {label} no disponibles. Fuente oficial pública pendiente "
            "de ingesta (ESMA/EBA/Registro Central/BOE). Se espera cobertura."
        ),
        "items": [],
        "total": 0,
    }


def _operational_envelope(table: str, label: str) -> dict:
    return {
        "status": "operational_data",
        "reason": "proprietary_to_obligated_entity",
        "domain": label,
        "table": table,
        "message": (
            f"Datos operacionales de {label}. Esta tabla modela información "
            "propietaria del sujeto obligado (listas de iniciados, registros "
            "ICT, informes de operaciones sospechosas, etc.). No procede de "
            "fuente pública; configure su pipeline interno si necesita "
            "persistirla aquí."
        ),
        "items": [],
        "total": 0,
    }


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
        table, label, category = mapping
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            return await call_next(request)
        if not _is_empty(engine, table):
            return await call_next(request)
        if category == "operational":
            return JSONResponse(status_code=200, content=_operational_envelope(table, label))
        return JSONResponse(status_code=200, content=_public_envelope(table, label))


def invalidate_cache() -> None:
    """Clear the TTL cache (e.g. after a worker finishes ingesting a domain)."""
    _CACHE.clear()
