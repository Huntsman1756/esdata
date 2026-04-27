"""Worker module for seeding and managing XBRL taxonomy data.

Supports ESEF core taxonomy (esef_cor) and IFRS taxonomy concepts
for accounting concept lookups, labels, and metadata.
"""

import argparse
from pathlib import Path

from sqlalchemy import create_engine, text

if __package__:
    from .runtime import get_database_url
else:
    from runtime import get_database_url


# ---------------------------------------------------------------------------
# ESEF Core + IFRS taxonomy seed data
# ---------------------------------------------------------------------------

_ESEF_CONCEPTS = [
    # --- IFRS 18 — Income Statement ---
    {
        "concept_qname": "ifrs-full_RevenueFromContractsWithCustomersExcludingRevenueFromFinancialServices",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Revenue from contracts with customers",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 18",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_InterestIncome",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Interest income",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 18",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_InterestExpense",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Interest expense",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 18",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_ProfitLoss",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Profit or loss",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_EarningsPerShareBasicAndDiluted",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Earnings per share — basic and diluted",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 33",
        "data_type": "xbrli:perShareItemType",
        "period_type": "duration",
        "is_monetary": False,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_OperatingProfitLoss",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Operating profit or loss",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 18",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_ExpensesFromOperatingActivities",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Expenses from operating activities",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 18",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    # --- IFRS 15 — Revenue ---
    {
        "concept_qname": "ifrs-full_RevenueFromContractsWithCustomersGoods",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Revenue from contracts with customers — goods",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 15",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_RevenueFromContractsWithCustomersServices",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Revenue from contracts with customers — services",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 15",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_RevenueFromContractsWithCustomersDisaggregatedByNatureOfGoodsOrServices",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Revenue — disaggregated by nature of goods or services",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 15",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    # --- IAS 1 — Balance Sheet ---
    {
        "concept_qname": "ifrs-full_Assets",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Assets",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_Liabilities",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Liabilities",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_AssetsCurrent",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Current assets",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_AssetsNoncurrent",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Non-current assets",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_LiabilitiesCurrent",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Current liabilities",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_LiabilitiesNoncurrent",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Non-current liabilities",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_EquityAttributableToOwnerOfParent",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Equity attributable to owner of parent",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    # --- IAS 16 — Property, Plant and Equipment ---
    {
        "concept_qname": "ifrs-full_PropertyPlantAndEquipment",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Property, plant and equipment",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 16",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_PropertyPlantAndEquipmentGross",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Property, plant and equipment — gross",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 16",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    # --- IAS 38 — Intangible Assets ---
    {
        "concept_qname": "ifrs-full_IntangibleAssetsExcludingGoodwill",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Intangible assets excluding goodwill",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 38",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_Goodwill",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Goodwill",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 3",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    # --- IAS 7 / IFRS 7 — Cash & Financial Instruments ---
    {
        "concept_qname": "ifrs-full_CashAndCashEquivalents",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Cash and cash equivalents",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 7",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_CashFlowsFromOperatingActivitiesBeforeChangesInWorkingCapital",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Cash flows from operating activities — before changes in working capital",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 7",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_CashFlowsFromInvestingActivities",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Cash flows from investing activities",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 7",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_CashFlowsFromFinancingActivities",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Cash flows from financing activities",
        "label_language": "en",
        "label_role": "label",
        "standard": "IAS 7",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    # --- IFRS 16 — Leases ---
    {
        "concept_qname": "ifrs-full_RightOfUseAssets",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Right-of-use assets",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 16",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_LeaseLiabilities",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Lease liabilities",
        "label_language": "en",
        "label_role": "label",
        "standard": "IFRS 16",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    # --- ESEF Core extensions ---
    {
        "concept_qname": "esef_cor_EsefStandardType",
        "namespace": "http://xbrl.esma.europa.eu/2025-03-27/esef_cor",
        "label": "ESEF standard type",
        "label_language": "en",
        "label_role": "label",
        "standard": "ESEF",
        "data_type": "esef_cor:standardType",
        "period_type": "instant",
        "is_monetary": False,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "esef_cor_EsefReportingPeriodEndDate",
        "namespace": "http://xbrl.esma.europa.eu/2025-03-27/esef_cor",
        "label": "ESEF reporting period end date",
        "label_language": "en",
        "label_role": "label",
        "standard": "ESEF",
        "data_type": "xbrli:dateOnly",
        "period_type": "instant",
        "is_monetary": False,
        "is_negative_allowed": False,
    },
    # --- Spanish labels for key concepts ---
    {
        "concept_qname": "ifrs-full_ProfitLoss",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Beneficio o pérdida",
        "label_language": "es",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_Assets",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Activos",
        "label_language": "es",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_Liabilities",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Pasivos",
        "label_language": "es",
        "label_role": "label",
        "standard": "IAS 1",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": False,
    },
    {
        "concept_qname": "ifrs-full_RevenueFromContractsWithCustomersExcludingRevenueFromFinancialServices",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Ingresos por contratos con clientes",
        "label_language": "es",
        "label_role": "label",
        "standard": "IFRS 18",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "duration",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
    {
        "concept_qname": "ifrs-full_CashAndCashEquivalents",
        "namespace": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias",
        "label": "Efectivo y equivalentes de efectivo",
        "label_language": "es",
        "label_role": "label",
        "standard": "IAS 7",
        "data_type": "xbrli:monetaryItemType",
        "period_type": "instant",
        "is_monetary": True,
        "is_negative_allowed": True,
    },
]


def seed_taxonomy(*, engine) -> int:
    """Seed the xbrl_taxonomy table with ESEF/IFRS concepts.

    Returns the number of rows inserted.
    """
    columns = (
        "concept_qname",
        "namespace",
        "label",
        "label_language",
        "label_role",
        "standard",
        "data_type",
        "period_type",
        "is_monetary",
        "is_negative_allowed",
    )

    with engine.begin() as conn:
        dialect_name = conn.dialect.name
        insert_sql = text(
            _insert_do_nothing_sql(
                "xbrl_taxonomy",
                columns,
                ("concept_qname", "label_language", "label_role"),
                dialect_name=dialect_name,
            )
        )
        inserted = 0
        for concept in _ESEF_CONCEPTS:
            result = conn.execute(insert_sql, concept)
            inserted += result.rowcount or 0

    return inserted


def _insert_do_nothing_sql(table_name: str, columns: tuple[str, ...], conflict_target: tuple[str, ...], *, dialect_name: str) -> str:
    column_list = ", ".join(columns)
    value_list = ", ".join(f":{column}" for column in columns)

    if dialect_name == "sqlite":
        return f"INSERT OR IGNORE INTO {table_name} ({column_list}) VALUES ({value_list})"

    conflict_list = ", ".join(conflict_target)
    return (
        f"INSERT INTO {table_name} ({column_list}) VALUES ({value_list}) "
        f"ON CONFLICT ({conflict_list}) DO NOTHING"
    )


def run_seed(*, engine=None):
    engine = engine or create_engine(get_database_url(), future=True)
    return seed_taxonomy(engine=engine)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print concepts without inserting")
    args = parser.parse_args()

    if args.dry_run:
        print(f"Concepts to insert: {len(_ESEF_CONCEPTS)}")
        for c in _ESEF_CONCEPTS:
            print(f"  {c['concept_qname']} [{c['label_language']}] {c['label']}")
        return

    inserted = run_seed()
    print(f"Inserted {inserted} taxonomy rows")


if __name__ == "__main__":
    main()
