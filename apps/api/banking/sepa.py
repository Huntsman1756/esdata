"""SEPA pain.001 XML generator and BIC validation.

Pure Python — uses xml.etree.ElementTree (stdlib).  No external
dependencies required.

Supported document:
    pain.001.001.03 — Customer Credit Transfer Initiation (SEPA)

Usage:
    from banking.sepa import generate_pain001, validate_bic
    xml_bytes = generate_pain001(debtor, payment_info, transactions)
    result = validate_bic("BSCHESMM")
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# BIC / FI-ID validation
# ---------------------------------------------------------------------------

_BIC_RE: re.Pattern[str] = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?$")


def validate_bic(bic: str) -> dict:
    """Validate a BIC/FI-ID code.

    Returns a dict with:
        - valid: bool
        - bic: str (cleaned, uppercase)
        - country_code: str | None
        - location_code: str | None
        - branch_code: str | None
        - errors: list[str]
    """
    errors: list[str] = []
    cleaned = bic.strip().upper()

    if not cleaned:
        return {
            "valid": False,
            "bic": "",
            "country_code": None,
            "location_code": None,
            "branch_code": None,
            "errors": ["BIC is empty"],
        }

    if not _BIC_RE.match(cleaned):
        return {
            "valid": False,
            "bic": cleaned,
            "country_code": None,
            "location_code": None,
            "branch_code": None,
            "errors": ["BIC format invalid: expected 8 or 11 alphanumeric chars (AAAA BB CC LLL)"],
        }

    if len(cleaned) not in (8, 11):
        errors.append(f"BIC length {len(cleaned)} not valid (expected 8 or 11)")

    country_code = cleaned[4:6]
    location_code = cleaned[6:8]
    branch_code = cleaned[8:] if len(cleaned) == 11 else None

    # Location code should not be "0" or "O"
    if location_code in ("00", "OO"):
        errors.append("BIC location code is not valid (00 or OO)")

    return {
        "valid": len(errors) == 0,
        "bic": cleaned,
        "country_code": country_code,
        "location_code": location_code,
        "branch_code": branch_code,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# pain.001.001.03 generator
# ---------------------------------------------------------------------------

_NS = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"


def _ns_tag(tag: str) -> str:
    return f"{{{_NS}}}{tag}"


def _set(elem: ET.Element, subtag: str, value: str | None) -> None:
    if value is not None:
        child = elem
        parts = subtag.split("/")
        for part in parts:
            child = ET.SubElement(child, _ns_tag(part))
        child.text = str(value)


def _set_optional(elem: ET.Element, subtag: str, value: Any, default: Any = None) -> None:
    if value is not None and value != default:
        child = elem
        parts = subtag.split("/")
        for part in parts:
            child = ET.SubElement(child, _ns_tag(part))
        child.text = str(value)


def _build_pmt_inf(
    payment_info_id: str,
    batch_booking: bool,
    nb_of_transactions: int,
    control_sum: float,
    execution_date: str,
    debtor_name: str,
    debtor_iban: str,
    debtor_bic: str | None,
    transactions: list[dict],
) -> ET.Element:
    """Build a PmtInf element."""
    pmt_inf = ET.Element(_ns_tag("PmtInf"))
    _set(pmt_inf, "PmtInfId", payment_info_id)
    _set(pmt_inf, "PmtMtd", "TRF")  # Bank transfer
    _set_optional(pmt_inf, "BtchBookg", "true" if batch_booking else "false", "false")
    _set(pmt_inf, "NbOfTxs", str(nb_of_transactions))
    _set(pmt_inf, "CtrlSum", f"{control_sum:.2f}")
    _set(pmt_inf, "PmtTpInf/SvcLvl/Cd", "SEPA")
    _set(pmt_inf, "ReqdExctnDt", execution_date)

    # Debtor
    debtor = ET.Element(_ns_tag("Dbtr"))
    _set(debtor, "Nm", debtor_name)
    pmt_inf.append(debtor)

    # Debtor account
    debtor_acct = ET.Element(_ns_tag("DbtrAcct"))
    id_elem = ET.SubElement(debtor_acct, _ns_tag("Id"))
    _set(id_elem, "IBAN", debtor_iban)
    pmt_inf.append(debtor_acct)

    # Debtor agent (BIC)
    if debtor_bic:
        debtor_agent = ET.Element(_ns_tag("DbtrAgt"))
        fin_id = ET.SubElement(debtor_agent, _ns_tag("FinInstnId"))
        _set(fin_id, "BIC", debtor_bic)
        pmt_inf.append(debtor_agent)

    # Credit transfer transactions
    for tx in transactions:
        tx_elem = ET.Element(_ns_tag("CdtTrfTxInf"))
        _set(tx_elem, "PmtId/EndToEndId", tx.get("end_to_end_id", "NOCODE"))
        _set(tx_elem, "PmtId/InstrId", tx.get("instruction_id", "NOCODE"))
        amt = ET.SubElement(tx_elem, _ns_tag("Amt"))
        instd_amt = ET.SubElement(amt, _ns_tag("InstdAmt"))
        instd_amt.text = f"{tx['amount']:.2f}"
        instd_amt.set("Ccy", tx.get("currency", "EUR"))

        # Creditor
        creditor = ET.Element(_ns_tag("Cdtr"))
        _set(creditor, "Nm", tx["creditor_name"])
        tx_elem.append(creditor)

        # Creditor IBAN
        cdtr_acct = ET.Element(_ns_tag("CdtrAcct"))
        cdtr_id = ET.SubElement(cdtr_acct, _ns_tag("Id"))
        _set(cdtr_id, "IBAN", tx["creditor_iban"])
        tx_elem.append(cdtr_acct)

        # Creditor BIC
        if tx.get("creditor_bic"):
            cdtr_agt = ET.Element(_ns_tag("CdtrAgt"))
            fin_id = ET.SubElement(cdtr_agt, _ns_tag("FinInstnId"))
            _set(fin_id, "BIC", tx["creditor_bic"])
            tx_elem.append(cdtr_agt)

        # Remittance info
        if tx.get("remittance_info"):
            rmce = ET.SubElement(tx_elem, _ns_tag("RmtInf"))
            _set(rmce, "Ustrd", tx["remittance_info"])

        pmt_inf.append(tx_elem)

    return pmt_inf


def generate_pain001(
    debtor_name: str,
    debtor_iban: str,
    debtor_bic: str | None = None,
    execution_date: str | None = None,
    payment_info_id_prefix: str = "PAY",
    batch_booking: bool = True,
    transactions: list[dict] | None = None,
) -> bytes:
    """Generate a pain.001.001.03 XML document.

    Args:
        debtor_name: Name of the ordering customer.
        debtor_iban: IBAN of the ordering account.
        debtor_bic: BIC of the debtor's bank (optional).
        execution_date: Execution date in YYYY-MM-DD format (defaults to today).
        payment_info_id_prefix: Prefix for payment info IDs.
        batch_booking: Whether to batch book transactions.
        transactions: List of dicts with keys:
            - creditor_name (str, required)
            - creditor_iban (str, required)
            - amount (float, required)
            - currency (str, default "EUR")
            - creditor_bic (str, optional)
            - remittance_info (str, optional)
            - end_to_end_id (str, optional, defaults to "NOCODE")
            - instruction_id (str, optional, defaults to "NOCODE")

    Returns:
        XML bytes of the pain.001 document.
    """
    if execution_date is None:
        execution_date = date.today().isoformat()

    if transactions is None:
        transactions = []

    # Group transactions by creditor_iban to create separate payment info blocks
    creditor_groups: dict[str, list[dict]] = {}
    for tx in transactions:
        key = tx["creditor_iban"]
        if key not in creditor_groups:
            creditor_groups[key] = []
        creditor_groups[key].append(tx)

    # Build root document
    doc = ET.Element(_ns_tag("Document"))
    doc.set("xmlns", _NS)

    pain_001 = ET.SubElement(doc, _ns_tag("CstmrCdtTrfInitn"))
    _set(pain_001, "GrpHdr/MsgId", f"{payment_info_id_prefix}-{hashlib.sha256(execution_date.encode()).hexdigest()[:8]}")
    _set(pain_001, "GrpHdr/CrtDt", execution_date)
    _set(pain_001, "GrpHdr/Dbtr", debtor_name)

    # Debtor agent
    grp_hdr = ET.SubElement(pain_001, _ns_tag("GrpHdr"))
    _set(grp_hdr, "MsgId", f"{payment_info_id_prefix}-{hashlib.sha256(execution_date.encode()).hexdigest()[:8]}")
    _set(grp_hdr, "CrtDt", execution_date)
    _set(grp_hdr, "Dbtr", debtor_name)

    debtor_agent = ET.SubElement(grp_hdr, _ns_tag("DbtrAgt"))
    fin_id = ET.SubElement(debtor_agent, _ns_tag("FinInstnId"))
    if debtor_bic:
        _set(fin_id, "BIC", debtor_bic)
    else:
        # Use IBAN to derive BBAN country if BIC not available
        _set(fin_id, "ClrSysMmbId/ClrSysId/Cd", "SEPA")
        _set(fin_id, "ClrSysMmbId/MmbId", "XXXXXX")

    # Build payment info blocks per creditor
    total_nb = 0
    total_sum = 0.0

    for idx, (creditor_iban, group_txs) in enumerate(sorted(creditor_groups.items())):
        pmt_inf_id = f"{payment_info_id_prefix}-{idx:03d}"
        group_sum = sum(tx["amount"] for tx in group_txs)
        nb_tx = len(group_txs)
        total_nb += nb_tx
        total_sum += group_sum

        pmt_inf = _build_pmt_inf(
            payment_info_id=pmt_inf_id,
            batch_booking=batch_booking,
            nb_of_transactions=nb_tx,
            control_sum=group_sum,
            execution_date=execution_date,
            debtor_name=debtor_name,
            debtor_iban=debtor_iban,
            debtor_bic=debtor_bic,
            transactions=group_txs,
        )
        pain_001.append(pmt_inf)

    # Set header totals
    _set(grp_hdr, "NbOfTxs", str(total_nb))
    _set(grp_hdr, "CtrlSum", f"{total_sum:.2f}")

    # Pretty print
    ET.indent(doc, space="  ")
    xml_bytes = ET.tostring(doc, encoding="utf-8", xml_declaration=True)
    return xml_bytes


# ---------------------------------------------------------------------------
# Batch grouping helper
# ---------------------------------------------------------------------------

def group_transactions(
    transactions: list[dict],
    max_batch_size: int = 999,
    group_by: str = "creditor_iban",
) -> list[dict]:
    """Group transactions for SEPA batch processing.

    Args:
        transactions: List of transaction dicts.
        max_batch_size: Max transactions per payment info block (default 999).
        group_by: Field to group by (default "creditor_iban").

    Returns:
        List of grouped transaction lists.
    """
    max_batch_size = max_batch_size or 999
    groups: dict[str, list[dict]] = {}
    ordered_keys: list[str] = []

    for tx in transactions:
        key = tx.get(group_by, "default")
        if key not in groups:
            groups[key] = []
            ordered_keys.append(key)
        groups[key].append(tx)

    result: list[list[dict]] = []
    for key in ordered_keys:
        batch = groups[key]
        # Split into chunks if exceeding max_batch_size
        for i in range(0, len(batch), max_batch_size):
            result.append(batch[i:i + max_batch_size])

    return result
