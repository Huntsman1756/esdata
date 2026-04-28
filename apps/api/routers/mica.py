"""MiCA / crypto-asset data model endpoints.

Fase 31 — Expansion regulatoria.

Endpoints:
    GET  /v1/mica/casp                     — list CASP providers
    GET  /v1/mica/casp/{id}                — get CASP by ID
    GET  /v1/mica/crypto-assets             — list crypto assets
    GET  /v1/mica/crypto-assets/{id}        — get crypto asset by ID
    GET  /v1/mica/tokenized-assets          — list tokenized assets
    GET  /v1/mica/tokenized-assets/{id}     — get tokenized asset by ID
    GET  /v1/mica/wallet-custodians         — list wallet custodians
    GET  /v1/mica/wallet-custodians/{id}    — get wallet custodian by ID
    GET  /v1/mica/crypto-transactions       — list crypto transactions
    GET  /v1/mica/crypto-transactions/{id}  — get transaction by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    CaspDetail,
    CaspListResponse,
    CryptoAssetDetail,
    CryptoAssetListResponse,
    CryptoTransactionDetail,
    CryptoTransactionListResponse,
    TokenizedAssetDetail,
    TokenizedAssetListResponse,
    WalletCustodianDetail,
    WalletCustodianListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/mica", tags=["mica"])


# ===========================================================================
# CASP (Crypto-Asset Service Providers)
# ===========================================================================


@router.get(
    "/casp",
    response_model=CaspListResponse,
    operation_id="list_casp",
)
async def list_casp(
    status: str | None = Query(None, description="Filtrar por estado: active, suspended, revoked"),
    home_state: str | None = Query(None, description="Filtrar por estado miembro"),
    search: str | None = Query(None, description="Buscar por nombre o numero de registro"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("c.status = :status")
        params["status"] = status
    if home_state:
        filters.append("c.home_member_state = :home_state")
        params["home_state"] = home_state
    if search:
        filters.append(
            "(c.name ILIKE :search OR c.registration_number ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, name, registration_number, home_member_state,
                       passport_active, status
                FROM casp
                WHERE {" AND ".join(filters)}
                ORDER BY name
                """
            ),
            params,
        ).mappings()
        return {"casps": [dict(r) for r in rows]}


@router.get(
    "/casp/{item_id}",
    response_model=CaspDetail,
    operation_id="get_casp",
)
async def get_casp(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, name, registration_number, home_member_state,
                       passport_active, services_offered, status, created_at
                FROM casp
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "CASP no encontrado"})
        return dict(row)


# ===========================================================================
# Crypto Assets
# ===========================================================================


