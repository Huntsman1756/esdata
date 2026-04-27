import json
import hashlib
import json
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from db import db_session
from pgc_data import get_pgc_marco_actual, list_pgc_aeat_references, list_pgc_cuentas, list_pgc_estados_financieros, list_pgc_normas_valoracion, list_pgc_referencias_fiscales, search_pgc_cuentas
from pgc_utils import pgc_to_csv
from schemas import PgcAeatReferencesResponse, PgcBuscarResponse, PgcCuentasResponse, PgcEstadosFinancierosResponse, PgcNormasValoracionResponse, PgcReferenciasFiscalesResponse

router = APIRouter(prefix="/v1/pgc", tags=["pgc"])


def _pgc_json(data: dict, request: Request) -> Response:
    """Build JSON response with ETag and optional 304."""
    # Compute ETag from data WITHOUT _etag key to avoid circularity
    clean = {k: v for k, v in data.items() if k != "_etag"}
    payload = json.dumps(clean, sort_keys=True, default=str)
    etag = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    
    if_match = request.headers.get("if-none-match", "").strip('"')
    if if_match == etag:
        return Response(status_code=304)
    
    resp = JSONResponse(content=clean)
    resp.headers["ETag"] = f'"{etag}"'
    return resp


def _pgc_csv(data: list[dict], request: Request, filename: str) -> Response:
    """Build CSV response with ETag and optional 304."""
    csv_body = pgc_to_csv(data)
    etag = hashlib.sha256(json.dumps({"data": data}, sort_keys=True, default=str).encode()).hexdigest()[:16]
    
    if_match = request.headers.get("if-none-match", "").strip('"')
    if if_match == etag:
        return Response(status_code=304)
    
    resp = Response(content=csv_body, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})
    resp.headers["ETag"] = f'"{etag}"'
    return resp


@router.get("/cuentas", operation_id="list_pgc_cuentas", response_model=PgcCuentasResponse)
async def list_pgc_cuentas_endpoint(
    request: Request,
    codigo: str | None = Query(None, description="Filtrar por codigo exacto"),
    q: str | None = Query(None, description="Buscar por codigo o descripcion"),
    tipo: str | None = Query(None, description="Filtrar por tipo de cuenta"),
    nivel: int | None = Query(None, description="Filtrar por nivel"),
    clase: str | None = Query(None, description="Filtrar por clase"),
    grupo: str | None = Query(None, description="Filtrar por grupo"),
    padre_codigo: str | None = Query(None, description="Filtrar por codigo padre"),
    format: str | None = Query(None, alias="format", description="Export format (csv, json)"),
):
    with db_session() as db:
        marco = get_pgc_marco_actual(db)
        cuentas = list_pgc_cuentas(
            db,
            codigo=codigo,
            q=q,
            tipo=tipo,
            nivel=nivel,
            clase=clase,
            grupo=grupo,
            padre_codigo=padre_codigo,
        )
        if format == "csv":
            return _pgc_csv(cuentas, request, "pgc_cuentas.csv")
        return _pgc_json({"marco": marco, "cuentas": cuentas}, request)


@router.get("/buscar", operation_id="search_pgc_cuentas", response_model=PgcBuscarResponse)
async def search_pgc_cuentas_endpoint(
    request: Request,
    q: str = Query(..., description="Buscar por texto libre en PGC"),
    format: str | None = Query(None, alias="format", description="Export format (csv, json)"),
):
    with db_session() as db:
        marco = get_pgc_marco_actual(db)
        resultados = search_pgc_cuentas(db, q=q)
        if format == "csv":
            return _pgc_csv(resultados, request, "pgc_buscar.csv")
        return _pgc_json({"marco": marco, "resultados": resultados}, request)


@router.get("/normas-valoracion", operation_id="list_pgc_normas_valoracion", response_model=PgcNormasValoracionResponse)
async def list_pgc_normas_valoracion_endpoint(
    request: Request,
    norma_ref: str | None = Query(None, description="Filtrar por referencia de norma"),
    cuenta_codigo: str | None = Query(None, description="Filtrar por codigo de cuenta"),
    format: str | None = Query(None, alias="format", description="Export format (csv, json)"),
):
    with db_session() as db:
        marco = get_pgc_marco_actual(db)
        normas = list_pgc_normas_valoracion(db, norma_ref=norma_ref, cuenta_codigo=cuenta_codigo)
        if format == "csv":
            return _pgc_csv(normas, request, "pgc_normas.csv")
        return _pgc_json({"marco": marco, "normas": normas}, request)


@router.get("/estados-financieros", operation_id="list_pgc_estados_financieros", response_model=PgcEstadosFinancierosResponse)
async def list_pgc_estados_financieros_endpoint(
    request: Request,
    estado: str | None = Query(None, description="Filtrar por tipo de estado (balance, pyg)"),
    tipo_presentacion: str | None = Query(None, description="Filtrar por tipo de presentacion"),
    periodo: str | None = Query(None, description="Filtrar por periodo"),
    format: str | None = Query(None, alias="format", description="Export format (csv, json)"),
):
    with db_session() as db:
        marco = get_pgc_marco_actual(db)
        estados = list_pgc_estados_financieros(db, estado=estado, tipo_presentacion=tipo_presentacion, periodo=periodo)
        if format == "csv":
            return _pgc_csv(estados, request, "pgc_estados_financieros.csv")
        return _pgc_json({"marco": marco, "estados": estados}, request)


@router.get("/referencias-fiscales", operation_id="list_pgc_referencias_fiscales", response_model=PgcReferenciasFiscalesResponse)
async def list_pgc_referencias_fiscales_endpoint(
    request: Request,
    modelo: str | None = Query(None, description="Filtrar por modelo fiscal (IRPF, IVA, IS...)"),
    cuenta_codigo: str | None = Query(None, description="Filtrar por codigo de cuenta"),
    format: str | None = Query(None, alias="format", description="Export format (csv, json)"),
):
    with db_session() as db:
        marco = get_pgc_marco_actual(db)
        referencias = list_pgc_referencias_fiscales(db, modelo=modelo, cuenta_codigo=cuenta_codigo)
        if format == "csv":
            return _pgc_csv(referencias, request, "pgc_referencias_fiscales.csv")
        return _pgc_json({"marco": marco, "referencias": referencias}, request)


@router.get("/referencias-aeat", operation_id="list_pgc_aeat_references", response_model=PgcAeatReferencesResponse)
async def list_pgc_aeat_references_endpoint(
    request: Request,
    modelo_id: int | None = Query(None, description="Filtrar por ID de modelo AEAT"),
    cuenta_codigo: str | None = Query(None, description="Filtrar por codigo de cuenta"),
    campana: str | None = Query(None, description="Filtrar por campana o ejercicio"),
    format: str | None = Query(None, alias="format", description="Export format (csv, json)"),
):
    with db_session() as db:
        marco = get_pgc_marco_actual(db)
        referencias = list_pgc_aeat_references(db, modelo_id=modelo_id, cuenta_codigo=cuenta_codigo, campana=campana)
        if format == "csv":
            return _pgc_csv(referencias, request, "pgc_referencias_aeat.csv")
        return _pgc_json({"marco": marco, "referencias": referencias}, request)
