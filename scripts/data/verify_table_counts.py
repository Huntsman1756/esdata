#!/usr/bin/env python
"""Verify row counts across all database tables and classify empty ones.

Usage:
    python scripts/data/verify_table_counts.py

Classifies tables into:
  - SEED_HAS_SCRIPT: tiene seed en scripts/data/
  - WORKER_FILLS: se llena automaticamente por workers
  - INFRA_EVAL: infraestructura de evaluacion (auditoria, evals, revision)
  - OUT_OF_SCOPE: corpus sin ingestion automatica, sin seed, sin worker

Requires DB connection. Default: postgresql://esdata:esdata_dev@localhost:5432/esdata
"""

import os
import sys
from collections import defaultdict

from sqlalchemy import create_engine, text

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://esdata:esdata_dev@localhost:5432/esdata",
)

# Tablas que se llenan automaticamente por workers de ingestion
WORKER_FILLED = {
    "chunk",
    "chunk_embedding",
    "document",
    "empresa",
    "articulo",
    "modelo_normativa",
    "norma",
    "modelo_articulo",
    "articulo_materia",
    "documento_articulo",
    "documento_fragmento",
    "documento_interpretativo",
    "documento_seccion",
    "version_articulo",
    "modelo_campana",
    "modelo_campana_operativa",
    "modelo_casilla",
    "modelo_clave",
    "modelo_formato",
    "modelo_instruccion",
    "screening_entries",
    "screening_lists",
    "screening_matches",
    "sync_log",
    "source_freshness_snapshot",
    "source_revision",
}

# Scripts de seed existentes (sin extension)
SEED_SCRIPTS = {
    f.replace("seed_", "").replace(".py", "")
    for f in os.listdir(os.path.join(os.path.dirname(__file__)))
    if f.startswith("seed_") and f.endswith(".py")
}

# Mapeo seed -> tabla (basado en nombres de scripts)
SEED_TO_TABLES = {
    "pgc": {"pgc_cuenta", "pgc_marco", "pgc_norma_valoracion", "pgc_estado_financiero", "pgc_xbrl_mapping"},
    "pgc_cuenta": {"pgc_cuenta"},
    "pgc_cuenta_refs": {"pgc_cuenta"},
    "pgc_marco": {"pgc_marco"},
    "pgc_norma_valoracion": {"pgc_norma_valoracion"},
    "pgc_estado_financiero": {"pgc_estado_financiero"},
    "pgc_xbrl_mapping": {"pgc_xbrl_mapping"},
    "modelo_articulo": {"modelo_articulo"},
    "articulo_materia": {"articulo_materia"},
    "documento_articulo": {"documento_articulo"},
    "documento_cnmv_version": {"documento_cnmv_version"},
    "ownership": {"ownership_relation", "ownership_share", "ubo_record"},
    "entity_identity": {"entity_identifiers", "entity_aliases"},
    "screening": {"screening_entries", "screening_lists", "screening_matches"},
    "screening_worker": {"screening_entries"},
    "data_lineage": {"data_lineage"},
    "source_revision": {"source_revision"},
    "cnmv": {"cnmv_regulation", "cnmv_document", "cnmv_version"},
    "cnmv_regulation_link": {"cnmv_regulation_link"},
    "cnmv_obligation_link": {"cnmv_obligation_link"},
    "irs_modelos": {"irs_modelo"},
    "irs_fiscal": {"irs_fiscal_norma", "irs_fiscal_obligacion"},
    "irs_fiscal_norma": {"irs_fiscal_norma"},
    "irs_dta_convention": {"irs_dta_convention"},
    "irs_tin_reference": {"irs_tin_reference"},
    "irs_withholding_rule": {"irs_withholding_rule"},
    "dac": {"dac_report", "dac_entity"},
    "dac_reporting_entity": {"dac_reporting_entity"},
    "dac_wallet_holder": {"dac_wallet_holder"},
    "dac_crypto_report": {"dac_crypto_report"},
    "crypto_asset": {"crypto_asset"},
    "crypto_transaction": {"crypto_transaction"},
    "fraud_incident": {"fraud_incident"},
    "fraud_prevention_program": {"fraud_prevention_program"},
    "fraud_risk_assessment": {"fraud_risk_assessment"},
    "xbrl": {"xbrl_taxonomy", "xbrl_filing", "xbrl_fact"},
    "xbrl_filing": {"xbrl_filing"},
    "xbrl_fact": {"xbrl_fact"},
    "aeat_models": {"aeat_modelo"},
    "calendario_fiscal": {"calendario_fiscal", "modelo_fiscal_calendar"},
    "fiscal_calendar": {"calendario_fiscal"},
    "fiscal_indicators": {"fiscal_indicators"},
    "modelos": {"modelo_fiscal"},
    "tax_data": {"tax_data"},
    "sfdr": {"sfdr_product", "sfdr_pacai_indicator", "sfdr_entity_paci", "sfdr_pre_contractual", "sfdr_annual_report"},
    "csrd": {"csrd_entity_report", "csrd_esg_data_point", "csrd_ess", "csrd_double_materiality"},
    "aifmd": {"aifmd_fund", "aifmd_regulatory_report", "aifmd_liquidity_management"},
    "ucits": {"ucits_fund", "ucits_regulatory_report"},
    "crd": {"crd_capital_position", "crd_stress_test"},
    "emir": {"emir_trade_report", "emir_clearing_member"},
    "psd2": {"psd2_report"},
    "facta": {"facta_report"},
    "internacional": {"obligacion_internacional"},
    "iva_rates": {"iva_rates"},
    "irpf_brackets": {"irpf_brackets"},
    "ss_rates": {"ss_rates"},
    "irnr_rates": {"irnr_rates"},
    "dgt": {"dgt_doctrina"},
    "boe": {"boe_document"},
    "bde": {"bde_circular"},
    "borme": {"borme_document"},
    "aepd": {"aepd_guidance"},
    "sepblac": {"sepblac_circular"},
    "eurlex": {"eurlex_regulation"},
    "mica": {"mica_regulation"},
    "priips": {"priips_kid"},
    "mar": {"mar_regulation"},
    "dora": {"dora_regulation"},
    "mifid_mar_dora": {"mifid_regulation", "mar_regulation", "dora_regulation"},
    "pbc": {"pbc_internal_control"},
    "w8_forms": {"w8_form"},
    "corporate": {"corporate_entity"},
}


