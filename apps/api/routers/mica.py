"""Routers para MiCA (Reglamento UE 2023/1114) y crypto-asset services.

Endpoints de consulta de CASP (Crypto-Asset Service Providers),
activos crypto, activos tokenizados, custodios de wallets y
transacciones crypto para DAC8/DAC9.
"""

import json

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    CASPCreate as CASPCreateSchema,
)
from schemas import (
    CASPDetail as CASPDetailSchema,
)
from schemas import (
    CASPListResponse,
    CryptoAssetListResponse,
    CryptoTransactionListResponse,
    TokenizedAssetListResponse,
    WalletCustodianListResponse,
)
from schemas import (
    CASPSummary as CASPSummarySchema,
)
from schemas import (
    CASPUpdate as CASPUpdateSchema,
)
from schemas import (
    CryptoAssetCreate as CryptoAssetCreateSchema,
)
from schemas import (
    CryptoAssetDetail as CryptoAssetDetailSchema,
)
from schemas import (
    CryptoAssetSummary as CryptoAssetSummarySchema,
)
from schemas import (
    CryptoTransactionCreate as CryptoTransactionCreateSchema,
)
from schemas import (
    CryptoTransactionDetail as CryptoTransactionDetailSchema,
)
from schemas import (
    CryptoTransactionSummary as CryptoTransactionSummarySchema,
)
from schemas import (
    TokenizedAssetDetail as TokenizedAssetDetailSchema,
)
from schemas import (
    WalletCustodianDetail as WalletCustodianDetailSchema,
)
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

router = APIRouter(prefix="/v1/mica", tags=["mica"])


# ===================================================================
# Helpers
# ===================================================================


def _parse_services(val) -> list[str]:
    """Parse services_offered JSON string or list into list[str]."""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _missing_table_error(exc: OperationalError) -> bool:
    message = str(exc).lower()
    return "no such table" in message or "does not exist" in message or "undefined table" in message


def _empty_list_on_missing_table(exc: OperationalError):
    if _missing_table_error(exc):
        return {"items": [], "total": 0}
    raise exc


# ===================================================================
# CASP — Crypto-Asset Service Providers
# ===================================================================


@router.get(
    "/casp",
    operation_id="list_casp",
    response_model=CASPListResponse,
)
async def list_casp(
    status: str | None = Query(default=None, description="Filtrar por estado: active, suspended, revoked"),
    home_member_state: str | None = Query(default=None, description="Filtrar por estado miembro (ISO 3166-1 alpha-2)"),
    search: str | None = Query(default=None, description="Busqueda por nombre"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Listar proveedores de servicios de criptoactivos (CASP) del registro ESMA."""
    conditions = []
    params = {}

    if status:
        conditions.append("status = :status")
        params["status"] = status
    if home_member_state:
        conditions.append("home_member_state = :home_member_state")
        params["home_member_state"] = home_member_state
    if search:
        conditions.append("name ILIKE :search")
        params["search"] = f"%{search}%"

    with db_session() as db:
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT id, name, registration_number, home_member_state,
                           passport_active, services_offered, status
                    FROM casp
                    {where}
                    ORDER BY name
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": limit, "offset": offset},
            ).mappings()

            items = [dict(r) for r in rows]
            for item in items:
                item["services_offered"] = _parse_services(item["services_offered"])

            total = db.execute(
                text(f"SELECT COUNT(*) FROM casp {where}"),
                params,
            ).scalar_one()
        except OperationalError as exc:
            return _empty_list_on_missing_table(exc)

        return {"items": items, "total": total}


@router.get(
    "/casp/{casp_id}",
    operation_id="get_casp",
    response_model=CASPDetailSchema,
)
async def get_casp(casp_id: int):
    """Obtener detalle de un CASP por ID."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, name, registration_number, home_member_state,
                       passport_active, services_offered, status,
                       created_at, updated_at
                FROM casp
                WHERE id = :id
                """
            ),
            {"id": casp_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "CASP no encontrado"})

    result = dict(row)
    result["services_offered"] = _parse_services(result["services_offered"])
    return result


@router.post(
    "/casp",
    operation_id="create_casp",
    response_model=CASPSummarySchema,
    status_code=201,
)
async def create_casp(body: CASPCreateSchema):
    """Crear un nuevo CASP."""
    services_json = json.dumps(body.services_offered) if body.services_offered else "[]"
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO casp (name, registration_number, home_member_state,
                                  passport_active, services_offered, status)
                VALUES (:name, :registration_number, :home_member_state,
                        :passport_active, :services_json, 'active')
                """
            ),
            {
                "name": body.name,
                "registration_number": body.registration_number,
                "home_member_state": body.home_member_state,
                "passport_active": body.passport_active,
                "services_json": services_json,
            },
        )
        db.commit()

        row = db.execute(
            text(
                """
                SELECT id, name, registration_number, home_member_state,
                       passport_active, services_offered, status
                FROM casp
                ORDER BY id DESC LIMIT 1
                """
            ),
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=500, detail={"error": "Error creando CASP"})

    result = dict(row)
    result["services_offered"] = _parse_services(result["services_offered"])
    return result


