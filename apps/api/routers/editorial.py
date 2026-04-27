from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    NotaEditorialCreate,
    NotaEditorialDetail,
    NotaEditorialListResponse,
    NotaEditorialSummary,
    NotaEditorialUpdate,
)

router = APIRouter(prefix="/v1/editorial/notas", tags=["editorial-notas"])


@router.get("", response_model=NotaEditorialListResponse, operation_id="listar_notas_editoriales")
async def listar_notas_editoriales(
    estado: str | None = Query(None, description="Filtrar por estado (borrador, vigente, revisar, obsoleto)"),
    tipo: str | None = Query(None, description="Filtrar por tipo (resumen_interno, criterio_experto, nota_operativa)"),
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
    if tipo:
        filters.append("tipo_contenido = :tipo")
        params["tipo"] = tipo
    if fuente:
        filters.append("fuente_oficial_referencia = :fuente")
        params["fuente"] = fuente
    if q:
        filters.append("LOWER(titulo) LIKE LOWER(:q)")
        params["q"] = f"%{q}%"

    where_clause = " AND ".join(filters) if filters else "1=1"

    with db_session() as db:
        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM nota_editorial_interna WHERE {where_clause}"),
            {k: v for k, v in params.items() if k != "skip" and k != "limit"},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, titulo, resumen_ejecutivo, tipo_contenido,
                       fuente_oficial_referencia, autor_id, estado,
                       fecha_creacion, fecha_revision
                FROM nota_editorial_interna
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "notas": [
                {
                    "id": str(row["id"]),
                    "titulo": row["titulo"],
                    "resumen_ejecutivo": row["resumen_ejecutivo"],
                    "tipo_contenido": row["tipo_contenido"],
                    "fuente_oficial_referencia": row["fuente_oficial_referencia"],
                    "autor_id": row["autor_id"],
                    "estado": row["estado"],
                    "fecha_creacion": str(row["fecha_creacion"]) if row["fecha_creacion"] else None,
                    "fecha_revision": str(row["fecha_revision"]) if row["fecha_revision"] else None,
                }
                for row in rows
            ],
            "total": count_rows,
        }


