#!/usr/bin/env python
"""Source freshness snapshot for all domains.

Fase 47 — Consolidacion: dashboard de frescura de datos.

Usage:
    python source_freshness_snapshot.py
    python source_freshness_snapshot.py --json
"""

import json
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'workers'))
from runtime import get_database_url
from sqlalchemy import create_engine, text

TABLES = {
    # AML/Screening
    "screening_entries": "Screening (OFAC/EU/UN)",
    "screening_lists": "Screening Lists",
    "screening_matches": "Screening Matches",
    "sepblac_match": "SEPBLAC",
    "fraud_incident": "Antifraud Incidents",
    "fraud_prevention_program": "Antifraud Programs",
    "fraud_risk_assessment": "Antifraud Risk",
    # Tax
    "giin_registry": "IRS GIIN",
    "irs_modelo": "IRS Tax Models",
    "irs_w8_form": "IRS W8 Forms",
    "irs_withholding_rule": "IRS Withholding",
    "irs_dta_convention": "IRS DTA Treaties",
    "aeat_modelo": "AEAT Models",
    "irnr_instruccion": "IRNR Instructions",
    "irnr_withholding_rate": "IRNR Rates",
    # Regulatory
    "norma": "EUR-Lex/BOE Norms",
    "borme_parse": "BORME",
    "cendoj_doctrina": "CENDOJ",
    "teac_resolution": "TEAC",
    "dgt_doctrina": "DGT Doctrine",
    "bdns_match": "BDNS",
    "eaet_match": "EAET",
    "parques_eolicos": "Parques Eolicos",
    "marcas_match": "Marcas",
    "patentes_match": "Patentes",
    "cnmv_obligation_link": "CNMV Obligations",
    "cnmv_regulation_link": "CNMV Regulations",
    "obligacion_regulatoria": "Regulatory Obligations",
    "micro_obligacion": "Micro Obligations",
    # PGC
    "pgc_cuenta": "BOE PGC Accounts",
    "pgc_marco": "BOE PGC Marco",
    # DAC8
    "dac_reporting_entity": "DAC8 Entities",
    "dac_crypto_report": "DAC8 Crypto",
    "dac_wallet_holder": "DAC8 Wallet Holders",
    # Consumer Credit
    "consumer_credit_disclosure": "Consumer Credit",
    "consumer_credit_contract": "Consumer Credit Contracts",
    "consumer_credit_overindebtedness": "Consumer Credit Overindebtedness",
    # IDD/Solvency
    "idd_distributor": "IDD Distributors",
    "idd_product_uci": "IDD Products",
    "solvency_ii_entity": "Solvency II Entities",
    "solvency_ii_sfp": "Solvency II SFP",
    # DORA
    "dora_third_party_provider": "DORA ICT Providers",
    "dora_ict_risk_register": "DORA ICT Risk",
    "dora_penetration_test": "DORA Pen Tests",
    "dora_incident_classification_framework": "DORA Incident Framework",
    "dora_tic_incident": "DORA TIC Incidents",
    # CRD/BRRD/EMIR
    "crd_brrd_emir_entity": "CRD/BRRD/EMIR Entities",
    "crd_capital_position": "CRD Capital",
    "crd_stress_test": "CRD Stress Tests",
    "brrd_bail_in": "BRRD Bail-in",
    "emir_clearing_member": "EMIR Clearing",
    "emir_trade_report": "EMIR Trades",
    # SFDR
    "sfdr_fund": "SFDR Funds",
    "sfdr_product": "SFDR Products",
    "sfdr_pre_contractual": "SFDR Pre-contractual",
    "sfdr_annual_report": "SFDR Annual Reports",
    "sfdr_entity_paci": "SFDR PACI Entities",
    "sfdr_paci_indicator": "SFDR PACI Indicators",
    # CSRD
    "csrd_company": "CSRD Companies",
    "csrd_double_materiality": "CSRD Materiality",
    "csrd_entity_report": "CSRD Reports",
    "csrd_esg_data_point": "CSRD ESG Data",
    "csrd_ess": "CSRD ESS",
    # PBC
    "pbc_entity": "PBC Entities",
    "pbc_internal_control": "PBC Controls",
    "pbc_obligated_subject": "PBC Subjects",
    # AIFMD/UCITS
    "aifmd_fund": "AIFMD Funds",
    "aifmd_liquidity_management": "AIFMD Liquidity",
    "aifmd_regulatory_report": "AIFMD Reports",
    "ucits_fund": "UCITS Funds",
    "ucits_regulatory_report": "UCITS Reports",
    # XBRL
    "xbrl_company": "XBRL Companies",
    "xbrl_fact": "XBRL Facts",
    "xbrl_filing": "XBRL Filings",
    "xbrl_taxonomy": "XBRL Taxonomies",
    # MAR/MiFID
    "mar_insider_transaction": "MAR Insider Transactions",
    "mifid_insider_list": "MiFID Insider Lists",
    "mar_market_manipulation_indicator": "MAR Manipulation",
    "mar_insider_communication": "MAR Communications",
    "mar_suspicious_transaction_report": "MAR Suspicious Reports",
    "mifid_best_execution_record": "MiFID Best Execution",
    "mifid_client_category": "MiFID Client Categories",
    "mifid_compensation_policy": "MiFID Compensation",
    "mifid_conflict_of_interest_registry": "MiFID Conflicts",
    "mifid_order_record": "MiFID Orders",
    "mifid_product_governance": "MiFID Product Governance",
    "mifid_suitability_report": "MiFID Suitability",
    # PRIIPs/Ownership
    "priips_product": "PRIIPs Products",
    "priips_kid": "PRIIPs KIDs",
    "ownership_relation": "Ownership Relations",
    "ownership_share": "Ownership Shares",
    # Beneficial ownership
    "beneficial_owner_record": "Beneficial Owners",
    "ubo_record": "UBO Records",
    # Transparency
    "transparency_issuer": "Transparency Issuers",
    "transparency_regulated_information": "Transparency Info",
    "transparency_voting_rights": "Transparency Voting",
    "transparency_internal_rule": "Transparency Rules",
    # PSD2
    "psd2_aisp": "PSD2 AISP",
    "psd2_aspsp": "PSD2 ASPSP",
    "psd2_pisp": "PSD2 PISP",
    "psd2_consent": "PSD2 Consents",
    "psd2_incident_report": "PSD2 Incidents",
    # Crypto
    "crypto_asset": "Crypto Assets",
    "crypto_transaction": "Crypto Transactions",
    "wallet_custodian": "Crypto Custodians",
    # LIVMC/Transparency
    "livmc_client_protection": "LIVMC Client Protection",
    "livmc_voice_procedure": "LIVMC Voice",
    # CASP
    "casp": "CASP Registry",
    # Entity
    "empresa": "Companies",
    "entity_aliases": "Entity Aliases",
    "entity_identifiers": "Entity Identifiers",
    # Doc
    "documento_interpretativo": "Interpretative Docs",
    "documento_version": "Doc Versions",
    "documento_fragmento": "Doc Fragments",
}