@router.get(
    "/crypto-assets",
    response_model=CryptoAssetListResponse,
    operation_id="list_crypto_assets",
)
async def list_crypto_assets(
    asset_type: str | None = Query(None, description="Filtrar por tipo: e-money_token, asset_referenced_token, utility_token, other"),
    is_sha: bool | None = Query(None, description="Filtrar por SHA (significant crypto-asset)"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive, delisted"),
    search: str | None = Query(None, description="Buscar por reference_uid o issuer_jurisdiction"),
):
    filters = ["1=1"]
    params: dict = {}

    if asset_type:
        filters.append("ca.asset_type = :asset_type")
        params["asset_type"] = asset_type
    if is_sha is not None:
        filters.append("ca.is_sha = :is_sha")
        params["is_sha"] = is_sha
    if status:
        filters.append("ca.status = :status")
        params["status"] = status
    if search:
        filters.append(
            "(ca.reference_uid ILIKE :search OR ca.issuer_jurisdiction ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, asset_type, reference_uid, issuer_jurisdiction,
                       is_sha, market_value_eur, holders_count, status
                FROM crypto_asset
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        return {"assets": [dict(r) for r in rows]}


@router.get(
    "/crypto-assets/{item_id}",
    response_model=CryptoAssetDetail,
    operation_id="get_crypto_asset",
)
async def get_crypto_asset(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, asset_type, reference_uid, issuer_jurisdiction,
                       is_sha, market_value_eur, holders_count, status, created_at
                FROM crypto_asset
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Crypto asset no encontrado"})
        return dict(row)


# ===========================================================================
# Tokenized Assets
# ===========================================================================


@router.get(
    "/tokenized-assets",
    response_model=TokenizedAssetListResponse,
    operation_id="list_tokenized_assets",
)
async def list_tokenized_assets(
    underlying_type: str | None = Query(None, description="Filtrar por tipo de activo subyacente"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive, delisted"),
):
    filters = ["1=1"]
    params: dict = {}

    if underlying_type:
        filters.append("ta.underlying_type = :underlying_type")
        params["underlying_type"] = underlying_type
    if status:
        filters.append("ta.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, underlying_type, face_value, total_amount,
                       listing_date, regulated_market, status
                FROM tokenized_asset
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        return {"assets": [dict(r) for r in rows]}


@router.get(
    "/tokenized-assets/{item_id}",
    response_model=TokenizedAssetDetail,
    operation_id="get_tokenized_asset",
)
async def get_tokenized_asset(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, issuer_id, underlying_type, face_value, total_amount,
                       listing_date, regulated_market, status, created_at
                FROM tokenized_asset
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Tokenized asset no encontrado"})
        return dict(row)


# ===========================================================================
# Wallet Custodians
# ===========================================================================


@router.get(
    "/wallet-custodians",
    response_model=WalletCustodianListResponse,
    operation_id="list_wallet_custodians",
)
async def list_wallet_custodians(
    wallet_type: str | None = Query(None, description="Filtrar por tipo: hot, cold, hybrid"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive, suspended"),
):
    filters = ["1=1"]
    params: dict = {}

    if wallet_type:
        filters.append("wc.wallet_type = :wallet_type")
        params["wallet_type"] = wallet_type
    if status:
        filters.append("wc.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, wallet_type, custody_mechanism,
                       insurance_coverage, audit_frequency, status, created_at
                FROM wallet_custodian
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        return {"custodians": [dict(r) for r in rows]}


@router.get(
    "/wallet-custodians/{item_id}",
    response_model=WalletCustodianDetail,
    operation_id="get_wallet_custodian",
)
async def get_wallet_custodian(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, wallet_type, custody_mechanism,
                       insurance_coverage, audit_frequency, status, created_at
                FROM wallet_custodian
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Wallet custodian no encontrado"})
        return dict(row)


# ===========================================================================
# Crypto Transactions (DAC8/DAC9)
# ===========================================================================


@router.get(
    "/crypto-transactions",
    response_model=CryptoTransactionListResponse,
    operation_id="list_crypto_transactions",
)
async def list_crypto_transactions(
    asset_type: str | None = Query(None, description="Filtrar por tipo de activo"),
    reporting_period: str | None = Query(None, description="Filtrar por periodo de reporte (YYYY-MM)"),
    sender_wallet: str | None = Query(None, description="Filtrar por wallet del remitente"),
    receiver_wallet: str | None = Query(None, description="Filtrar por wallet del destinatario"),
):
    filters = ["1=1"]
    params: dict = {}

    if asset_type:
        filters.append("ct.asset_type = :asset_type")
        params["asset_type"] = asset_type
    if reporting_period:
        filters.append("ct.reporting_period = :reporting_period")
        params["reporting_period"] = reporting_period
    if sender_wallet:
        filters.append("ct.sender_wallet ILIKE :sender_wallet")
        params["sender_wallet"] = f"%{sender_wallet}%"
    if receiver_wallet:
        filters.append("ct.receiver_wallet ILIKE :receiver_wallet")
        params["receiver_wallet"] = f"%{receiver_wallet}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, sender_wallet, receiver_wallet, asset_type,
                       amount, value_eur, reporting_period
                FROM crypto_transaction
                WHERE {" AND ".join(filters)}
                ORDER BY timestamp DESC NULLS LAST
                """
            ),
            params,
        ).mappings()
        return {"transactions": [dict(r) for r in rows]}


@router.get(
    "/crypto-transactions/{item_id}",
    response_model=CryptoTransactionDetail,
    operation_id="get_crypto_transaction",
)
async def get_crypto_transaction(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, sender_wallet, receiver_wallet, sender_jurisdiction,
                       receiver_jurisdiction, asset_type, amount, value_eur,
                       timestamp, reporting_period, created_at
                FROM crypto_transaction
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Crypto transaction no encontrada"},
            )
        return dict(row)
