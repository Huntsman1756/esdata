"""Screening router — sanctions, PEPs and entity resolution.

Endpoints:
    POST /v1/screening/check       — evaluate an entity against screening lists
    GET  /v1/screening/entries     — list screening entries with filters
    GET  /v1/screening/matches/{empresa_id} — get all matches for a company
"""

import json
import unicodedata

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from schemas import (
    ScreeningCheckRequest,
    ScreeningCheckResponse,
    ScreeningEntriesResponse,
    ScreeningEntry,
    ScreeningList,
    ScreeningMatch,
    ScreeningMatchesResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/screening", tags=["screening"])

UNAVAILABLE_SCREENING_CODES = {
    "EU_SANCTIONS": "EU consolidated sanctions parser is not populated yet; do not infer EU sanctions absence from OFAC-only data.",
    "SEPBLAC": "SEPBLAC list-entry parser is not populated yet; do not infer SEPBLAC absence from OFAC-only data.",
    "UN_SANCTIONS": "UN consolidated sanctions parser is not populated yet; do not infer UN sanctions absence from OFAC-only data.",
    "ES_PEPS": "Official Spanish PEP parser is not populated yet; do not infer PEP absence from OFAC-only data.",
}

UNAVAILABLE_SCREENING_TYPES = {
    "pep": "PEP screening entries are not populated from an official parser yet.",
    "watchlist": "Watchlist screening entries are not populated from an official parser yet.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Normalize a name for matching: lowercase, remove accents, special chars."""
    normalized = name.lower().strip()
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("utf-8")
    normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
    normalized = " ".join(normalized.split())
    return normalized


def _parse_json_list(value):
    """Parse a JSON list from DB or return empty list."""
    if isinstance(value, str):
        return json.loads(value)
    return value or []


def _build_match_row(row: dict) -> ScreeningMatch:
    """Convert a DB row into a ScreeningMatch dict."""
    entry_aliases = _parse_json_list(row["entry_aliases"])
    entry_categorias = _parse_json_list(row["entry_categorias"])

    return ScreeningMatch(
        id=row["id"],
        empresa_id=row["empresa_id"],
        entry=ScreeningEntry(
            id=row["entry_id"],
            entidad_id=row["entry_entidad_id"],
            nombre=row["entry_nombre"],
            tipo_entidad=row["entry_tipo_entidad"],
            pais=row["entry_pais"],
            nif=row["entry_nif"],
            fecha_nacimiento=str(row["entry_fecha_nacimiento"]) if row["entry_fecha_nacimiento"] else None,
            aliases=entry_aliases,
            categorias=entry_categorias,
            descripcion=row["entry_descripcion"],
            fecha_sancion=str(row["entry_fecha_sancion"]) if row["entry_fecha_sancion"] else None,
            fecha_baja=str(row["entry_fecha_baja"]) if row["entry_fecha_baja"] else None,
            activo=row["entry_activo"],
            lista=ScreeningList(
                id=row["list_id"],
                codigo=row["list_codigo"],
                nombre=row["list_nombre"],
                tipo=row["list_tipo"],
                organismo=row["list_organismo"],
                pais=row["list_pais"],
                url_fuente=row["list_url_fuente"],
                descripcion=row["list_descripcion"],
                actualizada=str(row["list_actualizada"]) if row["list_actualizada"] else None,
                activo=row["list_activo"],
            ),
        ),
        confianza=float(row["confianza"]),
        motivo=row["motivo"],
        match_campo=row.get("match_campo", ""),
        match_texto=row.get("match_texto"),
        revisado=row.get("revisado", False),
        revisor=row.get("revisor"),
        revisado_at=str(row["revisado_at"]) if row.get("revisado_at") else None,
        notas=row.get("notas"),
    )


# ---------------------------------------------------------------------------
# POST /v1/screening/check
# ---------------------------------------------------------------------------

@router.post("/", response_model=ScreeningCheckResponse, operation_id="screening_check")
async def screening_check(req: ScreeningCheckRequest):
    """Evaluate an entity against screening lists and return matches with scoring."""
    nombre_evaluado = (req.nombre or "").strip()
    nif_evaluado = (req.nif or "").strip().upper()

    if not nombre_evaluado and not nif_evaluado and not req.empresa_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "Se requiere nombre, nif o empresa_id"},
        )

    # Resolve empresa_id from nombre/nif if not provided
    empresa_id = req.empresa_id
    resolved_nombre = nombre_evaluado
    if not empresa_id and (nombre_evaluado or nif_evaluado):
        with db_session() as db:
            params = {}
            conditions = []
            if nombre_evaluado:
                conditions.append("LOWER(nombre) = :nombre_lower")
                params["nombre_lower"] = nombre_evaluado.lower()
            if nif_evaluado:
                conditions.append("UPPER(nif) = :nif_upper")
                params["nif_upper"] = nif_evaluado
            if conditions:
                empresa_row = db.execute(
                    text(f"SELECT id, nombre FROM empresa WHERE {' OR '.join(conditions)} LIMIT 1"),
                    params,
                ).mappings().first()
                if empresa_row:
                    empresa_id = empresa_row["id"]
                    resolved_nombre = empresa_row["nombre"]

    # Build list filter (string-formatted, not a bind param)
    list_where = ""
    list_params = {}
    if req.listas:
        placeholders = ",".join([f":list_{i}" for i in range(len(req.listas))])
        list_where = f" AND l.codigo IN ({placeholders})"
        for i, codigo in enumerate(req.listas):
            list_params[f"list_{i}"] = codigo

    normalized_nombre = _normalize_name(nombre_evaluado) if nombre_evaluado else ""

    # Fetch all active screening entries, then match in Python
    with db_session() as db:
        sql = (
            "SELECT sm.id, sm.empresa_id, se.id AS entry_id, "
            "se.entidad_id AS entry_entidad_id, se.nombre AS entry_nombre, "
            "se.tipo_entidad AS entry_tipo_entidad, se.pais AS entry_pais, "
            "se.nif AS entry_nif, se.fecha_nacimiento AS entry_fecha_nacimiento, "
            "se.aliases AS entry_aliases, se.categorias AS entry_categorias, "
            "se.descripcion AS entry_descripcion, se.fecha_sancion AS entry_fecha_sancion, "
            "se.fecha_baja AS entry_fecha_baja, se.activo AS entry_activo, "
            "se.nombre_normalizado, "
            "l.id AS list_id, l.codigo AS list_codigo, l.nombre AS list_nombre, "
            "l.tipo AS list_tipo, l.organismo AS list_organismo, l.pais AS list_pais, "
            "l.url_fuente AS list_url_fuente, l.descripcion AS list_descripcion, "
            "l.actualizada AS list_actualizada, l.activo AS list_activo "
            "FROM screening_entries se "
            "JOIN screening_lists l ON l.id = se.list_id "
            "LEFT JOIN screening_matches sm ON sm.entry_id = se.id "
            "AND (:empresa_id IS NULL OR sm.empresa_id = :empresa_id) "
            "WHERE l.activo = 1 AND se.activo = 1 "
            "AND l.tipo IN ('sanctions', 'pep', 'watchlist')"
        )
        if list_where:
            sql += list_where
        sql += " ORDER BY l.codigo, se.nombre"

        rows = list(db.execute(
            text(sql),
            {
                "empresa_id": empresa_id,
                **list_params,
            },
        ).mappings())

        # Match in Python
        matches = []
        for r in rows:
            row = dict(r)
            confianza = 0.0
            motivo = ""
            match_texto = None

            # NIF exact match
            if nif_evaluado and row["entry_nif"]:
                if row["entry_nif"].upper() == nif_evaluado:
                    confianza = 1.0
                    motivo = "nif_exacto"
                    match_texto = row["entry_nif"]
                    row["match_campo"] = "nif"

            # NIF similar (no dashes)
            elif nif_evaluado and row["entry_nif"]:
                nif_clean = row["entry_nif"].replace("-", "")
                nif_input = nif_evaluado.replace("-", "")
                if nif_clean == nif_input:
                    confianza = 0.85
                    motivo = "nif_similar"
                    match_texto = row["entry_nif"]
                    row["match_campo"] = "nif"

            # Nombre exacto
            if confianza < 0.85 and row["entry_nombre"]:
                if row["entry_nombre"].lower() == nombre_evaluado.lower():
                    confianza = 0.95
                    motivo = "nombre_exacto"
                    match_texto = row["entry_nombre"]
                    row["match_campo"] = "nombre"

            # Nombre normalizado exacto
            if confianza < 0.85 and row["entry_nombre"] and normalized_nombre:
                if (row["nombre_normalizado"] or "").lower() == normalized_nombre.lower():
                    confianza = 0.95
                    motivo = "nombre_normalizado_exacto"
                    match_texto = row["entry_nombre"]
                    row["match_campo"] = "nombre"

            # Alias exacto
            if confianza < 0.85 and normalized_nombre:
                aliases = row["entry_aliases"] or []
                for alias in aliases:
                    if _normalize_name(alias) == normalized_nombre:
                        confianza = 0.9
                        motivo = "alias_exacto"
                        match_texto = alias
                        row["match_campo"] = "alias"
                        break

            # Alias similar
            if confianza < 0.85 and normalized_nombre:
                aliases = row["entry_aliases"] or []
                for alias in aliases:
                    norm_alias = _normalize_name(alias)
                    if normalized_nombre in norm_alias or norm_alias in normalized_nombre:
                        confianza = 0.7
                        motivo = "alias_similar"
                        match_texto = alias
                        row["match_campo"] = "alias"
                        break

            # Nombre similar (contains)
            if confianza < 0.7 and normalized_nombre and row["entry_nombre"]:
                norm_entry = _normalize_name(row["entry_nombre"])
                if normalized_nombre in norm_entry or norm_entry in normalized_nombre:
                    confianza = 0.75
                    motivo = "nombre_similar"
                    match_texto = row["entry_nombre"]
                    row["match_campo"] = "nombre"

            # Nombre normalizado similar (contains)
            if confianza < 0.7 and normalized_nombre and row["entry_nombre"]:
                norm_entry = (row["nombre_normalizado"] or "").lower()
                if normalized_nombre in norm_entry or norm_entry in normalized_nombre:
                    confianza = 0.75
                    motivo = "nombre_normalizado_similar"
                    match_texto = row["entry_nombre"]
                    row["match_campo"] = "nombre"

            if confianza > 0:
                row["confianza"] = confianza
                row["motivo"] = motivo
                row["match_texto"] = match_texto
                matches.append(row)

        # Sort by confidence desc, then name asc
        matches.sort(key=lambda m: (-m["confianza"] if m["confianza"] is not None else 0.0, m["entry_nombre"]))
        matches = matches[:50]

        matches = [_build_match_row(m) for m in matches]

    return ScreeningCheckResponse(
        empresa_id=empresa_id,
        nombre_evaluado=resolved_nombre or nombre_evaluado,
        nif_evaluado=nif_evaluado if nif_evaluado else None,
        matches=matches,
        sin_coincidencias=len(matches) == 0,
    )