@router.get("/{nota_id}", response_model=NotaEditorialDetail, operation_id="get_nota_editorial")
async def get_nota_editorial(nota_id: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, titulo, resumen_ejecutivo, contexto, impacto_practico,
                       advertencias, fuente_oficial_referencia, documento_origen_id,
                       autor_id, revisor_id, estado, tipo_contenido,
                       fecha_creacion, fecha_revision, created_at, updated_at
                FROM nota_editorial_interna
                WHERE id = :nota_id
                LIMIT 1
                """
            ),
            {"nota_id": nota_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Nota editorial no encontrada"})

        return {
            "id": str(row["id"]),
            "titulo": row["titulo"],
            "resumen_ejecutivo": row["resumen_ejecutivo"],
            "contexto": row["contexto"],
            "impacto_practico": row["impacto_practico"],
            "advertencias": row["advertencias"],
            "fuente_oficial_referencia": row["fuente_oficial_referencia"],
            "documento_origen_id": str(row["documento_origen_id"]) if row["documento_origen_id"] else None,
            "autor_id": row["autor_id"],
            "revisor_id": row["revisor_id"],
            "estado": row["estado"],
            "tipo_contenido": row["tipo_contenido"],
            "fecha_creacion": str(row["fecha_creacion"]) if row["fecha_creacion"] else None,
            "fecha_revision": str(row["fecha_revision"]) if row["fecha_revision"] else None,
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        }


@router.post("", response_model=NotaEditorialDetail, operation_id="crear_nota_editorial")
async def crear_nota_editorial(body: NotaEditorialCreate):
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

        result = db.execute(
            text(
                """
                INSERT INTO nota_editorial_interna (
                    titulo, resumen_ejecutivo, contexto, impacto_practico,
                    advertencias, fuente_oficial_referencia, documento_origen_id,
                    autor_id, revisor_id, estado, tipo_contenido, fecha_revision
                ) VALUES (
                    :titulo, :resumen_ejecutivo, :contexto, :impacto_practico,
                    :advertencias, :fuente_oficial_referencia, :documento_origen_id,
                    :autor_id, :revisor_id, :estado, :tipo_contenido, :fecha_revision
                )
                RETURNING id, titulo, resumen_ejecutivo, contexto, impacto_practico,
                          advertencias, fuente_oficial_referencia, documento_origen_id,
                          autor_id, revisor_id, estado, tipo_contenido,
                          fecha_creacion, fecha_revision, created_at, updated_at
                """
            ),
            {
                "titulo": body.titulo,
                "resumen_ejecutivo": body.resumen_ejecutivo,
                "contexto": body.contexto,
                "impacto_practico": body.impacto_practico,
                "advertencias": body.advertencias,
                "fuente_oficial_referencia": body.fuente_oficial_referencia,
                "documento_origen_id": doc_origen_id,
                "autor_id": body.autor_id,
                "revisor_id": body.revisor_id,
                "estado": body.estado,
                "tipo_contenido": body.tipo_contenido,
                "fecha_revision": body.fecha_revision,
            },
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "titulo": result["titulo"],
            "resumen_ejecutivo": result["resumen_ejecutivo"],
            "contexto": result["contexto"],
            "impacto_practico": result["impacto_practico"],
            "advertencias": result["advertencias"],
            "fuente_oficial_referencia": result["fuente_oficial_referencia"],
            "documento_origen_id": str(result["documento_origen_id"]) if result["documento_origen_id"] else None,
            "autor_id": result["autor_id"],
            "revisor_id": result["revisor_id"],
            "estado": result["estado"],
            "tipo_contenido": result["tipo_contenido"],
            "fecha_creacion": str(result["fecha_creacion"]) if result["fecha_creacion"] else None,
            "fecha_revision": str(result["fecha_revision"]) if result["fecha_revision"] else None,
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }


@router.patch("/{nota_id}", response_model=NotaEditorialDetail, operation_id="actualizar_nota_editorial")
async def actualizar_nota_editorial(nota_id: str, body: NotaEditorialUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM nota_editorial_interna WHERE id = :nota_id LIMIT 1"),
            {"nota_id": nota_id},
        ).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Nota editorial no encontrada"})

        updates = []
        params: dict = {"nota_id": nota_id}

        for field, param_name in [
            ("titulo", "titulo"),
            ("resumen_ejecutivo", "resumen_ejecutivo"),
            ("contexto", "contexto"),
            ("impacto_practico", "impacto_practico"),
            ("advertencias", "advertencias"),
            ("fuente_oficial_referencia", "fuente_oficial_referencia"),
            ("revisor_id", "revisor_id"),
            ("estado", "estado"),
            ("tipo_contenido", "tipo_contenido"),
            ("fecha_revision", "fecha_revision"),
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
            UPDATE nota_editorial_interna
            SET {', '.join(updates)}
            WHERE id = :nota_id
            RETURNING id, titulo, resumen_ejecutivo, contexto, impacto_practico,
                      advertencias, fuente_oficial_referencia, documento_origen_id,
                      autor_id, revisor_id, estado, tipo_contenido,
                      fecha_creacion, fecha_revision, created_at, updated_at
            """
        )

        result = db.execute(query, params).mappings().first()
        db.commit()

        return {
            "id": str(result["id"]),
            "titulo": result["titulo"],
            "resumen_ejecutivo": result["resumen_ejecutivo"],
            "contexto": result["contexto"],
            "impacto_practico": result["impacto_practico"],
            "advertencias": result["advertencias"],
            "fuente_oficial_referencia": result["fuente_oficial_referencia"],
            "documento_origen_id": str(result["documento_origen_id"]) if result["documento_origen_id"] else None,
            "autor_id": result["autor_id"],
            "revisor_id": result["revisor_id"],
            "estado": result["estado"],
            "tipo_contenido": result["tipo_contenido"],
            "fecha_creacion": str(result["fecha_creacion"]) if result["fecha_creacion"] else None,
            "fecha_revision": str(result["fecha_revision"]) if result["fecha_revision"] else None,
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }
