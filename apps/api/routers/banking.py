"""Banking router — utilitarian endpoints for payment data validation/parsing.

Fase 17 — Rails bancarios, pagos y formatos operativos.

This module is intentionally lightweight: no DB writes, no persistence.
All endpoints are stateless and return validated/parsed data only.
"""

import xml.etree.ElementTree as ET

from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from banking.iban import validate_iban
from banking.iso20022 import parse_iso20022
from banking.n43 import parse_n43
from banking.sepa import generate_pain001, validate_bic, group_transactions
from schemas import (
    IbanValidateRequest, IbanValidateResponse,
    Iso20022ParseResponse, N43ParseResponse,
    SepaBicValidateRequest, SepaBicValidateResponse,
    SepaGenerateRequest, SepaGenerateResponse,
    SepaGroupBatch, SepaGroupTransactionsRequest, SepaGroupTransactionsResponse,
)

router = APIRouter(prefix="/v1/banking", tags=["banking"])


# ---------------------------------------------------------------------------
# IBAN
# ---------------------------------------------------------------------------

@router.post(
    "/iban/validate",
    response_model=IbanValidateResponse,
    operation_id="iban_validate",
)
async def iban_validate(req: IbanValidateRequest):
    """Validate an IBAN string (format + mod-97 check).

    Stateless — no DB access.  Returns country code, format validity,
    length validation against SWIFT registry and mod-97 check result.
    """
    iban = req.iban
    if not iban or not iban.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "IBAN is required"},
        )

    result = validate_iban(iban)
    return IbanValidateResponse(result=result)


@router.get(
    "/iban/countries",
    operation_id="iban_country_codes",
)
async def iban_country_codes():
    """Return the list of country codes supported for length validation."""
    return {"supported_countries": list(sorted(validate_iban.__globals__["IBAN_COUNTRY_LENGTHS"].keys()))}


# ---------------------------------------------------------------------------
# ISO 20022
# ---------------------------------------------------------------------------

@router.post(
    "/iso20022/parse",
    response_model=Iso20022ParseResponse,
    operation_id="iso20022_parse",
)
async def iso20022_parse(xml_file: UploadFile = File(..., description="XML file to parse")):
    """Parse an ISO 20022 pain.008 XML document.

    Extracts group header, payment information blocks, individual
    transactions with amounts, creditors, remittance info, etc.

    Stateless — no DB access.  Returns structured dict.
    """
    content = await xml_file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail={"error": "XML file is empty"},
        )

    result = parse_iso20022(content)
    return Iso20022ParseResponse(**result)


# ---------------------------------------------------------------------------
# N43 / AEB Cuaderno Bancario
# ---------------------------------------------------------------------------

@router.post(
    "/n43/parse",
    response_model=N43ParseResponse,
    operation_id="n43_parse",
)
async def n43_parse(n43_file: UploadFile = File(..., description="N43 bank statement file")):
    """Parse an N43 bank statement file (AEB norma 43).

    Extracts account headers, transactions, balances, and metadata
    from fixed-width text bank statement files.

    Stateless — no DB access.  Returns structured dict.
    """
    content = await n43_file.read()
    text = content.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "N43 file is empty"},
        )

    result = parse_n43(text)
    return N43ParseResponse(**result.model_dump())


# ---------------------------------------------------------------------------
# SEPA / pain.001
# ---------------------------------------------------------------------------

@router.post(
    "/sepa/bic/validate",
    response_model=SepaBicValidateResponse,
    operation_id="sepa_bic_validate",
)
async def sepa_bic_validate(req: SepaBicValidateRequest):
    """Validate a BIC/FI-ID code (8 or 11 alphanumeric chars).

    Stateless — no DB access.  Returns country code, location code,
    branch code and validation result.
    """
    result = validate_bic(req.bic)
    return SepaBicValidateResponse(result=result)