# ---------------------------------------------------------------------------
# GET /v1/screening/entries
# ---------------------------------------------------------------------------

@router.get("/entries", response_model=ScreeningEntriesResponse, operation_id="screening_entries")
async def screening_entries(
    tipo: str | None = Query(None, description="Filtrar por tipo de lista: sanctions, pep, watchlist"),
    codigo: str | None = Query(None, description="Filtrar por codigo de lista (OFAC_SDN, EU_SANCTIONS, etc.)"),
    activo: bool | None = Query(None, description="Filtrar por estado activo"),
    q: str | None = Query(None, description="Buscar por nombre o alias"),
    limit: int = Query(50, ge=1, le=500, description="Limite de resultados"),
):
    """List screening entries with filters."""
    filters = []
    params = {}

    if tipo:
        filters.append("l.tipo = :tipo")
        params["tipo"] = tipo
    if codigo:
        filters.append("l.codigo = :codigo")
        params["codigo"] = codigo
    if activo is not None:
        filters.append("se.activo = :activo")
        params["activo"] = activo
    if q:
        q_lower = q.lower()
        filters.append(
            "(LOWER(se.nombre) LIKE :q_like OR LOWER(se.nombre_normalizado) LIKE :q_like)"
        )
        params["q_like"] = f"%{q_lower}%"

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    with db_session() as db:
        rows = list(db.execute(
            text(
                f"""
                SELECT
                    se.id,
                    se.entidad_id,
                    se.nombre,
                    se.tipo_entidad,
                    se.pais,
                    se.nif,
                    se.fecha_nacimiento,
                    se.aliases,
                    se.categorias,
                    se.descripcion,
                    se.fecha_sancion,
                    se.fecha_baja,
                    se.activo,
                    se.metadata_json,
                    l.id AS list_id,
                    l.codigo AS list_codigo,
                    l.nombre AS list_nombre,
                    l.tipo AS list_tipo,
                    l.organismo AS list_organismo,
                    l.pais AS list_pais,
                    l.url_fuente AS list_url_fuente,
                    l.descripcion AS list_descripcion,
                    l.actualizada AS list_actualizada,
                    l.activo AS list_activo
                FROM screening_entries se
                JOIN screening_lists l ON l.id = se.list_id
                {where_clause}
                ORDER BY l.codigo, se.nombre
                LIMIT :limit
                """
            ),
            {**params, "limit": limit},
        ).mappings())

        entries = []
        for row in rows:
            aliases_raw = row["aliases"]
            categorias_raw = row["categorias"]
            aliases = json.loads(aliases_raw) if isinstance(aliases_raw, str) else (aliases_raw or [])
            categorias = json.loads(categorias_raw) if isinstance(categorias_raw, str) else (categorias_raw or [])

            entries.append(ScreeningEntry(
                id=row["id"],
                entidad_id=row["entidad_id"],
                nombre=row["nombre"],
                tipo_entidad=row["tipo_entidad"],
                pais=row["pais"],
                nif=row["nif"],
                fecha_nacimiento=str(row["fecha_nacimiento"]) if row["fecha_nacimiento"] else None,
                aliases=aliases,
                categorias=categorias,
                descripcion=row["descripcion"],
                fecha_sancion=str(row["fecha_sancion"]) if row["fecha_sancion"] else None,
                fecha_baja=str(row["fecha_baja"]) if row["fecha_baja"] else None,
                activo=row["activo"],
                lista=ScreeningList(
                    id=row["list_id"],
                    codigo=row["list_codigo"],
                    nombre=row["list_nombre"],
                    tipo=row["list_tipo"],
                    organismo=row["list_organismo"],
                    pais=row["list_pais"],
                    url_fuente=row["list_url_fuente"],
                    descripcion=row["list_descripcion"],
                    actualizada=str(row["list_actualizada"]) if row["list_actualizada"] else None,
                    activo=row["list_activo"],
                ),
            ))

        total = db.execute(
            text(f"SELECT COUNT(*) FROM screening_entries se JOIN screening_lists l ON l.id = se.list_id {where_clause}"),
            params,
        ).scalar()

    requested_code = codigo.upper() if codigo else None
    if total == 0 and requested_code in UNAVAILABLE_SCREENING_CODES:
        return JSONResponse(
            status_code=200,
            content={
                "status": "configured_but_unavailable",
                "availability_status": "configured_but_unavailable",
                "safe_to_answer": False,
                "domain": "Screening/Sanctions",
                "table": "screening_entries",
                "codigo": requested_code,
                "reason": UNAVAILABLE_SCREENING_CODES[requested_code],
                "entries": [],
                "total": 0,
                "limit": limit,
            },
        )

    requested_type = tipo.lower() if tipo else None
    if total == 0 and requested_type in UNAVAILABLE_SCREENING_TYPES:
        return JSONResponse(
            status_code=200,
            content={
                "status": "configured_but_unavailable",
                "availability_status": "configured_but_unavailable",
                "safe_to_answer": False,
                "domain": "Screening/Sanctions",
                "table": "screening_entries",
                "tipo": requested_type,
                "reason": UNAVAILABLE_SCREENING_TYPES[requested_type],
                "entries": [],
                "total": 0,
                "limit": limit,
            },
        )

    return ScreeningEntriesResponse(
        total=total,
        limit=limit,
        entries=entries,
        coverage_status="official_list_loaded" if entries else "workflow_empty",
        safe_to_answer=bool(entries),
    )