@router.patch(
    "/casp/{casp_id}",
    operation_id="update_casp",
    response_model=CASPSummarySchema,
)
async def update_casp(casp_id: int, body: CASPUpdateSchema):
    """Actualizar un CASP existente."""
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM casp WHERE id = :id"),
            {"id": casp_id},
        ).scalar_one_or_none()

    if not existing:
        raise HTTPException(status_code=404, detail={"error": "CASP no encontrado"})

    with db_session() as db:
        row = db.execute(
            text("SELECT services_offered FROM casp WHERE id = :id"),
            {"id": casp_id},
        ).mappings().first()

        current_services = _parse_services(row["services_offered"]) if row else []
        new_services = body.services_offered if body.services_offered is not None else current_services
        services_json = json.dumps(new_services) if new_services else "[]"

        set_parts = []
        params = {"id": casp_id}

        if body.name is not None:
            set_parts.append("name = :name")
            params["name"] = body.name
        if body.registration_number is not None:
            set_parts.append("registration_number = :registration_number")
            params["registration_number"] = body.registration_number
        if body.home_member_state is not None:
            set_parts.append("home_member_state = :home_member_state")
            params["home_member_state"] = body.home_member_state
        if body.passport_active is not None:
            set_parts.append("passport_active = :passport_active")
            params["passport_active"] = body.passport_active
        if body.status is not None:
            set_parts.append("status = :status")
            params["status"] = body.status

        set_parts.append("services_offered = :services_json")
        params["services_json"] = services_json
        set_parts.append("updated_at = CURRENT_TIMESTAMP")

        db.execute(
            text(f"UPDATE casp SET {', '.join(set_parts)} WHERE id = :id"),
            params,
        )
        db.commit()

        row = db.execute(
            text(
                """
                SELECT id, name, registration_number, home_member_state,
                       passport_active, services_offered, status
                FROM casp
                WHERE id = :id
                """
            ),
            {"id": casp_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=500, detail={"error": "Error actualizando CASP"})

    result = dict(row)
    result["services_offered"] = _parse_services(result["services_offered"])
    return result


# ===================================================================
# Crypto Asset
# ===================================================================


@router.get(
    "/crypto-assets",
    operation_id="list_crypto_assets",
    response_model=CryptoAssetListResponse,
)
async def list_crypto_assets(
    asset_type: str | None = Query(default=None, description="asset-referenced, e-money, utility, other"),
    is_sha: bool | None = Query(default=None, description="Filtrar por criptoactivo significativo"),
    status: str | None = Query(default=None, description="Filtrar por estado"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Listar criptoactivos bajo MiCA."""
    conditions = []
    params = {}

    if asset_type:
        conditions.append("asset_type = :asset_type")
        params["asset_type"] = asset_type
    if is_sha is not None:
        conditions.append("is_sha = :is_sha")
        params["is_sha"] = is_sha
    if status:
        conditions.append("status = :status")
        params["status"] = status

    with db_session() as db:
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT id, asset_type, reference_uid, issuer_jurisdiction,
                           is_sha, market_value_eur, holders_count, status
                    FROM crypto_asset
                    {where}
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": limit, "offset": offset},
            ).mappings()

            items = [dict(r) for r in rows]

            total = db.execute(
                text(f"SELECT COUNT(*) FROM crypto_asset {where}"),
                params,
            ).scalar_one()
        except OperationalError as exc:
            return _empty_list_on_missing_table(exc)

        return {"items": items, "total": total}


@router.get(
    "/crypto-assets/{asset_id}",
    operation_id="get_crypto_asset",
    response_model=CryptoAssetDetailSchema,
)
async def get_crypto_asset(asset_id: int):
    """Obtener detalle de un criptoactivo por ID."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, asset_type, reference_uid, issuer_jurisdiction,
                       is_sha, market_value_eur, holders_count, status,
                       created_at, updated_at
                FROM crypto_asset
                WHERE id = :id
                """
            ),
            {"id": asset_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "Criptoactivo no encontrado"})

    return dict(row)


@router.post(
    "/crypto-assets",
    operation_id="create_crypto_asset",
    response_model=CryptoAssetSummarySchema,
    status_code=201,
)
async def create_crypto_asset(body: CryptoAssetCreateSchema):
    """Crear un nuevo criptoactivo."""
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction,
                                          is_sha, market_value_eur, holders_count, status)
                VALUES (:asset_type, :reference_uid, :issuer_jurisdiction,
                        :is_sha, :market_value_eur, :holders_count, 'active')
                """
            ),
            {
                "asset_type": body.asset_type,
                "reference_uid": body.reference_uid,
                "issuer_jurisdiction": body.issuer_jurisdiction,
                "is_sha": body.is_sha,
                "market_value_eur": body.market_value_eur,
                "holders_count": body.holders_count,
            },
        )
        db.commit()

        row = db.execute(
            text(
                """
                SELECT id, asset_type, reference_uid, issuer_jurisdiction,
                       is_sha, market_value_eur, holders_count, status
                FROM crypto_asset
                ORDER BY id DESC LIMIT 1
                """
            ),
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=500, detail={"error": "Error creando criptoactivo"})

    return dict(row)


# ===================================================================
# Tokenized Asset
# ===================================================================


@router.get(
    "/tokenized-assets",
    operation_id="list_tokenized_assets",
    response_model=TokenizedAssetListResponse,
)
async def list_tokenized_assets(
    underlying_type: str | None = Query(default=None, description="equity, bond, fund, real-estate, other"),
    status: str | None = Query(default=None, description="Filtrar por estado"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Listar activos tokenizados bajo MiCA."""
    conditions = []
    params = {}

    if underlying_type:
        conditions.append("underlying_type = :underlying_type")
        params["underlying_type"] = underlying_type
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    with db_session() as db:
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT id, underlying_type, issuer_id, face_value, total_amount,
                           listing_date, regulated_market, status
                    FROM tokenized_asset
                    {where}
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": limit, "offset": offset},
            ).mappings()

            items = [dict(r) for r in rows]

            total = db.execute(
                text(f"SELECT COUNT(*) FROM tokenized_asset {where}"),
                params,
            ).scalar_one()
        except OperationalError as exc:
            return _empty_list_on_missing_table(exc)

        return {"items": items, "total": total}


@router.get(
    "/tokenized-assets/{asset_id}",
    operation_id="get_tokenized_asset",
    response_model=TokenizedAssetDetailSchema,
)
async def get_tokenized_asset(asset_id: int):
    """Obtener detalle de un activo tokenizado por ID."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, underlying_type, issuer_id, face_value, total_amount,
                       listing_date, regulated_market, status,
                       created_at, updated_at
                FROM tokenized_asset
                WHERE id = :id
                """
            ),
            {"id": asset_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "Activo tokenizado no encontrado"})

    return dict(row)


# ===================================================================
# Wallet Custodian
# ===================================================================


@router.get(
    "/wallet-custodians",
    operation_id="list_wallet_custodians",
    response_model=WalletCustodianListResponse,
)
async def list_wallet_custodians(
    wallet_type: str | None = Query(default=None, description="hot, cold, hybrid"),
    status: str | None = Query(default=None, description="Filtrar por estado"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Listar proveedores de custodia de wallets."""
    conditions = []
    params = {}

    if wallet_type:
        conditions.append("wallet_type = :wallet_type")
        params["wallet_type"] = wallet_type
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    with db_session() as db:
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT id, entity_id, wallet_type, custody_mechanism,
                           insurance_coverage, audit_frequency, status
                    FROM wallet_custodian
                    {where}
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": limit, "offset": offset},
            ).mappings()

            items = [dict(r) for r in rows]

            total = db.execute(
                text(f"SELECT COUNT(*) FROM wallet_custodian {where}"),
                params,
            ).scalar_one()
        except OperationalError as exc:
            return _empty_list_on_missing_table(exc)

        return {"items": items, "total": total}


@router.get(
    "/wallet-custodians/{custodian_id}",
    operation_id="get_wallet_custodian",
    response_model=WalletCustodianDetailSchema,
)
async def get_wallet_custodian(custodian_id: int):
    """Obtener detalle de un custodio por ID."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, wallet_type, custody_mechanism,
                       insurance_coverage, audit_frequency, status,
                       created_at, updated_at
                FROM wallet_custodian
                WHERE id = :id
                """
            ),
            {"id": custodian_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "Custodio no encontrado"})

    return dict(row)


