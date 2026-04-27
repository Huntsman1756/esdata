"""ISO 20022 XML parser for pain.008.001.08 (customer credit transfer).

Pure Python — uses xml.etree.ElementTree (stdlib).  No external
dependencies required.

Supported document:
    pain.008.001.08 — Customer Credit Transfer Initiation

Usage:
    from banking.iso20022 import parse_iso20022
    result = parse_iso20022(xml_bytes)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any


# ISO 20022 namespace prefixes we recognise
KNOWN_NS: dict[str, str] = {
    "urn:iso:std:iso:20022:tech:xsd:pain.008.001.08": "pain008",
    "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02": "pain008",
    "urn:iso:std:iso:20022:tech:xsd:pain.008.001.03": "pain008",
    "urn:iso:std:iso:20022:tech:xsd:pain.008.001.04": "pain008",
    "urn:iso:std:iso:20022:tech:xdxsd:pain.008.001.04": "pain008",
}

# Map namespace URI -> prefix used in xpath
_NS_MAP: dict[str, str] = {}


def _detect_ns(root: ET.Element) -> str:
    """Detect the ISO 20022 namespace from the root element."""
    ns = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""
    if ns in KNOWN_NS:
        return ns
    # Try any namespace
    for uri in KNOWN_NS:
        if root.tag.endswith(uri.split(":")[-1]) or ns in uri:
            return uri
    return ""


def _ns(tag: str, ns: str) -> str:
    """Build a namespace-qualified tag for ElementTree: {uri}tag."""
    if ns:
        return f"{{{ns}}}{tag}"
    return tag


def _build_ns_path(path: str, ns: str) -> str:
    """Convert 'GrpHdr/MsgId' or './/GrpHdr' to '{ns}GrpHdr/{ns}MsgId'."""
    if path.startswith('.//'):
        prefix = './/'
        remainder = path[3:]
    elif path.startswith('./'):
        prefix = './'
        remainder = path[2:]
    elif path.startswith('/'):
        prefix = '/'
        remainder = path[1:]
    else:
        prefix = ''
        remainder = path

    parts = remainder.split('/')
    ns_parts = [f"{{{ns}}}{p}" for p in parts]
    return prefix + '/'.join(ns_parts)


def _find_el(root: ET.Element, xpath: str, ns: str) -> ET.Element | None:
    """Find a single element by xpath. Returns the Element (not its text).

    Supports './/Tag', './Tag', '/Tag', or plain 'Tag'.
    Uses iter() for reliable namespace-agnostic search within root only.
    """
    local = xpath.split(':')[-1].split('/')[-1]

    # Build a scoped search: only descend into root's children, not root itself
    if ns:
        ns_tag = f"{{{ns}}}{local}"
        for child in root:
            for elem in child.iter():
                if elem.tag == ns_tag:
                    return elem
    # Fallback: try without namespace
    for child in root:
        for elem in child.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == local:
                return elem
    return None


def _find(root: ET.Element, xpath: str, ns: str) -> str | None:
    """Find a single element by xpath using detected namespace."""
    elem = _find_el(root, xpath, ns)
    return elem.text if elem is not None else None


def _find_all(root: ET.Element, xpath: str, ns: str) -> list[ET.Element]:
    """Find all elements by xpath using detected namespace."""
    local = xpath.split(':')[-1].split('/')[-1]
    results: list[ET.Element] = []
    seen = set()

    if ns:
        ns_tag = f"{{{ns}}}{local}"
        for child in root:
            for elem in child.iter():
                if elem.tag == ns_tag and elem not in seen:
                    results.append(elem)
                    seen.add(elem)
    # Fallback: try without namespace
    for child in root:
        for elem in child.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == local and elem not in seen:
                results.append(elem)
                seen.add(elem)
    return results


def _parse_group_header(root: ET.Element, ns: str) -> dict[str, Any] | None:
    """Parse GrpHdr (Group Header)."""
    grp_hdr = _find_el(root, ".//GrpHdr", ns)
    if grp_hdr is None:
        return None

    result: dict[str, Any] = {}

    # GrpHdr is an element, not a path — find its children
    for child in grp_hdr:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "MsgId":
            result["msg_id"] = child.text
        elif tag == "CreDtTm":
            result["creation_datetime"] = child.text
        elif tag == "NbOfTxs":
            result["number_of_transactions"] = child.text
        elif tag == "CtrlSum":
            result["control_sum"] = child.text
        elif tag == "InitgPrty":
            result["instruction_priority"] = child.text

    return result if result else None


def _parse_payment_info(root: ET.Element, ns: str, pmt_inf_el: ET.Element) -> dict[str, Any]:
    """Parse a single PmtInf (Payment Information) block."""
    pmt: dict[str, Any] = {}

    for child in pmt_inf_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "PmtInfId":
            pmt["payment_information_id"] = child.text
        elif tag == "PmtMtd":
            pmt["payment_method"] = child.text
        elif tag == "BtchBookg":
            pmt["batch_booking"] = child.text.lower() == "true" if child.text else None
        elif tag == "NbOfTxs":
            pmt["number_of_transactions"] = child.text
        elif tag == "CtrlSum":
            pmt["control_sum"] = child.text
        elif tag == "PmtTpInf":
            pmt["payment_type_info"] = _parse_payment_type_info(child, ns)
        elif tag == "ReqdExctnDt":
            pmt["requested_execution_date"] = child.text
        elif tag == "Dbtr":
            pmt["debtor"] = _parse_party(child, ns)
        elif tag == "DbtrAcct":
            pmt["debtor_account"] = _parse_account(child, ns)
        elif tag == "DbtrAgt":
            pmt["debtor_agent"] = _parse_agent(child, ns)
        elif tag == "CdtrAgt":
            pmt["creditor_agent"] = _parse_agent(child, ns)
        elif tag == "ChqInstr":
            pmt["cheque_instruction"] = _parse_cheque(child)

    # Parse child payment instructions (ChqInstr is separate; individual txns are direct children with specific structure)
    pmt["transactions"] = _parse_transactions(root, ns, pmt_inf_el)

    return pmt


def _parse_payment_type_info(pmt_tp_el: ET.Element, ns: str) -> dict[str, str] | None:
    """Parse PmtTpInf (Payment Type Information)."""
    result: dict[str, str] = {}
    for child in pmt_tp_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "SvcLn":
            for svc_child in child:
                svc_tag = svc_child.tag.split("}")[-1] if "}" in svc_child.tag else svc_child.tag
                if svc_tag == "Prtry":
                    result["service_level"] = svc_child.text
        elif tag == "LclInstrm":
            for lc_child in child:
                lc_tag = lc_child.tag.split("}")[-1] if "}" in lc_child.tag else lc_child.tag
                if lc_tag == "Prtry":
                    result["local_instrument"] = lc_child.text
        elif tag == "CtgryPurp":
            result["category_purpose"] = child.text
    return result if result else None


def _parse_party(party_el: ET.Element, ns: str) -> dict[str, str] | None:
    """Parse a party element (Debtor, Creditor)."""
    result: dict[str, str] = {}
    for child in party_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "Nm":
            result["name"] = child.text
        elif tag == "PstlAdr":
            result["address"] = _parse_address(child, ns)
    return result if result else None


def _parse_address(addr_el: ET.Element, ns: str) -> dict[str, str] | None:
    """Parse a postal address."""
    result: dict[str, str] = {}
    for child in addr_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "Ctry":
            result["country"] = child.text
        elif tag == "AdrLine":
            line = child.text
            if line:
                result.setdefault("lines", []).append(line)
    return result if result else None


def _parse_account(acct_el: ET.Element, ns: str) -> dict[str, str] | None:
    """Parse an account element, extracting IBAN if present."""
    result: dict[str, str] = {}
    for child in acct_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "Id":
            for id_child in child:
                id_tag = id_child.tag.split("}")[-1] if "}" in id_child.tag else id_child.tag
                if id_tag == "IBAN":
                    result["iban"] = id_child.text
                elif id_tag == "Othr":
                    other_id = id_child.find(".//Id")
                    if other_id is not None:
                        result["other_id"] = other_id.text
                    other_schem = id_child.find(".//Prtry")
                    if other_schem is not None:
                        result["other_scheme"] = other_schem.text
    return result if result else None


def _parse_agent(agent_el: ET.Element, ns: str) -> dict[str, str] | None:
    """Parse an agent element (Debtor/Creditor Agent)."""
    result: dict[str, str] = {}
    for child in agent_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "FinInstnId":
            for fin_child in child:
                fin_tag = fin_child.tag.split("}")[-1] if "}" in fin_child.tag else fin_child.tag
                if fin_tag == "BICFI":
                    result["bicfi"] = fin_child.text
                elif fin_tag == "Othr":
                    other_id = fin_child.find(".//Id")
                    if other_id is not None:
                        result["other_id"] = other_id.text
    return result if result else None


def _parse_cheque(chq_el: ET.Element) -> dict[str, str] | None:
    """Parse cheque instruction."""
    result: dict[str, str] = {}
    for child in chq_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "Tp":
            for tp_child in child:
                tp_tag = tp_child.tag.split("}")[-1] if "}" in tp_child.tag else tp_child.tag
                if tp_tag == "CdOrPrtry":
                    for cd_child in tp_child:
                        cd_tag = cd_child.tag.split("}")[-1] if "}" in cd_child.tag else cd_child.tag
                        if cd_tag == "Cd":
                            result["type"] = cd_child.text
        elif tag == "ChqNb":
            result["cheque_number"] = child.text
        elif tag == "ChqPymntMtd":
            result["payment_method"] = child.text
    return result if result else None


def _parse_transactions(root: ET.Element, ns: str, pmt_inf_el: ET.Element) -> list[dict[str, Any]]:
    """Parse individual payment transactions within a PmtInf block."""
    transactions: list[dict[str, Any]] = []

    # Find transaction blocks: TxInfAndPmtDtls or CstmrPmtInf
    txns = []
    for child in pmt_inf_el:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("TxInfAndPmtDtls", "CstmrPmtInf"):
            txns.append(child)

    # Fallback: look for elements with PmtId + InstdAmt
    if not txns:
        for child in pmt_inf_el:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            has_pmt_id = _find_el(child, ".//PmtId", ns) is not None
            has_instr_amt = _find_el(child, ".//InstdAmt", ns) is not None
            if has_pmt_id or has_instr_amt:
                txns.append(child)

    for txn_el in txns:
        txn: dict[str, Any] = {}

        # Payment ID
        pmt_id_el = _find_el(txn_el, ".//PmtId", ns)
        if pmt_id_el is not None:
            end_to_end = _find_el(pmt_id_el, ".//EndToEndId", ns)
            if end_to_end is not None:
                txn["end_to_end_id"] = end_to_end.text
            instr_id = _find_el(pmt_id_el, ".//InstrId", ns)
            if instr_id is not None:
                txn["instruction_id"] = instr_id.text

        # Amount
        inst_amt_el = _find_el(txn_el, ".//InstdAmt", ns)
        if inst_amt_el is not None:
            txn["amount"] = inst_amt_el.text
            txn["currency"] = inst_amt_el.get("Ccy", "EUR")

        # Remittance
        rmt_el = _find_el(txn_el, ".//RmtInf", ns)
        if rmt_el is not None:
            rmt_info: dict[str, str] = {}
            ustrd = _find_el(rmt_el, ".//Ustrd", ns)
            if ustrd is not None:
                rmt_info["unstructured"] = ustrd.text
            strd = _find_el(rmt_el, ".//Strd", ns)
            if strd is not None:
                cdtr_ref = _find_el(strd, ".//CdtrRefInf", ns)
                if cdtr_ref is not None:
                    ref = _find_el(cdtr_ref, ".//Ref", ns)
                    if ref is not None:
                        rmt_info["structured_reference"] = ref.text
                        ref_type = _find_el(cdtr_ref, ".//Tp", ns)
                        if ref_type is not None:
                            cd = _find_el(ref_type, ".//Cd", ns)
                            if cd is not None:
                                rmt_info["reference_type"] = cd.text
                            prtry = _find_el(ref_type, ".//Prtry", ns)
                            if prtry is not None:
                                rmt_info["reference_type"] = prtry.text
            if rmt_info:
                txn["remittance"] = rmt_info

        # Creditor
        cdtr_el = _find_el(txn_el, ".//Cdtr", ns)
        if cdtr_el is not None:
            txn["creditor"] = _parse_party(cdtr_el, ns)

        # Creditor account
        cdtr_acct_el = _find_el(txn_el, ".//CdtrAcct", ns)
        if cdtr_acct_el is not None:
            txn["creditor_account"] = _parse_account(cdtr_acct_el, ns)

        # Creditor agent
        cdtr_agt_el = _find_el(txn_el, ".//CdtrAgt", ns)
        if cdtr_agt_el is not None:
            txn["creditor_agent"] = _parse_agent(cdtr_agt_el, ns)

        # Charge bearer
        chrg_br = _find_el(txn_el, ".//ChrgBr", ns)
        if chrg_br is not None:
            txn["charge_bearer"] = chrg_br.text

        # Requested execution date
        req_dt = _find_el(txn_el, ".//ReqdExctnDt", ns)
        if req_dt is not None:
            txn["requested_execution_date"] = req_dt.text

        if txn:
            transactions.append(txn)

    return transactions


def parse_iso20022(xml_bytes: bytes) -> dict[str, Any]:
    """Parse an ISO 20022 pain.008 XML document.

    Returns a dict with:
        - valid: bool
        - document_type: str | None (e.g. "pain.008.001.08")
        - namespace: str
        - group_header: dict | None
        - payment_informations: list[dict]
        - total_transactions: int
        - total_control_sum: str | None
        - errors: list[str]
    """
    errors: list[str] = []
    result: dict[str, Any] = {
        "valid": False,
        "document_type": None,
        "namespace": "",
        "group_header": None,
        "payment_informations": [],
        "total_transactions": 0,
        "total_control_sum": None,
        "errors": [],
    }

    if not xml_bytes:
        errors.append("XML input is empty")
        result["errors"] = errors
        return result

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        errors.append(f"XML parse error: {e}")
        result["errors"] = errors
        return result

    # Detect namespace
    ns = _detect_ns(root)
    result["namespace"] = ns

    # Extract document type from namespace
    if ns in KNOWN_NS:
        doc_type = ns.split(":")[-1] if ":" in ns else ns
        result["document_type"] = doc_type

    # Parse group header
    grp_hdr = _parse_group_header(root, ns)
    result["group_header"] = grp_hdr

    if grp_hdr:
        result["total_control_sum"] = grp_hdr.get("control_sum")
        try:
            result["total_transactions"] = int(grp_hdr.get("number_of_transactions", 0))
        except (ValueError, TypeError):
            result["total_transactions"] = 0

    # Parse payment information blocks
    pmt_inf_els = _find_all(root, ".//PmtInf", ns)

    if not pmt_inf_els:
        # Try searching without strict namespace
        pmt_inf_els = root.findall(".//PmtInf")

    if not pmt_inf_els:
        errors.append("No PmtInf (Payment Information) blocks found")
    else:
        for pmt_el in pmt_inf_els:
            pmt = _parse_payment_info(root, ns, pmt_el)
            result["payment_informations"].append(pmt)

        # Update total counts from PmtInf blocks
        total_txns = 0
        total_sum = 0.0
        for pmt in result["payment_informations"]:
            try:
                total_txns += int(pmt.get("number_of_transactions", 0))
            except (ValueError, TypeError):
                pass
            ctrl = pmt.get("control_sum")
            if ctrl:
                try:
                    total_sum += float(ctrl)
                except (ValueError, TypeError):
                    pass

        if total_txns > 0:
            result["total_transactions"] = total_txns
        if total_sum > 0:
            result["total_control_sum"] = f"{total_sum:.2f}"

    result["valid"] = len(errors) == 0
    result["errors"] = errors
    return result