# ---------------------------------------------------------------------------
# GET /v1/screening/matches/{empresa_id}
# ---------------------------------------------------------------------------

@router.get("/matches/{empresa_id}", response_model=ScreeningMatchesResponse, operation_id="screening_matches")
async def screening_matches(empresa_id: int):
    """Get all screening matches for a company."""
    with db_session() as db:
        empresa = db.execute(
            text("SELECT id, nombre FROM empresa WHERE id = :empresa_id"),
            {"empresa_id": empresa_id},
        ).mappings().first()

        if not empresa:
            raise HTTPException(
                status_code=404,
                detail={"error": "Empresa no encontrada", "empresa_id": empresa_id},
            )

        rows = list(db.execute(
            text(
                """
                SELECT
                    sm.id,
                    sm.empresa_id,
                    se.id AS entry_id,
                    se.entidad_id AS entry_entidad_id,
                    se.nombre AS entry_nombre,
                    se.tipo_entidad AS entry_tipo_entidad,
                    se.pais AS entry_pais,
                    se.nif AS entry_nif,
                    se.fecha_nacimiento AS entry_fecha_nacimiento,
                    se.aliases AS entry_aliases,
                    se.categorias AS entry_categorias,
                    se.descripcion AS entry_descripcion,
                    se.fecha_sancion AS entry_fecha_sancion,
                    se.fecha_baja AS entry_fecha_baja,
                    se.activo AS entry_activo,
                    l.id AS list_id,
                    l.codigo AS list_codigo,
                    l.nombre AS list_nombre,
                    l.tipo AS list_tipo,
                    l.organismo AS list_organismo,
                    l.pais AS list_pais,
                    l.url_fuente AS list_url_fuente,
                    l.descripcion AS list_descripcion,
                    l.actualizada AS list_actualizada,
                    l.activo AS list_activo,
                    sm.confianza,
                    sm.motivo,
                    sm.match_campo,
                    sm.match_texto,
                    sm.revisado,
                    sm.revisor,
                    sm.revisado_at,
                    sm.notas
                FROM screening_matches sm
                JOIN screening_entries se ON se.id = sm.entry_id
                JOIN screening_lists l ON l.id = se.list_id
                WHERE sm.empresa_id = :empresa_id
                ORDER BY sm.confianza DESC, sm.created_at DESC
                """
            ),
            {"empresa_id": empresa_id},
        ).mappings())

        matches = [_build_match_row(dict(r)) for r in rows]

    return ScreeningMatchesResponse(
        empresa_id=empresa_id,
        nombre=empresa["nombre"],
        matches=matches,
    )
