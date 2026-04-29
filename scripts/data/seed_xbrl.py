#!/usr/bin/env python3
"""Seed XBRL — filings, facts y taxonomy ESEF/IFRS espanola.

Crea fixtures de 2 filing XBRL de sociedades de valores espanolas con
datos de balance y cuenta de resultados, mas mapeo a taxonomy ESEF/IFRS.

Uso:
    python scripts/data/seed_xbrl.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"


FILING_DATA = [
    {
        "source_name": "Banco Sabadell S.A. — Annual XBRL 2024",
        "source_path": "esr://cnmv.es/filing/2024/banco-sabadell-annual-xbrl.xml",
        "entity_identifier": "A01234567",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "filing_type": "annual_report",
    },
    {
        "source_name": "Banco Bilbao Vizcaya Argentaria S.A. — Annual XBRL 2024",
        "source_path": "esr://cnmv.es/filing/2024/bbv-a-annual-xbrl.xml",
        "entity_identifier": "A09876543",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "filing_type": "annual_report",
    },
]


FACTS_DATA = {
    "A01234567": [
        {"concept": "esga:TotalAssets", "value_raw": "287456000000", "value_numeric": 287456000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:TotalLiabilities", "value_raw": "265123000000", "value_numeric": 265123000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:TotalEquity", "value_raw": "22333000000", "value_numeric": 22333000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:NetIncome", "value_raw": "1245000000", "value_numeric": 1245000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:OperatingRevenue", "value_raw": "4567000000", "value_numeric": 4567000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:InterestIncome", "value_raw": "8901000000", "value_numeric": 8901000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:InterestExpense", "value_raw": "3456000000", "value_numeric": 3456000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:LoanPortfolio", "value_raw": "178900000000", "value_numeric": 178900000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:CustomerDeposits", "value_raw": "156789000000", "value_numeric": 156789000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:CommonEquityTier1Ratio", "value_raw": "15.2", "value_numeric": 15.20, "unit": "pure", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "2"},
        {"concept": "esga:TotalRiskExposure", "value_raw": "146927000000", "value_numeric": 146927000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
        {"concept": "esga:NonPerformingLoans", "value_raw": "3456000000", "value_numeric": 3456000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A01234567", "decimals": "INF"},
    ],
    "A09876543": [
        {"concept": "esga:TotalAssets", "value_raw": "646789000000", "value_numeric": 646789000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:TotalLiabilities", "value_raw": "595432000000", "value_numeric": 595432000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:TotalEquity", "value_raw": "51357000000", "value_numeric": 51357000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:NetIncome", "value_raw": "4890000000", "value_numeric": 4890000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:OperatingRevenue", "value_raw": "12345000000", "value_numeric": 12345000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:InterestIncome", "value_raw": "21234000000", "value_numeric": 21234000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:InterestExpense", "value_raw": "7890000000", "value_numeric": 7890000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:LoanPortfolio", "value_raw": "389012000000", "value_numeric": 389012000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:CustomerDeposits", "value_raw": "345678000000", "value_numeric": 345678000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:CommonEquityTier1Ratio", "value_raw": "13.8", "value_numeric": 13.80, "unit": "pure", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "2"},
        {"concept": "esga:TotalRiskExposure", "value_raw": "372145000000", "value_numeric": 372145000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:NonPerformingLoans", "value_raw": "5678000000", "value_numeric": 5678000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:OperatingLeaseLiability", "value_raw": "1234000000", "value_numeric": 1234000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
        {"concept": "esga:DerivativeFinancialAssets", "value_raw": "45678000000", "value_numeric": 45678000000.00, "unit": "EUR", "context_ref": "2024-12-31", "period_start": "2024-01-01", "period_end": "2024-12-31", "entity_identifier": "A09876543", "decimals": "INF"},
    ],
}


TAXONOMY_DATA = [
    # ESEF Core — Balance Sheet
    {"concept_qname": "esga:TotalAssets", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Total Assets", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalLiabilities", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Total Liabilities", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalEquity", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Total Equity", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    # ESEF Core — Income Statement
    {"concept_qname": "esga:NetIncome", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Net Income", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:OperatingRevenue", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Operating Revenue", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:InterestIncome", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Interest Income", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:InterestExpense", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Interest Expense", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    # ESEF Core — Banking Metrics
    {"concept_qname": "esga:LoanPortfolio", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Loan Portfolio", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:CustomerDeposits", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Customer Deposits", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:CommonEquityTier1Ratio", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Common Equity Tier 1 Ratio", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:pureItemType", "period_type": "instant", "is_monetary": False, "is_negative_allowed": False},
    {"concept_qname": "esga:TotalRiskExposure", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Total Risk Exposure Amount", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:NonPerformingLoans", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Non-Performing Loans", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:OperatingLeaseLiability", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Operating Lease Liability", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:DerivativeFinancialAssets", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Derivative Financial Assets", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    # IFRS labels (ES)
    {"concept_qname": "esga:TotalAssets", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Activo Total", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalLiabilities", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Pasivo Total", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalEquity", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Patrimonio Neto Total", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:NetIncome", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Resultado Neto", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:OperatingRevenue", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Ingresos Operativos", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:LoanPortfolio", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Cartera de Prstamos", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:CustomerDeposits", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Depósitos de Clientes", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:NonPerformingLoans", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Prstamos Dudosos", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
]


def upsert_filing(cur, filing):
    cur.execute(
        """INSERT INTO xbrl_filing (source_name, source_path, entity_identifier,
           period_start, period_end, filing_type)
           VALUES (%(source_name)s, %(source_path)s, %(entity_identifier)s,
                   %(period_start)s, %(period_end)s, %(filing_type)s)
           ON CONFLICT (source_path) DO UPDATE SET
               entity_identifier = EXCLUDED.entity_identifier,
               period_start = EXCLUDED.period_start,
               period_end = EXCLUDED.period_end,
               filing_type = EXCLUDED.filing_type
           RETURNING id""",
     filing,
    )
    return cur.fetchone()[0]


def upsert_fact(cur, fact):
    cur.execute(
        """INSERT INTO xbrl_fact (filing_id, concept, value_raw, value_numeric,
           unit, context_ref, period_start, period_end, entity_identifier, decimals)
           VALUES (%(filing_id)s, %(concept)s, %(value_raw)s, %(value_numeric)s,
                   %(unit)s, %(context_ref)s, %(period_start)s, %(period_end)s,
                   %(entity_identifier)s, %(decimals)s)
           ON CONFLICT (filing_id, concept, context_ref, value_raw) DO UPDATE SET
               value_numeric = EXCLUDED.value_numeric,
               unit = EXCLUDED.unit""",
        fact,
    )


def upsert_taxonomy(cur, tax):
    cur.execute(
        """INSERT INTO xbrl_taxonomy (concept_qname, namespace, label,
           label_language, label_role, standard, data_type, period_type,
           is_monetary, is_negative_allowed)
           VALUES (%(concept_qname)s, %(namespace)s, %(label)s,
                   %(label_language)s, %(label_role)s, %(standard)s, %(data_type)s,
                   %(period_type)s, %(is_monetary)s, %(is_negative_allowed)s)
           ON CONFLICT (concept_qname, label_language, label_role) DO UPDATE SET
               standard = EXCLUDED.standard,
               data_type = EXCLUDED.data_type,
               period_type = EXCLUDED.period_type,
               is_monetary = EXCLUDED.is_monetary,
               is_negative_allowed = EXCLUDED.is_negative_allowed""",
        tax,
    )


def main():
    parser = argparse.ArgumentParser(description="Seed XBRL data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(FILING_DATA)} filings")
        for f in FILING_DATA:
            print(f"  Filing: {f['source_name']} ({f['entity_identifier']})")
        total_facts = sum(len(v) for v in FACTS_DATA.values())
        print(f"[DRY RUN] Would insert {total_facts} XBRL facts")
        for entity_id, facts in FACTS_DATA.items():
            print(f"  {entity_id}: {len(facts)} facts")
        print(f"[DRY RUN] Would insert {len(TAXONOMY_DATA)} taxonomy entries")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # Insert filings
    filing_ids = []
    for filing in FILING_DATA:
        filing_id = upsert_filing(cur, filing)
        filing_ids.append(filing_id)
        print(f"  Filing: {filing['source_name']} (id={filing_id})")

    # Insert facts
    total_facts = 0
    for filing, entity_id in zip(FILING_DATA, FACTS_DATA.keys()):
        filing_id = upsert_filing(cur, filing)
        for fact in FACTS_DATA[entity_id]:
            fact_with_filing = dict(fact, filing_id=filing_id)
            upsert_fact(cur, fact_with_filing)
            total_facts += 1

    # Insert taxonomy
    total_taxonomy = 0
    for tax in TAXONOMY_DATA:
        upsert_taxonomy(cur, tax)
        total_taxonomy += 1

    conn.commit()
    print(f"OK: {len(FILING_DATA)} filings, {total_facts} facts, {total_taxonomy} taxonomy entries inserted")
    conn.close()


if __name__ == "__main__":
    main()
