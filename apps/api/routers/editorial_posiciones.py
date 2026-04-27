from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    PosicionInterpretativaCreate,
    PosicionInterpretativaDetail,
    PosicionInterpretativaListResponse,
    PosicionInterpretativaSummary,
    PosicionInterpretativaUpdate,
)

router = APIRouter(prefix="/v1/editorial/posiciones", tags=["editorial-posiciones"])


@router.get("", response_model=PosicionInterpretativaListResponse, operation_id="listar_posiciones_interpretativas")
async def listar_posiciones_interpretativas(
    estado: str | None = Query(None, description="Filtrar por estado (borrador, vigente, revisar, obsoleto)"),
    fuente: str | None = Query(None, description="Filtrar por referencia de fuente oficial"),
    q: str | None = Query(None, description="Buscar por titulo"),
    skip: int = Query(0, ge=0, description="Offset de paginacion"),
    limit: int = Query(20, ge=1, le=100, description="Numero de resultados (max 100)"),
):
    filters = []
    params: dict = {"skip": skip, "limit": limit}

    if estado:
        filters.append("estado = :estado")
        params["estado"] = estado
    if fuente:
        filters.append("fuente_oficial_referencia = :fuente")
        params["fuente"] = fuente
    if q:
        filters.append("LOWER(titulo) LIKE LOWER(:q)")
        params["q"] = f"%{q}%"

    where_clause = " AND ".join(filters) if filters else "1=1"

    with db_session() as db:
        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM posicion_interpretativa WHERE {where_clause}"),
            {k: v for k, v in params.items() if k != "skip" and k != "limit"},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, titulo, descripcion, fuente_oficial_referencia,
                       autor_id, revisor_id, estado, version,
                       vigencia_desde, vigencia_hasta
                FROM posicion_interpretativa
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "posiciones": [
                {
                    "id": str(row["id"]),
                    "titulo": row["titulo"],
                    "descripcion": row["descripcion"],
                    "fuente_oficial_referencia": row["fuente_oficial_referencia"],
                    "autor_id": row["autor_id"],
                    "revisor_id": row["revisor_id"],
                    "estado": row["estado"],
                    "version": row["version"],
                    "vigencia_desde": str(row["vigencia_desde"]) if row["vigencia_desde"] else None,
                    "vigencia_hasta": str(row["vigencia_hasta"]) if row["vigencia_hasta"] else None,
                }
                for row in rows
            ],
            "total": count_rows,
        }


