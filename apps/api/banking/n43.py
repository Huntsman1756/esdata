"""N43 / AEB cuaderno bancario parser.

Parsea archivos de extractos bancarios en formato N43 (AEB norma 43).
Texto fijo 80 chars/line con registros de tipos 11, 22, 23, 24, 33, 88.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Record type codes
# ---------------------------------------------------------------------------

RECORD_CABECERA = "11"
RECORD_MOVIMIENTO = "22"
RECORD_COMPLEMENTARIO_CONCEPTO = "23"
RECORD_COMPLEMENTARIO_IMPORTE = "24"
RECORD_FINAL_CUENTA = "33"
RECORD_FINAL_FICHERO = "88"

RECORD_TYPE_NAMES: dict[str, str] = {
    RECORD_CABECERA: "CabeceraDeCuenta",
    RECORD_MOVIMIENTO: "Movimiento",
    RECORD_COMPLEMENTARIO_CONCEPTO: "ComplementarioConcepto",
    RECORD_COMPLEMENTARIO_IMPORTE: "ComplementarioImporte",
    RECORD_FINAL_CUENTA: "FinalDeCuenta",
    RECORD_FINAL_FICHERO: "FinalDeFichero",
}


# ---------------------------------------------------------------------------
# Currency codes (ISO 4217 numeric -> alpha)
# ---------------------------------------------------------------------------

CURRENCY_CODES: dict[str, str] = {
    "036": "AUD",
    "124": "CAD",
    "208": "DKK",
    "392": "JPY",
    "554": "NZD",
    "578": "NOK",
    "752": "SEK",
    "756": "CHF",
    "826": "GBP",
    "840": "USD",
    "978": "EUR",
}


# ---------------------------------------------------------------------------
# Common concept codes (AEB)
# ---------------------------------------------------------------------------

COMMON_CONCEPTS: dict[str, str] = {
    "01": "TALONES - REINTEGROS",
    "02": "ABONARÉS - ENTREGAS - INGRESOS",
    "03": "DOMICILIADOS - RECIBOS - LETRAS - PAGOS POR SU CTA.",
    "04": "GIROS - TRANSFERENCIAS - TRASPASOS - CHEQUES",
    "05": "AMORTIZACIONES PRÉSTAMOS, CRÉDITOS, ETC.",
    "06": "REMESAS EFECTOS",
    "07": "SUSCRIPCIONES - DIV. PASIVOS - CANJES.",
    "08": "DIV. CUPONES - PRIMA JUNTA - AMORTIZACIONES",
    "09": "OPERACIONES DE BOLSA Y/O COMPRA /VENTA VALORES",
    "10": "CHEQUES GASOLINA",
    "11": "CAJERO AUTOMÁTICO",
    "12": "TARJETAS DE CRÉDITO - TARJETAS DÉBITO",
    "13": "OPERACIONES EXTRANJERO",
    "14": "DEVOLUCIONES E IMPAGADOS",
    "15": "NÓMINAS - SEGUROS SOCIALES",
    "16": "TIMBRES - CORRETAJE - PÓLIZA",
    "17": "INTERESES - COMISIONES – CUSTODIA - GASTOS E IMPUESTOS",
    "98": "ANULACIONES - CORRECCIONES ASIENTO",
    "99": "VARIOS",
}


# ---------------------------------------------------------------------------
# Field definitions per record type
# ---------------------------------------------------------------------------

# Each field: (name, from_pos, to_pos, format)
# from_pos/to_pos are 1-based inclusive positions
# format: N=numeric string, A=alpha, D=decimal/100, F=date(YYMMDD), I=integer

CABECERA_FIELDS: list[tuple[str, int, int, str]] = [
    ("Clave de la Entidad", 3, 6, "N"),
    ("Clave de Oficina", 7, 10, "N"),
    ("Nº de cuenta", 11, 20, "N"),
    ("Fecha inicial", 21, 26, "F"),
    ("Fecha final", 27, 32, "F"),
    ("Clave Debe o Haber", 33, 33, "N"),
    ("Importe saldo inicial", 34, 47, "D"),
    ("Clave de divisa", 48, 50, "N"),
    ("Modalidad de información", 51, 51, "N"),
    ("Nombre abreviado", 52, 77, "A"),
    ("Libre", 78, 80, "A"),
]

MOVIMIENTO_FIELDS: list[tuple[str, int, int, str]] = [
    ("Libre", 3, 6, "N"),
    ("Clave de Oficina Origen", 7, 10, "A"),
    ("Fecha operación", 11, 16, "F"),
    ("Fecha valor", 17, 22, "F"),
    ("Concepto común", 23, 24, "N"),
    ("Concepto propio", 25, 27, "N"),
    ("Clave Debe o Haber", 28, 28, "N"),
    ("Importe", 29, 42, "D"),
    ("Nº de documento", 43, 52, "N"),
    ("Referencia 1", 53, 64, "A"),
    ("Referencia 2", 65, 80, "A"),
]

COMPLEMENTARIO_CONCEPTO_FIELDS: list[tuple[str, int, int, str]] = [
    ("Código Dato", 3, 4, "N"),
    ("Concepto 1", 5, 42, "A"),
    ("Concepto 2", 43, 80, "A"),
]

COMPLEMENTARIO_IMPORTE_FIELDS: list[tuple[str, int, int, str]] = [
    ("Código Dato", 3, 4, "N"),
    ("Clave divisa origen del movimiento", 5, 7, "N"),
    ("Importe", 8, 21, "D"),
    ("Libre", 22, 80, "N"),
]

FINAL_CUENTA_FIELDS: list[tuple[str, int, int, str]] = [
    ("Clave de la Entidad", 3, 6, "N"),
    ("Clave de Oficina", 7, 10, "N"),
    ("Nº de cuenta", 11, 20, "N"),
    ("Nº apuntes Debe", 21, 25, "N"),
    ("Total importes Debe", 26, 39, "D"),
    ("Nº apuntes Haber", 40, 44, "N"),
    ("Total importes Haber", 45, 58, "D"),
    ("Código Saldo final", 59, 59, "N"),
    ("Saldo final", 60, 73, "D"),
    ("Clave de Divisa", 74, 76, "N"),
    ("Libre", 77, 80, "A"),
]

FINAL_FICHERO_FIELDS: list[tuple[str, int, int, str]] = [
    ("Nueves", 3, 20, "N"),
    ("Nº de registros", 21, 26, "I"),
    ("Libre", 27, 80, "A"),
]

FIELD_SETS: dict[str, list[tuple[str, int, int, str]]] = {
    RECORD_CABECERA: CABECERA_FIELDS,
    RECORD_MOVIMIENTO: MOVIMIENTO_FIELDS,
    RECORD_COMPLEMENTARIO_CONCEPTO: COMPLEMENTARIO_CONCEPTO_FIELDS,
    RECORD_COMPLEMENTARIO_IMPORTE: COMPLEMENTARIO_IMPORTE_FIELDS,
    RECORD_FINAL_CUENTA: FINAL_CUENTA_FIELDS,
    RECORD_FINAL_FICHERO: FINAL_FICHERO_FIELDS,
}


# ---------------------------------------------------------------------------
# Field value converters
# ---------------------------------------------------------------------------

def _convert_field(raw: str, fmt: str) -> Any:
    """Convert a raw field string according to its format."""
    raw = raw.strip()
    if not raw:
        return raw if fmt == "A" else 0

    if fmt == "A":
        return raw
    if fmt == "N":
        return raw.replace(" ", "").strip()
    if fmt == "D":
        cleaned = raw.replace(" ", "").strip()
        if not cleaned:
            return 0
        return int(cleaned) / 100
    if fmt == "I":
        cleaned = raw.replace(" ", "").strip()
        if not cleaned:
            return 0
        return int(cleaned)
    if fmt == "F":
        # Date format YYMMDD -> YYYY-MM-DD
        cleaned = raw.replace(" ", "").strip()
        if len(cleaned) >= 6:
            yy = cleaned[0:2]
            mm = cleaned[2:4]
            dd = cleaned[4:6]
            return f"20{yy}-{mm}-{dd}"
        return raw
    return raw


def _extract_field(line: str, from_pos: int, to_pos: int, fmt: str) -> Any:
    """Extract and convert a fixed-width field from a line (1-based positions)."""
    raw = line[from_pos - 1 : to_pos]
    return _convert_field(raw, fmt)


# ---------------------------------------------------------------------------
# Record parsing
# ---------------------------------------------------------------------------

@dataclass
class Record:
    """A single N43 record line."""
    record_type_code: str
    record_type_name: str
    fields: dict[str, Any]
    raw_line: str


def _parse_record(line: str) -> Record | None:
    """Parse a single N43 record line into a Record object."""
    line = line.rstrip("\r\n")
    if not line:
        return None
    if len(line) < 80:
        line = line.ljust(80)

    code = line[0:2]
    type_name = RECORD_TYPE_NAMES.get(code)
    if not type_name:
        return None

    fields_def = FIELD_SETS.get(code)
    if not fields_def:
        return None

    fields: dict[str, Any] = {}
    for name, from_p, to_p, fmt in fields_def:
        fields[name] = _extract_field(line, from_p, to_p, fmt)

    return Record(
        record_type_code=code,
        record_type_name=type_name,
        fields=fields,
        raw_line=line,
    )


# ---------------------------------------------------------------------------
# IBAN construction
# ---------------------------------------------------------------------------

def _build_iban(
    bank_id: str,
    branch_id: str,
    control_digits: str,
    account_id: str,
    country: str = "ES",
) -> str:
    """Build an ES IBAN from N43 account components."""
    acc = f"{country}{control_digits}{bank_id}{branch_id}{account_id}"
    mod97 = _iban_mod97(acc)
    check = f"{(98 - mod97):02d}"
    return f"{country}{check}{bank_id}{branch_id}{control_digits}{account_id}"


def _iban_mod97(iban: str) -> int:
    """Mod-97 check for IBAN validation."""
    # Move first 4 chars to end
    rearranged = iban[4:] + iban[:4]
    # Replace letters (A=10, B=11, ...)
    digits = ""
    for ch in rearranged.upper():
        if ch.isdigit():
            digits += ch
        else:
            digits += str(ord(ch) - ord("A") + 10)
    return int(digits) % 97


def _compute_control_digits(bank_branch: str, account: str) -> str:
    """Compute the two control digits for an ES account (N43 style).

    bank_branch: combined 8-char key (4 entity + 4 branch).
    account: 10-char account number.
    """
    factors1 = [4, 8, 5, 10, 9, 7, 3, 6]
    key = bank_branch.ljust(8, "0")[:8]
    sum1 = sum(int(key[i]) * factors1[i] for i in range(8))
    ctrl1 = 11 - (sum1 % 11)

    factors2 = [1, 2, 4, 8, 5, 10, 9, 7, 3, 6]
    account_padded = account.ljust(10, "0")[:10]
    sum2 = sum(int(account_padded[i]) * factors2[i] for i in range(10))
    ctrl2 = 11 - (sum2 % 11)

    return str(ctrl1 % 10) + str(ctrl2 % 10)


def _apply_balance_sign(amount: float, debe_haber: Any) -> float:
    """Apply N43 debit/credit sign convention to balances."""
    code = str(debe_haber).strip()
    return -amount if code == "1" else amount


# ---------------------------------------------------------------------------
# Account header / end parsing
# ---------------------------------------------------------------------------

@dataclass
class AccountHeader:
    """Parsed account header from a 11/33 pair."""
    iban: str
    bank_id: str
    branch_id: str
    account_number: str
    currency: str
    balance_start: float
    balance_end: float
    balance_variation: float
    fecha_inicial: str
    fecha_final: str
    cliente_nombre: str
    debe_count: int = 0
    debe_total: float = 0.0
    haber_count: int = 0
    haber_total: float = 0.0


def _parse_account_header(header_rec: Record, end_rec: Record) -> AccountHeader:
    """Build an AccountHeader from CabeceraDeCuenta + FinalDeCuenta."""
    h = header_rec.fields
    e = end_rec.fields

    bank = h["Clave de la Entidad"].strip()
    branch = h["Clave de Oficina"].strip()
    account = h["Nº de cuenta"].strip()
    ctrl = _compute_control_digits(bank + branch, account)

    iban = _build_iban(bank, branch, ctrl, account)

    currency_code = h.get("Clave de divisa", "978")
    if isinstance(currency_code, str):
        currency_code = currency_code.strip()
    currency = CURRENCY_CODES.get(currency_code.strip(), "EUR")

    saldo_inicial = _apply_balance_sign(float(h.get("Importe saldo inicial", 0)), h.get("Clave Debe o Haber", "2"))
    saldo_final = _apply_balance_sign(float(e.get("Saldo final", 0)), e.get("Código Saldo final", "2"))

    return AccountHeader(
        iban=iban,
        bank_id=bank,
        branch_id=branch,
        account_number=account,
        currency=currency,
        balance_start=saldo_inicial,
        balance_end=saldo_final,
        balance_variation=round(saldo_final - saldo_inicial, 2),
        fecha_inicial=str(h.get("Fecha inicial", "")),
        fecha_final=str(h.get("Fecha final", "")),
        cliente_nombre=str(h.get("Nombre abreviado", "")).strip(),
        debe_count=int(e.get("Nº apuntes Debe", 0)),
        debe_total=float(e.get("Total importes Debe", 0)),
        haber_count=int(e.get("Nº apuntes Haber", 0)),
        haber_total=float(e.get("Total importes Haber", 0)),
    )


# ---------------------------------------------------------------------------
# Transaction parsing
# ---------------------------------------------------------------------------

@dataclass
class N43Transaction:
    """A single parsed N43 transaction."""
    order: int
    booking_date: str
    value_date: str
    amount: float
    currency: str
    concept_common: str
    concept_own: str
    remittance: str
    document_number: str
    reference1: str
    reference2: str
    balance: float


def _parse_transactions(
    records: list[Record],
    headers: list[Record],
    ends: list[Record],
    currency: str,
    order_type: int,
) -> list[N43Transaction]:
    """Extract transactions from N43 records for a single account."""
    transactions: list[N43Transaction] = []

    # Gather movements and their supplements
    movements: list[Record] = []
    current: Record | None = None

    for rec in records:
        if rec.record_type_code == RECORD_MOVIMIENTO:
            if current is not None:
                movements.append(current)
            current = rec
        elif rec.record_type_code == RECORD_COMPLEMENTARIO_CONCEPTO and current is not None:
            # Append extra concept fields
            if not hasattr(current, "_extra_concepts"):
                current._extra_concepts: list[str] = []
            c1 = str(rec.fields.get("Concepto 1", "")).strip()
            c2 = str(rec.fields.get("Concepto 2", "")).strip()
            combined = f"{c1}{c2}".strip()
            if combined:
                current._extra_concepts.append(combined)
        elif rec.record_type_code == RECORD_COMPLEMENTARIO_IMPORTE:
            # Store for reference (foreign currency info)
            if not hasattr(current, "_extra_amount"):
                current._extra_amount: dict[str, Any] = {}
            current._extra_amount["divisa"] = str(rec.fields.get("Clave divisa origen del movimiento", "")).strip()
            current._extra_amount["importe"] = rec.fields.get("Importe", 0)
        else:
            if current is not None:
                movements.append(current)
                current = None

    if current is not None:
        movements.append(current)

    # Build transactions
    for idx, mov in enumerate(movements):
        f = mov.fields
        debe_haber = f.get("Clave Debe o Haber", "2")
        if isinstance(debe_haber, str):
            debe_haber = debe_haber.strip()
        mult = -1 if debe_haber == "1" else 1

        amount_raw = f.get("Importe", 0)
        if isinstance(amount_raw, str):
            amount_raw = int(amount_raw) / 100
        amount = mult * amount_raw

        # Build remittance
        concepto_comun = str(f.get("Concepto común", "")).strip()
        concepto_propio = str(f.get("Concepto propio", "")).strip()
        concept_label = ""
        if concepto_propio and concepto_propio in COMMON_CONCEPTS:
            concept_label = COMMON_CONCEPTS[concepto_propio]
        elif concepto_comun:
            concept_label = COMMON_CONCEPTS.get(concepto_comun, concepto_comun)

        parts = [concepto_propio, concept_label]
        if hasattr(mov, "_extra_concepts"):
            parts.extend(mov._extra_concepts)

        remittance = " ".join(p for p in parts if p).strip()

        booking_date = str(f.get("Fecha operación", ""))
        value_date = str(f.get("Fecha valor", ""))
        doc_number = str(f.get("Nº de documento", "")).strip()
        ref1 = str(f.get("Referencia 1", "")).strip()
        ref2 = str(f.get("Referencia 2", "")).strip()

        transactions.append(N43Transaction(
            order=idx + 1,
            booking_date=booking_date,
            value_date=value_date,
            amount=amount,
            currency=currency,
            concept_common=concepto_comun,
            concept_own=concepto_propio,
            remittance=remittance,
            document_number=doc_number,
            reference1=ref1,
            reference2=ref2,
            balance=0.0,  # filled below
        ))

    # Calculate running balance
    if order_type == -1:
        transactions.reverse()

    balance = 0.0
    for i, txn in enumerate(transactions):
        balance += txn.amount
        transactions[i].balance = round(balance, 2)

    return transactions


# ---------------------------------------------------------------------------
# Order type detection
# ---------------------------------------------------------------------------

def _detect_order(movements: list[Record]) -> int:
    """Detect if transactions are ordered ascending (1) or descending (-1)."""
    if len(movements) < 2:
        return 1

    dates = []
    for m in movements:
        d = m.fields.get("Fecha operación", "")
        if isinstance(d, str):
            dates.append(d)
        else:
            dates.append(str(d))

    if len(dates) < 2:
        return 1

    # Compare first few dates
    sum_diff = 0
    for i in range(1, min(len(dates), 5)):
        sum_diff += dates[i] > dates[i - 1]
        sum_diff -= dates[i] < dates[i - 1]

    if sum_diff > 0:
        return 1
    if sum_diff < 0:
        return -1
    return 1


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

class N43File(BaseModel):
    """Result of parsing an N43 file."""
    valid: bool = True
    accounts: list[dict[str, Any]] = field(default_factory=list)
    account_count: int = 0
    raw_line_count: int = 0
    total_record_count: int = 0
    errors: list[str] = field(default_factory=list)


def parse_n43(text: str) -> N43File:
    """Parse an N43 bank statement file.

    Args:
        text: Raw text content of the N43 file.

    Returns:
        N43File with parsed accounts, transactions, and metadata.
    """
    result = N43File()
    lines = text.splitlines()
    result.raw_line_count = len(lines)

    # Parse all records
    records: list[Record] = []
    for line in lines:
        rec = _parse_record(line)
        if rec is not None:
            records.append(rec)
            result.total_record_count += 1

    # Group by account (11 ... 33 pairs)
    headers: list[Record] = [r for r in records if r.record_type_code == RECORD_CABECERA]
    ends: list[Record] = [r for r in records if r.record_type_code == RECORD_FINAL_CUENTA]

    if not headers:
        result.valid = False
        result.errors.append("No CabeceraDeCuenta (11) records found")
        return result

    for h_idx, header in enumerate(headers):
        if h_idx >= len(ends):
            result.valid = False
            result.errors.append(f"Missing FinalDeCuenta for header {h_idx}")
            break

        end = ends[h_idx]
        account_header = _parse_account_header(header, end)

        # Gather movements between this header and end
        start_idx = records.index(header)
        end_idx = records.index(end)

        account_records: list[Record] = []
        for r in records[start_idx:end_idx + 1]:
            if r.record_type_code in {
                RECORD_MOVIMIENTO,
                RECORD_COMPLEMENTARIO_CONCEPTO,
                RECORD_COMPLEMENTARIO_IMPORTE,
            }:
                account_records.append(r)

        # Detect order
        order = _detect_order(account_records)

        # Parse transactions
        transactions = _parse_transactions(
            account_records,
            headers,
            ends,
            account_header.currency,
            order,
        )

        # Build account dict
        account_data: dict[str, Any] = {
            "iban": account_header.iban,
            "bank_id": account_header.bank_id,
            "branch_id": account_header.branch_id,
            "account_number": account_header.account_number,
            "currency": account_header.currency,
            "balance_start": account_header.balance_start,
            "balance_end": account_header.balance_end,
            "balance_variation": account_header.balance_variation,
            "fecha_inicial": account_header.fecha_inicial,
            "fecha_final": account_header.fecha_final,
            "cliente_nombre": account_header.cliente_nombre,
            "debe_count": account_header.debe_count,
            "debe_total": account_header.debe_total,
            "haber_count": account_header.haber_count,
            "haber_total": account_header.haber_total,
            "transactions": [
                {
                    "order": t.order,
                    "booking_date": t.booking_date,
                    "value_date": t.value_date,
                    "amount": round(t.amount, 2),
                    "currency": t.currency,
                    "concept_common": t.concept_common,
                    "concept_own": t.concept_own,
                    "remittance": t.remittance,
                    "document_number": t.document_number,
                    "reference1": t.reference1,
                    "reference2": t.reference2,
                    "balance": t.balance,
                }
                for t in transactions
            ],
            "transactions_amount": round(sum(t.amount for t in transactions), 2),
            "transaction_count": len(transactions),
        }

        result.accounts.append(account_data)

    result.account_count = len(result.accounts)

    return result