@router.post(
    "/sepa/generate",
    response_model=SepaGenerateResponse,
    operation_id="sepa_generate",
)
async def sepa_generate(req: SepaGenerateRequest):
    """Generate a pain.001.001.03 SEPA XML file.

    Creates a Customer Credit Transfer Initiation document with
    automatic batch grouping by creditor IBAN.

    Stateless — no DB access.  Returns XML bytes and metadata.
    """
    errors: list[str] = []

    # Validate debtor IBAN
    iban_result = validate_iban(req.debtor_iban)
    if not iban_result["valid"]:
        errors.append(f"Debtor IBAN invalid: {'; '.join(iban_result['errors'])}")

    # Validate debtor BIC if provided
    if req.debtor_bic:
        bic_result = validate_bic(req.debtor_bic)
        if not bic_result["valid"]:
            errors.append(f"Debtor BIC invalid: {'; '.join(bic_result['errors'])}")

    # Validate transactions
    for i, tx in enumerate(req.transactions):
        tx_iban = validate_iban(tx.creditor_iban)
        if not tx_iban["valid"]:
            errors.append(f"Transaction {i}: Creditor IBAN invalid: {'; '.join(tx_iban['errors'])}")
        if tx.creditor_bic:
            tx_bic = validate_bic(tx.creditor_bic)
            if not tx_bic["valid"]:
                errors.append(f"Transaction {i}: Creditor BIC invalid: {'; '.join(tx_bic['errors'])}")
        if tx.amount <= 0:
            errors.append(f"Transaction {i}: Amount must be positive, got {tx.amount}")

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"error": "Validation errors", "details": errors},
        )

    # Build transactions list for generator
    tx_list = []
    for tx in req.transactions:
        tx_list.append({
            "creditor_name": tx.creditor_name,
            "creditor_iban": tx.creditor_iban,
            "amount": tx.amount,
            "currency": tx.currency,
            "creditor_bic": tx.creditor_bic,
            "remittance_info": tx.remittance_info,
            "end_to_end_id": tx.end_to_end_id or "NOCODE",
            "instruction_id": tx.instruction_id or "NOCODE",
        })

    try:
        xml_bytes = generate_pain001(
            debtor_name=req.debtor_name,
            debtor_iban=req.debtor_iban,
            debtor_bic=req.debtor_bic,
            execution_date=req.execution_date,
            payment_info_id_prefix=req.payment_info_id_prefix,
            batch_booking=req.batch_booking,
            transactions=tx_list,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "XML generation failed", "details": str(exc)},
        )

    # Parse the generated XML to extract metadata
    root = ET.fromstring(xml_bytes)
    ns = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"

    def find(elem: ET.Element, path: str) -> str | None:
        qualified_path = "/".join(f"{{{ns}}}{segment}" for segment in path.split("/"))
        found = elem.find(qualified_path)
        return found.text if found is not None else None

    group_header = root.find(f"{{{ns}}}CstmrCdtTrfInitn")
    if group_header is None:
        group_header = root

    return SepaGenerateResponse(
        valid=True,
        document_type="pain.001.001.03",
        namespace=ns,
        group_header_msg_id=find(group_header, "GrpHdr/MsgId"),
        group_header_creation_date=find(group_header, "GrpHdr/CrtDt"),
        group_header_nb_of_txs=find(group_header, "GrpHdr/NbOfTxs"),
        group_header_control_sum=find(group_header, "GrpHdr/CtrlSum"),
        payment_info_count=len(group_header.findall(f"{{{ns}}}PmtInf")),
        xml_size_bytes=len(xml_bytes),
    )


@router.post(
    "/sepa/group",
    response_model=SepaGroupTransactionsResponse,
    operation_id="sepa_group_transactions",
)
async def sepa_group_transactions(req: SepaGroupTransactionsRequest):
    """Group transactions for SEPA batch processing.

    Groups by creditor_iban (or any other field) and splits into
    batches respecting max_batch_size.

    Stateless — no DB access.  Returns grouped batches with metadata.
    """
    batches = group_transactions(
        transactions=req.transactions,
        max_batch_size=req.max_batch_size,
        group_by=req.group_by,
    )

    batch_items = []
    for batch in batches:
        # Calculate totals from the batch
        total_amount = 0.0
        group_key = batch[0].get(req.group_by, "unknown") if batch else "unknown"
        for tx in batch:
            total_amount += tx.get("amount", 0.0)
        batch_items.append(
            SepaGroupBatch(
                group_key=group_key,
                transaction_count=len(batch),
                total_amount=total_amount,
                transactions=batch,
            )
        )

    return SepaGroupTransactionsResponse(
        total_transactions=len(req.transactions),
        total_batches=len(batch_items),
        batches=batch_items,
    )