def main() -> None:
    engine = create_engine(get_database_url(), future=True)
    now = datetime.now(UTC)
    results = []

    with engine.begin() as conn:
        for table, label in TABLES.items():
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                col_result = conn.execute(text(f"""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = '{table}'
                    AND column_name IN ('created_at', 'updated_at', 'fecha', 'reporting_date')
                    ORDER BY ordinal_position LIMIT 1
                """))
                date_col = col_result.scalar()
                if date_col:
                    date_result = conn.execute(text(
                        f"SELECT MAX({date_col}) FROM {table}"
                    ))
                    max_date = date_result.scalar()
                    if max_date and hasattr(max_date, 'tzinfo') and max_date.tzinfo:
                        days_ago = (now - max_date).days
                    elif max_date:
                        days_ago = (now - max_date.replace(tzinfo=UTC)).days
                    else:
                        days_ago = None
                else:
                    max_date = None
                    days_ago = None
                results.append({
                    "table": table,
                    "label": label,
                    "count": count,
                    "max_date": max_date.isoformat() if max_date else None,
                    "days_ago": days_ago,
                })
            except Exception:
                results.append({
                    "table": table,
                    "label": label,
                    "count": 0,
                    "max_date": None,
                    "days_ago": None,
                })

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(f"{'Label':<45} {'Count':>6} {'Days Ago':>9}")
        print("-" * 62)
        for r in results:
            days = str(r['days_ago']) if r['days_ago'] is not None else "-"
            print(f"{r['label']:<45} {r['count']:>6} {days:>9}")
        print()
        total_rows = sum(r['count'] for r in results)
        print(f"Total rows: {total_rows}")


if __name__ == "__main__":
    main()
