from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    LineaCriterioCreate,
    LineaCriterioDetail,
    LineaCriterioListResponse,
    LineaCriterioReferenciaCreate,
    LineaCriterioSummary,
    LineaCriterioUpdate,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/criterio", tags=["criterio"])


@router.get("", response_model=LineaCriterioListResponse, operation_id="listar_lineas_criterio")
async def listar_lineas_criterio(
    estado: str | None = Query(None, description="Filtrar por estado (borrador, vigente, revisar, obsoleto)"),
    q: str | None = Query(None, description="Buscar por titulo o cuestion practica"),
    activo: bool | None = Query(None, description="Filtrar por estado activo/inactivo"),
    skip: int = Query(0, ge=0, description="Offset de paginacion"),
    limit: int = Query(20, ge=1, le=100, description="Numero de resultados (max 100)"),
):
    filters = []
    params: dict = {"skip": skip, "limit": limit}

    if estado:
        filters.append("estado = :estado")
        params["estado"] = estado
    if q:
        filters.append("LOWER(titulo) LIKE LOWER(:q) OR LOWER(cuestion_practica) LIKE LOWER(:q)")
        params["q"] = f"%{q}%"
    if activo is not None:
        filters.append("activo = :activo")
        params["activo"] = activo

    where_clause = " AND ".join(filters) if filters else "1=1"

    with db_session() as db:
        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM linea_criterio WHERE {where_clause}"),
            {k: v for k, v in params.items() if k != "skip" and k != "limit"},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, titulo, cuestion_practica, estado, autor_id, revisor_id,
                       ultimo_cambio, activo, created_at, updated_at
                FROM linea_criterio
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "lineas": [
                {
                    "id": int(row["id"]),
                    "titulo": row["titulo"],
                    "cuestion_practica": row["cuestion_practica"],
                    "estado": row["estado"],
                    "autor_id": int(row["autor_id"]) if row["autor_id"] is not None else None,
                    "revisor_id": int(row["revisor_id"]) if row["revisor_id"] is not None else None,
                    "ultimo_cambio": str(row["ultimo_cambio"]) if row["ultimo_cambio"] else None,
                    "activo": bool(row["activo"]),
                    "created_at": str(row["created_at"]) if row["created_at"] else None,
                    "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
                }
                for row in rows
            ],
            "total": int(count_rows),
        }