def get_table_counts(engine) -> dict[str, int]:
    """Get row counts for all tables in public schema."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT schemaname || '.' || relname as qualified_name,
                   n_live_tup as approx_count
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY n_live_tup ASC
        """))
        return {row[0]: row[1] for row in result.fetchall()}


def classify_tables(table_counts: dict[str, int]) -> dict[str, list[str]]:
    """Classify tables by their population status."""
    categories = defaultdict(list)

    for table, count in sorted(table_counts.items()):
        table_lower = table.lower()
        is_empty = count == 0

        if not is_empty:
            categories["POPULATED"].append(f"{table} ({count:,} rows)")
            continue

        # Check if there's a seed script for this table
        has_seed = False
        for seed_name, seed_tables in SEED_TO_TABLES.items():
            if table_lower in seed_tables:
                has_seed = True
                break

        if table_lower in WORKER_FILLED:
            categories["WORKER_FILLED (empty — needs ingestion)"].append(table)
        elif has_seed:
            categories["HAS_SEED_SCRIPT (empty — needs running)"].append(table)
        else:
            # Check if it's an infra/eval table
            infra_keywords = {"ai_audit_log", "eval_query", "eval_run", "human_review",
                            "query_audit_log", "ai_config_version", "ai_model_registry"}
            if table_lower in infra_keywords:
                categories["INFRA/EVAL (empty by design)"].append(table)
            else:
                categories["OUT_OF_SCOPE (no seed, no worker)"].append(table)

    return dict(categories)


def main():
    print(f"Connecting to: {DB_URL[:50]}...")
    engine = create_engine(DB_URL)

    try:
        table_counts = get_table_counts(engine)
        print(f"\nFound {len(table_counts)} tables in public schema\n")
        print("=" * 60)

        categories = classify_tables(table_counts)

        for category, tables in sorted(categories.items()):
            print(f"\n[{category}] ({len(tables)} tables)")
            print("-" * 40)
            for t in tables:
                print(f"  - {t}")

        print(f"\n{'=' * 60}")
        print(f"Summary:")
        for category, tables in categories.items():
            print(f"  {category}: {len(tables)}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Make sure PostgreSQL is running and DATABASE_URL is correct.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