# ===================================================================
# Crypto Transaction
# ===================================================================


@router.get(
    "/transactions",
    operation_id="list_crypto_transactions",
    response_model=CryptoTransactionListResponse,
)
async def list_crypto_transactions(
    asset_type: str | None = Query(default=None, description="asset-referenced, e-money, utility, other"),
    reporting_period: str | None = Query(default=None, description="Filtrar por periodo (YYYY-MM)"),
    status: str | None = Query(default=None, description="reported, amended, rejected"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Listar transacciones crypto para DAC8/DAC9."""
    conditions = []
    params = {}

    if asset_type:
        conditions.append("asset_type = :asset_type")
        params["asset_type"] = asset_type
    if reporting_period:
        conditions.append("reporting_period = :reporting_period")
        params["reporting_period"] = reporting_period

    if status:
        conditions.append("status = :status")
        params["status"] = status

    with db_session() as db:
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT id, sender_wallet, receiver_wallet,
                           sender_jurisdiction, receiver_jurisdiction,
                           asset_type, amount, value_eur, timestamp,
                           reporting_period, status
                    FROM crypto_transaction
                    {where}
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": limit, "offset": offset},
            ).mappings()

            items = [dict(r) for r in rows]

            total = db.execute(
                text(f"SELECT COUNT(*) FROM crypto_transaction {where}"),
                params,
            ).scalar_one()
        except OperationalError as exc:
            return _empty_list_on_missing_table(exc)

        return {"items": items, "total": total}


@router.get(
    "/transactions/{transaction_id}",
    operation_id="get_crypto_transaction",
    response_model=CryptoTransactionDetailSchema,
)
async def get_crypto_transaction(transaction_id: int):
    """Obtener detalle de una transaccion crypto por ID."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, sender_wallet, receiver_wallet,
                       sender_jurisdiction, receiver_jurisdiction,
                       asset_type, amount, value_eur, timestamp,
                       reporting_period, status,
                       created_at, updated_at
                FROM crypto_transaction
                WHERE id = :id
                """
            ),
            {"id": transaction_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "Transaccion no encontrada"})

    return dict(row)


@router.post(
    "/transactions",
    operation_id="create_crypto_transaction",
    response_model=CryptoTransactionSummarySchema,
    status_code=201,
)
async def create_crypto_transaction(body: CryptoTransactionCreateSchema):
    """Crear una nueva transaccion crypto."""
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO crypto_transaction (sender_wallet, receiver_wallet,
                        sender_jurisdiction, receiver_jurisdiction,
                        asset_type, amount, value_eur, timestamp,
                        reporting_period, status)
                VALUES (:sender_wallet, :receiver_wallet,
                        :sender_jurisdiction, :receiver_jurisdiction,
                        :asset_type, :amount, :value_eur, :timestamp,
                        :reporting_period, 'reported')
                """
            ),
            {
                "sender_wallet": body.sender_wallet,
                "receiver_wallet": body.receiver_wallet,
                "sender_jurisdiction": body.sender_jurisdiction,
                "receiver_jurisdiction": body.receiver_jurisdiction,
                "asset_type": body.asset_type,
                "amount": body.amount,
                "value_eur": body.value_eur,
                "timestamp": body.timestamp,
                "reporting_period": body.reporting_period,
            },
        )
        db.commit()

        row = db.execute(
            text(
                """
                SELECT id, sender_wallet, receiver_wallet,
                       sender_jurisdiction, receiver_jurisdiction,
                       asset_type, amount, value_eur, timestamp,
                       reporting_period, status
                FROM crypto_transaction
                ORDER BY id DESC LIMIT 1
                """
            ),
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=500, detail={"error": "Error creando transaccion"})

    return dict(row)