@router.get("/{posicion_id}", response_model=PosicionInterpretativaDetail, operation_id="get_posicion_interpretativa")
async def get_posicion_interpretativa(posicion_id: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, titulo, descripcion, contenido, fuente_oficial_referencia,
                       documento_origen_id, autor_id, revisor_id, estado, version,
                       vigencia_desde, vigencia_hasta, version_anterior_id,
                       fecha_creacion, fecha_revision, created_at, updated_at
                FROM posicion_interpretativa
                WHERE id = :posicion_id
                LIMIT 1
                """
            ),
            {"posicion_id": posicion_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Posicion interpretativa no encontrada"})

        return {
            "id": str(row["id"]),
            "titulo": row["titulo"],
            "descripcion": row["descripcion"],
            "contenido": row["contenido"],
            "fuente_oficial_referencia": row["fuente_oficial_referencia"],
            "documento_origen_id": str(row["documento_origen_id"]) if row["documento_origen_id"] else None,
            "autor_id": row["autor_id"],
            "revisor_id": row["revisor_id"],
            "estado": row["estado"],
            "version": row["version"],
            "vigencia_desde": str(row["vigencia_desde"]) if row["vigencia_desde"] else None,
            "vigencia_hasta": str(row["vigencia_hasta"]) if row["vigencia_hasta"] else None,
            "version_anterior_id": str(row["version_anterior_id"]) if row["version_anterior_id"] else None,
            "fecha_creacion": str(row["fecha_creacion"]) if row["fecha_creacion"] else None,
            "fecha_revision": str(row["fecha_revision"]) if row["fecha_revision"] else None,
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        }


@router.post("", response_model=PosicionInterpretativaDetail, operation_id="crear_posicion_interpretativa")
async def crear_posicion_interpretativa(body: PosicionInterpretativaCreate):
    with db_session() as db:
        doc_origen_id = None
        if body.documento_origen_referencia:
            row = db.execute(
                text(
                    """
                    SELECT id FROM documento_interpretativo
                    WHERE referencia = :referencia
                    LIMIT 1
                    """
                ),
                {"referencia": body.documento_origen_referencia},
            ).mappings().first()
            if row:
                doc_origen_id = row["id"]

        # Determine next version for the same source
        version = 1
        if doc_origen_id:
            max_ver = db.execute(
                text(
                    """
                    SELECT COALESCE(MAX(version), 0) + 1
                    FROM posicion_interpretativa
                    WHERE documento_origen_id = :doc_id
                    """
                ),
                {"doc_id": doc_origen_id},
            ).scalar()
            if max_ver:
                version = max_ver

        result = db.execute(
            text(
                """
                INSERT INTO posicion_interpretativa (
                    titulo, descripcion, contenido, fuente_oficial_referencia,
                    documento_origen_id, autor_id, revisor_id, estado, version,
                    vigencia_desde, vigencia_hasta
                ) VALUES (
                    :titulo, :descripcion, :contenido, :fuente_oficial_referencia,
                    :documento_origen_id, :autor_id, :revisor_id, :estado, :version,
                    :vigencia_desde, :vigencia_hasta
                )
                RETURNING id, titulo, descripcion, contenido, fuente_oficial_referencia,
                          documento_origen_id, autor_id, revisor_id, estado, version,
                          vigencia_desde, vigencia_hasta, version_anterior_id,
                          fecha_creacion, fecha_revision, created_at, updated_at
                """
            ),
            {
                "titulo": body.titulo,
                "descripcion": body.descripcion,
                "contenido": body.contenido,
                "fuente_oficial_referencia": body.fuente_oficial_referencia,
                "documento_origen_id": doc_origen_id,
                "autor_id": body.autor_id,
                "revisor_id": body.revisor_id,
                "estado": body.estado,
                "version": version,
                "vigencia_desde": body.vigencia_desde,
                "vigencia_hasta": body.vigencia_hasta,
            },
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "titulo": result["titulo"],
            "descripcion": result["descripcion"],
            "contenido": result["contenido"],
            "fuente_oficial_referencia": result["fuente_oficial_referencia"],
            "documento_origen_id": str(result["documento_origen_id"]) if result["documento_origen_id"] else None,
            "autor_id": result["autor_id"],
            "revisor_id": result["revisor_id"],
            "estado": result["estado"],
            "version": result["version"],
            "vigencia_desde": str(result["vigencia_desde"]) if result["vigencia_desde"] else None,
            "vigencia_hasta": str(result["vigencia_hasta"]) if result["vigencia_hasta"] else None,
            "version_anterior_id": str(result["version_anterior_id"]) if result["version_anterior_id"] else None,
            "fecha_creacion": str(result["fecha_creacion"]) if result["fecha_creacion"] else None,
            "fecha_revision": str(result["fecha_revision"]) if result["fecha_revision"] else None,
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }


@router.patch("/{posicion_id}", response_model=PosicionInterpretativaDetail, operation_id="actualizar_posicion_interpretativa")
async def actualizar_posicion_interpretativa(posicion_id: str, body: PosicionInterpretativaUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM posicion_interpretativa WHERE id = :posicion_id LIMIT 1"),
            {"posicion_id": posicion_id},
        ).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Posicion interpretativa no encontrada"})

        updates = []
        params: dict = {"posicion_id": posicion_id}

        for field, param_name in [
            ("titulo", "titulo"),
            ("descripcion", "descripcion"),
            ("contenido", "contenido"),
            ("fuente_oficial_referencia", "fuente_oficial_referencia"),
            ("revisor_id", "revisor_id"),
            ("estado", "estado"),
            ("vigencia_desde", "vigencia_desde"),
            ("vigencia_hasta", "vigencia_hasta"),
        ]:
            value = getattr(body, param_name, None)
            if value is not None:
                updates.append(f"{field} = :{param_name}")
                params[param_name] = value

        if not updates:
            raise HTTPException(status_code=400, detail={"error": "Ningun campo valido para actualizar"})

        updates.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now()

        query = text(
            f"""
            UPDATE posicion_interpretativa
            SET {', '.join(updates)}
            WHERE id = :posicion_id
            RETURNING id, titulo, descripcion, contenido, fuente_oficial_referencia,
                      documento_origen_id, autor_id, revisor_id, estado, version,
                      vigencia_desde, vigencia_hasta, version_anterior_id,
                      fecha_creacion, fecha_revision, created_at, updated_at
            """
        )

        result = db.execute(query, params).mappings().first()
        db.commit()

        return {
            "id": str(result["id"]),
            "titulo": result["titulo"],
            "descripcion": result["descripcion"],
            "contenido": result["contenido"],
            "fuente_oficial_referencia": result["fuente_oficial_referencia"],
            "documento_origen_id": str(result["documento_origen_id"]) if result["documento_origen_id"] else None,
            "autor_id": result["autor_id"],
            "revisor_id": result["revisor_id"],
            "estado": result["estado"],
            "version": result["version"],
            "vigencia_desde": str(result["vigencia_desde"]) if result["vigencia_desde"] else None,
            "vigencia_hasta": str(result["vigencia_hasta"]) if result["vigencia_hasta"] else None,
            "version_anterior_id": str(result["version_anterior_id"]) if result["version_anterior_id"] else None,
            "fecha_creacion": str(result["fecha_creacion"]) if result["fecha_creacion"] else None,
            "fecha_revision": str(result["fecha_revision"]) if result["fecha_revision"] else None,
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }
