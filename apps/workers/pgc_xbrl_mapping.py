"""pgc_xbrl_mapping worker — seed IFRS/ESEF -> PGC account crosswalk.

Maps XBRL taxonomy concepts (IFRS/ESEF) to PGC (Plan General Contable)
chart of accounts codes. This is the integration bridge between
Phase 16 (XBRL) and Phase 11 (PGC).

Mapping strategy:
- direct: same-line-item correspondence (Revenue -> 700, Cash -> 572)
- similar: conceptually related but not identical
- derived: requires aggregation/subtraction logic
- expert: professional judgment mapping with no automated basis

Confidence levels:
- high: widely accepted, textbook correspondence
- medium: reasonable but may vary by entity type
- low: tentative, needs expert review

"""

import argparse
import os

from sqlalchemy import create_engine, text

if __package__:
    from .runtime import get_database_url
else:
    from runtime import get_database_url

# ---------------------------------------------------------------------------
# Mapping dataset: IFRS/ESEF XBRL concepts -> PGC account codes
# ---------------------------------------------------------------------------

# Income statement mappings (IFRS 18 / IAS 1 P&L)
PGC_XBRL_MAPPING_INCOME = [
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
        "pgc_account_codigo": "700",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Revenue IFRS -> Ventas de mercaderias PGC 700",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
        "pgc_account_codigo": "70",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Revenue IFRS -> Ventas PGC 70 (grupo)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS18/ProfitLoss",
        "pgc_account_codigo": "6",
        "confidence": "medium",
        "mapping_type": "derived",
        "note": "Profit/Loss IFRS -> Compras y gastos PGC 6 (agrupacion)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS18/ProfitLoss",
        "pgc_account_codigo": "7",
        "confidence": "medium",
        "mapping_type": "derived",
        "note": "Profit/Loss IFRS -> Ventas e ingresos PGC 7 (agrupacion)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS18/OperatingProfit",
        "pgc_account_codigo": "700",
        "confidence": "medium",
        "mapping_type": "derived",
        "note": "Operating profit IFRS -> Ventas 700 menos gastos 600",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/OperatingExpenses",
        "pgc_account_codigo": "600",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Operating expenses IFRS -> Compras mercaderias PGC 600",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/OperatingExpenses",
        "pgc_account_codigo": "62",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Operating expenses IFRS -> Servicios exteriores PGC 62",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/OperatingExpenses",
        "pgc_account_codigo": "621",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Operating expenses IFRS -> Arrendamientos y canones PGC 621",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS18/EarningsPerShare",
        "pgc_account_codigo": "7",
        "confidence": "medium",
        "mapping_type": "derived",
        "note": "EPS IFRS -> derivado de ingresos 7 menos gastos 6",
    },
    {
        "xbrl_concept_qname": "http://xbrl.esma.europa.eu/2025-03-27/esef_cor/StandardType",
        "pgc_account_codigo": "6",
        "confidence": "low",
        "mapping_type": "expert",
        "note": "ESEF StandardType -> marco contable PGC 6 (nota)",
    },
]

# Balance sheet mappings (IFRS / IAS 1)
PGC_XBRL_MAPPING_BALANCE = [
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/Assets",
        "pgc_account_codigo": "1",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Assets IFRS -> Activo no corriente PGC 1 (agrupacion)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/Assets",
        "pgc_account_codigo": "2",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Assets IFRS -> Activo corriente PGC 2 (agrupacion)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/Liabilities",
        "pgc_account_codigo": "3",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Liabilities IFRS -> Patrimonio neto PGC 3 (agrupacion)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/Liabilities",
        "pgc_account_codigo": "4",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Liabilities IFRS -> Pasivo corriente PGC 4 (agrupacion)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/Equity",
        "pgc_account_codigo": "3",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Equity IFRS -> Patrimonio neto PGC 3",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/Equity",
        "pgc_account_codigo": "30",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Equity IFRS -> Capital y reservas PGC 30",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/Equity",
        "pgc_account_codigo": "300",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Equity IFRS -> Capital social PGC 300",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS16/PropertyPlantAndEquipment",
        "pgc_account_codigo": "11",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "PPE IFRS -> Inmovilizado material PGC 11",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS16/PropertyPlantAndEquipment",
        "pgc_account_codigo": "110",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "PPE IFRS -> Terrenos y bienes naturales PGC 110",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS38/IntangibleAssets",
        "pgc_account_codigo": "10",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Intangible assets IFRS -> Inmovilizado intangible PGC 10",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS38/IntangibleAssets",
        "pgc_account_codigo": "100",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Intangible assets IFRS -> Investigacion y desarrollo PGC 100",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS3/Goodwill",
        "pgc_account_codigo": "10",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Goodwill IFRS -> Inmovilizado intangible PGC 10",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS32/CashAndCashEquivalents",
        "pgc_account_codigo": "572",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Cash & equivalents IFRS -> Bancos PGC 572",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS32/CashAndCashEquivalents",
        "pgc_account_codigo": "570",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Cash & equivalents IFRS -> Caja PGC 570",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS32/CashAndCashEquivalents",
        "pgc_account_codigo": "57",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Cash & equivalents IFRS -> Tesoreria PGC 57",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS2/Inventory",
        "pgc_account_codigo": "20",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Inventory IFRS -> Existencias comerciales PGC 20",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS2/Inventory",
        "pgc_account_codigo": "200",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Inventory IFRS -> Mercaderias PGC 200",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/TradeAndOtherReceivables",
        "pgc_account_codigo": "430",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Trade receivables IFRS -> Clientes PGC 430",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/TradeAndOtherReceivables",
        "pgc_account_codigo": "43",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Trade receivables IFRS -> Clientes PGC 43",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/TradeAndOtherPayables",
        "pgc_account_codigo": "400",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Trade payables IFRS -> Proveedores PGC 400",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS1/TradeAndOtherPayables",
        "pgc_account_codigo": "40",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Trade payables IFRS -> Proveedores PGC 40",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS12/TaxesPayable",
        "pgc_account_codigo": "472",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Taxes payable IFRS -> IVA soportado PGC 472",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS12/TaxesPayable",
        "pgc_account_codigo": "477",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Taxes payable IFRS -> IVA repercutido PGC 477",
    },
]

# Cash flow mappings (IFRS 7 / IAS 7)
PGC_XBRL_MAPPING_CASHFLOW = [
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS7/CashAndCashEquivalents",
        "pgc_account_codigo": "572",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Cash flows IFRS -> Bancos PGC 572",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS7/CashFromOperatingActivities",
        "pgc_account_codigo": "57",
        "confidence": "medium",
        "mapping_type": "derived",
        "note": "Cash from operations IFRS -> Tesoreria PGC 57",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS7/CashFromInvestingActivities",
        "pgc_account_codigo": "11",
        "confidence": "medium",
        "mapping_type": "derived",
        "note": "Cash from investing IFRS -> Inmovilizado material PGC 11",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS7/CashFromFinancingActivities",
        "pgc_account_codigo": "30",
        "confidence": "medium",
        "mapping_type": "derived",
        "note": "Cash from financing IFRS -> Capital y reservas PGC 30",
    },
]

# Lease mappings (IFRS 16)
PGC_XBRL_MAPPING_LEASES = [
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS16/LeaseLiabilities",
        "pgc_account_codigo": "4",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Lease liabilities IFRS -> Pasivo corriente PGC 4",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS16/RightOfUseAssets",
        "pgc_account_codigo": "11",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Right-of-use assets IFRS -> Inmovilizado material PGC 11",
    },
    {
        "xbrl_concept_qname": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IFRS16/LeasePayments",
        "pgc_account_codigo": "621",
        "confidence": "high",
        "mapping_type": "direct",
        "note": "Lease payments IFRS -> Arrendamientos y canones PGC 621",
    },
]

# ESEF core mappings
PGC_XBRL_MAPPING_ESEF = [
    {
        "xbrl_concept_qname": "http://xbrl.esma.europa.eu/2025-03-27/esef_cor/ReportingPeriodEndDate",
        "pgc_account_codigo": "7",
        "confidence": "low",
        "mapping_type": "expert",
        "note": "ESEF ReportingPeriodEndDate -> marco contable PGC 7 (nota)",
    },
    {
        "xbrl_concept_qname": "http://xbrl.esma.europa.eu/2025-03-27/esef_cor/StandardType",
        "pgc_account_codigo": "7",
        "confidence": "low",
        "mapping_type": "expert",
        "note": "ESEF StandardType -> marco contable PGC 7 (nota)",
    },
]

ALL_MAPPINGS = (
    PGC_XBRL_MAPPING_INCOME
    + PGC_XBRL_MAPPING_BALANCE
    + PGC_XBRL_MAPPING_CASHFLOW
    + PGC_XBRL_MAPPING_LEASES
    + PGC_XBRL_MAPPING_ESEF
)


def _upsert_mapping(conn, mapping) -> int:
    existing = conn.execute(
        text(
            """
            SELECT 1
            FROM pgc_xbrl_mapping m
            WHERE m.xbrl_concept_qname = :xbrl_concept
              AND m.pgc_account_codigo = :pgc_codigo
            LIMIT 1
            """
        ),
        {
            "xbrl_concept": mapping["xbrl_concept_qname"],
            "pgc_codigo": mapping["pgc_account_codigo"],
        },
    ).first()
    if existing:
        return 0

    conn.execute(
        text(
            """
            INSERT INTO pgc_xbrl_mapping (
                xbrl_concept_qname, pgc_account_codigo, confidence,
                mapping_type, note, is_active
            )
            VALUES (
                :xbrl_concept, :pgc_codigo, :confidence,
                :mapping_type, :note, true
            )
            """
        ),
        {
            "xbrl_concept": mapping["xbrl_concept_qname"],
            "pgc_codigo": mapping["pgc_account_codigo"],
            "confidence": mapping["confidence"],
            "mapping_type": mapping["mapping_type"],
            "note": mapping["note"],
        },
    )
    return 1


def run_sync(engine=None) -> dict[str, int]:
    engine = engine or create_engine(get_database_url(), future=True)

    with engine.begin() as conn:
        mappings_upserted = sum(_upsert_mapping(conn, m) for m in ALL_MAPPINGS)

    return {"mappings_upserted": mappings_upserted}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed PGC-XBRL mapping data")
    parser.add_argument("--db-url", help="Database URL override")
    args = parser.parse_args()

    engine = create_engine(args.db_url or os.getenv("DATABASE_URL") or get_database_url(), future=True)
    run_sync(engine=engine)


if __name__ == "__main__":
    main()