@router.get("/{linea_id}", response_model=LineaCriterioDetail, operation_id="detalle_linea_criterio")
async def obtener_linea_criterio(linea_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, titulo, cuestion_practica, descripcion, criterio_dominante,
                       matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id,
                       activo, created_at, updated_at
                FROM linea_criterio
                WHERE id = :linea_id
                """
            ),
            {"linea_id": linea_id},
        ).mappings().one_or_none()

        if not row:
            raise HTTPException(status_code=404, detail="Linea de criterio no encontrada")

        refs = db.execute(
            text(
                """
                SELECT id, linea_id, documento_referencia, tipo_documento,
                       organismo_emisor, fecha, rol_en_linea, orden, created_at
                FROM linea_criterio_referencia
                WHERE linea_id = :linea_id
                ORDER BY orden ASC
                """
            ),
            {"linea_id": linea_id},
        ).mappings()

        return {
            "id": int(row["id"]),
            "titulo": row["titulo"],
            "cuestion_practica": row["cuestion_practica"],
            "descripcion": row["descripcion"],
            "criterio_dominante": row["criterio_dominante"],
            "matices": row["matices"],
            "excepciones": row["excepciones"],
            "ultimo_cambio": str(row["ultimo_cambio"]) if row["ultimo_cambio"] else None,
            "estado": row["estado"],
            "autor_id": int(row["autor_id"]) if row["autor_id"] is not None else None,
            "revisor_id": int(row["revisor_id"]) if row["revisor_id"] is not None else None,
            "activo": bool(row["activo"]),
            "referencias": [
                {
                    "id": int(r["id"]),
                    "documento_referencia": r["documento_referencia"],
                    "tipo_documento": r["tipo_documento"],
                    "organismo_emisor": r["organismo_emisor"],
                    "fecha": str(r["fecha"]) if r["fecha"] else None,
                    "rol_en_linea": r["rol_en_linea"],
                    "orden": int(r["orden"]),
                }
                for r in refs
            ],
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        }


@router.post("", response_model=LineaCriterioSummary, status_code=201, operation_id="crear_linea_criterio")
async def crear_linea_criterio(data: LineaCriterioCreate):
    with db_session() as db:
        result = db.execute(
            text(
                """
                INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante,
                                            matices, excepciones, estado, activo)
                VALUES (:titulo, :cuestion_practica, :descripcion, :criterio_dominante,
                        :matices, :excepciones, :estado, true)
                RETURNING id
                """
            ),
            {
                "titulo": data.titulo,
                "cuestion_practica": data.cuestion_practica,
                "descripcion": data.descripcion,
                "criterio_dominante": data.criterio_dominante,
                "matices": data.matices,
                "excepciones": data.excepciones,
                "estado": data.estado or "borrador",
            },
        ).mappings().one()

        linea_id = int(result["id"])
        db.commit()

        return {
            "id": linea_id,
            "titulo": data.titulo,
            "cuestion_practica": data.cuestion_practica,
            "estado": data.estado or "borrador",
            "autor_id": None,
            "revisor_id": None,
            "ultimo_cambio": None,
            "activo": True,
            "created_at": None,
            "updated_at": None,
        }


@router.patch("/{linea_id}", response_model=LineaCriterioSummary, operation_id="actualizar_linea_criterio")
async def actualizar_linea_criterio(linea_id: int, data: LineaCriterioUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM linea_criterio WHERE id = :id"),
            {"id": linea_id},
        ).mappings().one_or_none()

        if not existing:
            raise HTTPException(status_code=404, detail="Linea de criterio no encontrada")

        updates = []
        params = {"id": linea_id}

        for field in ["titulo", "cuestion_practica", "descripcion", "criterio_dominante", "matices", "excepciones"]:
            val = getattr(data, field, None)
            if val is not None:
                updates.append(f"{field} = :{field}")
                params[field] = val

        if data.estado is not None:
            updates.append("estado = :estado")
            params["estado"] = data.estado

        if data.ultimo_cambio is not None:
            updates.append("ultimo_cambio = :ultimo_cambio")
            params["ultimo_cambio"] = data.ultimo_cambio

        if updates:
            params["updated_at"] = "now()"
            db.execute(
                text(f"""
                    UPDATE linea_criterio
                    SET {', '.join(updates)}
                    WHERE id = :id
                """),
                params,
            )
            db.commit()

        row = db.execute(
            text(
                """
                SELECT id, titulo, cuestion_practica, estado, autor_id, revisor_id,
                       ultimo_cambio, activo, created_at, updated_at
                FROM linea_criterio
                WHERE id = :id
                """
            ),
            {"id": linea_id},
        ).mappings().one()

        return {
            "id": int(row["id"]),
            "titulo": row["titulo"],
            "cuestion_practica": row["cuestion_practica"],
            "estado": row["estado"],
            "autor_id": int(row["autor_id"]) if row["autor_id"] is not None else None,
            "revisor_id": int(row["revisor_id"]) if row["revisor_id"] is not None else None,
            "ultimo_cambio": str(row["ultimo_cambio"]) if row["ultimo_cambio"] else None,
            "activo": bool(row["activo"]),
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        }


@router.get("/{linea_id}/referencias", response_model=list, operation_id="listar_referencias_linea")
async def listar_referencias_linea(linea_id: int):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM linea_criterio WHERE id = :id"),
            {"id": linea_id},
        ).mappings().one_or_none()

        if not existing:
            raise HTTPException(status_code=404, detail="Linea de criterio no encontrada")

        refs = db.execute(
            text(
                """
                SELECT id, documento_referencia, tipo_documento, organismo_emisor,
                       fecha, rol_en_linea, orden, created_at
                FROM linea_criterio_referencia
                WHERE linea_id = :linea_id
                ORDER BY orden ASC
                """
            ),
            {"linea_id": linea_id},
        ).mappings()

        return [
            {
                "id": int(r["id"]),
                "documento_referencia": r["documento_referencia"],
                "tipo_documento": r["tipo_documento"],
                "organismo_emisor": r["organismo_emisor"],
                "fecha": str(r["fecha"]) if r["fecha"] else None,
                "rol_en_linea": r["rol_en_linea"],
                "orden": int(r["orden"]),
            }
            for r in refs
        ]


@router.post("/{linea_id}/referencias", status_code=201, operation_id="anadir_referencia_linea")
async def anadir_referencia_linea(linea_id: int, data: LineaCriterioReferenciaCreate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM linea_criterio WHERE id = :id"),
            {"id": linea_id},
        ).mappings().one_or_none()

        if not existing:
            raise HTTPException(status_code=404, detail="Linea de criterio no encontrada")

        result = db.execute(
            text(
                """
                INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento,
                                                       organismo_emisor, fecha, rol_en_linea, orden)
                VALUES (:linea_id, :documento_referencia, :tipo_documento,
                        :organismo_emisor, :fecha, :rol_en_linea, :orden)
                RETURNING id
                """
            ),
            {
                "linea_id": linea_id,
                "documento_referencia": data.documento_referencia,
                "tipo_documento": data.tipo_documento,
                "organismo_emisor": data.organismo_emisor,
                "fecha": data.fecha,
                "rol_en_linea": data.rol_en_linea or "soporte",
                "orden": data.orden,
            },
        ).mappings().one()

        db.commit()
        return {"id": int(result["id"]), "status": "created"}
