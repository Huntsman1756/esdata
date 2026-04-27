"""Risk-Control Matrix router — Fase 22.

Endpoints for:
- riesgo_regulatorio (CRUD + list with filters)
- control_interno (CRUD + list with filters)
- riesgo_control_link (create, list, detail with pruebas)
- prueba_control (create + list)
- control_gaps (aggregate view of missing/partial controls)
"""

from datetime import date, datetime
from uuid import uuid4

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    ControlGapsResponse,
    ControlInternoCreate,
    ControlInternoDetail,
    ControlInternoListResponse,
    ControlInternoUpdate,
    PruebaControlCreate,
    PruebaControlDetail,
    PruebaControlListResponse,
    RiesgoControlLinkCreate,
    RiesgoControlLinkDetail,
    RiesgoControlLinkListResponse,
    RiesgoRegulatorioCreate,
    RiesgoRegulatorioDetail,
    RiesgoRegulatorioListResponse,
    RiesgoRegulatorioUpdate,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/risk-control", tags=["risk-control-matrix"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_ts(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _fmt_date(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val.isoformat()
    return str(val)


# ---------------------------------------------------------------------------
# Riesgo regulatorio — list
# ---------------------------------------------------------------------------


@router.get(
    "/riesgos",
    response_model=RiesgoRegulatorioListResponse,
    operation_id="listar_riesgos",
)
async def listar_riesgos(
    estado: str | None = Query(None, description="Filtrar por estado"),
    categoria: str | None = Query(None, description="Filtrar por categoria"),
    obligacion: str | None = Query(None, description="Filtrar por codigo de obligacion"),
    severidad: str | None = Query(None, description="Filtrar por severidad"),
    q: str | None = Query(None, description="Buscar por nombre"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    filters = []
    params: dict = {"skip": skip, "limit": limit}

    if estado:
        filters.append("estado = :estado")
        params["estado"] = estado
    if categoria:
        filters.append("categoria = :categoria")
        params["categoria"] = categoria
    if obligacion:
        filters.append("obligacion_codigo = :obligacion")
        params["obligacion"] = obligacion
    if severidad:
        filters.append("severidad = :severidad")
        params["severidad"] = severidad
    if q:
        filters.append("LOWER(nombre) LIKE LOWER(:q)")
        params["q"] = f"%{q}%"

    where_clause = " AND ".join(filters) if filters else "1=1"

    with db_session() as db:
        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM riesgo_regulatorio WHERE {where_clause}"),
            {k: v for k, v in params.items() if k not in ("skip", "limit")},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, codigo, nombre, obligacion_codigo, categoria,
                       severidad, probabilidad, riesgo_inherente,
                       area_responsable, owner_rol, estado
                FROM riesgo_regulatorio
                WHERE {where_clause}
                ORDER BY
                    CASE severidad
                        WHEN 'critica' THEN 1
                        WHEN 'alta' THEN 2
                        WHEN 'media' THEN 3
                        WHEN 'baja' THEN 4
                        ELSE 5
                    END,
                    created_at DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "riesgos": [
                {
                    "id": str(r["id"]),
                    "codigo": r["codigo"],
                    "nombre": r["nombre"],
                    "obligacion_codigo": r["obligacion_codigo"],
                    "categoria": r["categoria"],
                    "severidad": r["severidad"],
                    "probabilidad": r["probabilidad"],
                    "riesgo_inherente": r["riesgo_inherente"],
                    "area_responsable": r["area_responsable"],
                    "owner_rol": r["owner_rol"],
                    "estado": r["estado"],
                }
                for r in rows
            ],
            "total": count_rows,
        }


# ---------------------------------------------------------------------------
# Riesgo regulatorio — detail
# ---------------------------------------------------------------------------


@router.get(
    "/riesgos/{riesgo_id}",
    response_model=RiesgoRegulatorioDetail,
    operation_id="get_riesgo",
)
async def get_riesgo(riesgo_id: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, nombre, descripcion, obligacion_codigo,
                       categoria, severidad, probabilidad, riesgo_inherente,
                       area_responsable, owner_rol, estado, created_at, updated_at
                FROM riesgo_regulatorio
                WHERE id = :rid
                LIMIT 1
                """
            ),
            {"rid": riesgo_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Riesgo regulatorio no encontrado"})

        # Fetch risk -> control links + control details
        links = db.execute(
            text(
                """
                SELECT rcl.id, rcl.efectividad, rcl.riesgo_residual,
                       rcl.frecuencia_prueba, rcl.criterio_suficiencia,
                       rcl.caducidad_dias, rcl.activo,
                       ci.codigo AS control_codigo, ci.nombre AS control_nombre
                FROM riesgo_control_link rcl
                JOIN control_interno ci ON ci.id = rcl.control_id
                WHERE rcl.riesgo_id = :rid AND rcl.activo = true
                """
            ),
            {"rid": riesgo_id},
        ).mappings()

        controles = [
            {
                "id": str(lnk["id"]),
                "control_codigo": lnk["control_codigo"],
                "control_nombre": lnk["control_nombre"],
                "efectividad": lnk["efectividad"],
                "riesgo_residual": lnk["riesgo_residual"],
                "frecuencia_prueba": lnk["frecuencia_prueba"],
                "criterio_suficiencia": lnk["criterio_suficiencia"],
                "caducidad_dias": lnk["caducidad_dias"],
                "activo": lnk["activo"],
            }
            for lnk in links
        ]

        return {
            "id": str(row["id"]),
            "codigo": row["codigo"],
            "nombre": row["nombre"],
            "descripcion": row["descripcion"],
            "obligacion_codigo": row["obligacion_codigo"],
            "categoria": row["categoria"],
            "severidad": row["severidad"],
            "probabilidad": row["probabilidad"],
            "riesgo_inherente": row["riesgo_inherente"],
            "area_responsable": row["area_responsable"],
            "owner_rol": row["owner_rol"],
            "estado": row["estado"],
            "controles": controles,
            "created_at": _fmt_ts(row["created_at"]),
            "updated_at": _fmt_ts(row["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Riesgo regulatorio — create
# ---------------------------------------------------------------------------


@router.post(
    "/riesgos",
    response_model=RiesgoRegulatorioDetail,
    operation_id="crear_riesgo",
)
async def crear_riesgo(body: RiesgoRegulatorioCreate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM riesgo_regulatorio WHERE codigo = :codigo LIMIT 1"),
            {"codigo": body.codigo},
        ).mappings().first()

        if existing:
            raise HTTPException(status_code=409, detail={"error": f"El codigo '{body.codigo}' ya existe"})

        result = db.execute(
            text(
                """
                INSERT INTO riesgo_regulatorio (
                    codigo, nombre, descripcion, obligacion_codigo, categoria,
                    severidad, probabilidad, area_responsable, owner_rol, estado
                ) VALUES (
                    :codigo, :nombre, :descripcion, :obligacion_codigo, :categoria,
                    :severidad, :probabilidad, :area_responsable, :owner_rol, :estado
                )
                RETURNING id, codigo, nombre, descripcion, obligacion_codigo,
                          categoria, severidad, probabilidad, area_responsable,
                          owner_rol, estado, created_at, updated_at
                """
            ),
            {
                "codigo": body.codigo,
                "nombre": body.nombre,
                "descripcion": body.descripcion,
                "obligacion_codigo": body.obligacion_codigo,
                "categoria": body.categoria,
                "severidad": body.severidad,
                "probabilidad": body.probabilidad,
                "area_responsable": body.area_responsable,
                "owner_rol": body.owner_rol,
                "estado": body.estado,
            },
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "codigo": result["codigo"],
            "nombre": result["nombre"],
            "descripcion": result["descripcion"],
            "obligacion_codigo": result["obligacion_codigo"],
            "categoria": result["categoria"],
            "severidad": result["severidad"],
            "probabilidad": result["probabilidad"],
            "area_responsable": result["area_responsable"],
            "owner_rol": result["owner_rol"],
            "estado": result["estado"],
            "controles": [],
            "created_at": _fmt_ts(result["created_at"]),
            "updated_at": _fmt_ts(result["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Riesgo regulatorio — update
# ---------------------------------------------------------------------------


@router.patch(
    "/riesgos/{riesgo_id}",
    response_model=RiesgoRegulatorioDetail,
    operation_id="actualizar_riesgo",
)
async def actualizar_riesgo(riesgo_id: str, body: RiesgoRegulatorioUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM riesgo_regulatorio WHERE id = :rid LIMIT 1"),
            {"rid": riesgo_id},
        ).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Riesgo regulatorio no encontrado"})

        updates = []
        params: dict = {"rid": riesgo_id}

        for field, param_name in [
            ("nombre", "nombre"),
            ("descripcion", "descripcion"),
            ("obligacion_codigo", "obligacion_codigo"),
            ("categoria", "categoria"),
            ("severidad", "severidad"),
            ("probabilidad", "probabilidad"),
            ("area_responsable", "area_responsable"),
            ("owner_rol", "owner_rol"),
            ("estado", "estado"),
        ]:
            value = getattr(body, param_name, None)
            if value is not None:
                updates.append(f"{field} = :{param_name}")
                params[param_name] = value

        if not updates:
            raise HTTPException(status_code=400, detail={"error": "Ningun campo valido para actualizar"})

        updates.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now()

        result = db.execute(
            text(
                f"""
                UPDATE riesgo_regulatorio
                SET {', '.join(updates)}
                WHERE id = :rid
                RETURNING id, codigo, nombre, descripcion, obligacion_codigo,
                          categoria, severidad, probabilidad, riesgo_inherente, area_responsable,
                          owner_rol, estado, created_at, updated_at
                """
            ),
            params,
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "codigo": result["codigo"],
            "nombre": result["nombre"],
            "descripcion": result["descripcion"],
            "obligacion_codigo": result["obligacion_codigo"],
            "categoria": result["categoria"],
            "severidad": result["severidad"],
            "probabilidad": result["probabilidad"],
            "riesgo_inherente": result["riesgo_inherente"],
            "area_responsable": result["area_responsable"],
            "owner_rol": result["owner_rol"],
            "estado": result["estado"],
            "controles": [],
            "created_at": _fmt_ts(result["created_at"]),
            "updated_at": _fmt_ts(result["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Control interno — list
# ---------------------------------------------------------------------------


@router.get(
    "/controles",
    response_model=ControlInternoListResponse,
    operation_id="listar_controles",
)
async def listar_controles(
    estado: str | None = Query(None, description="Filtrar por estado"),
    tipo: str | None = Query(None, description="Filtrar por tipo de control"),
    owner_rol: str | None = Query(None, description="Filtrar por rol responsable"),
    q: str | None = Query(None, description="Buscar por nombre"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    filters = []
    params: dict = {"skip": skip, "limit": limit}

    if estado:
        filters.append("estado = :estado")
        params["estado"] = estado
    if tipo:
        filters.append("tipo_control = :tipo")
        params["tipo"] = tipo
    if owner_rol:
        filters.append("owner_rol = :owner_rol")
        params["owner_rol"] = owner_rol
    if q:
        filters.append("LOWER(nombre) LIKE LOWER(:q)")
        params["q"] = f"%{q}%"

    where_clause = " AND ".join(filters) if filters else "1=1"

    with db_session() as db:
        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM control_interno WHERE {where_clause}"),
            {k: v for k, v in params.items() if k not in ("skip", "limit")},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, codigo, nombre, tipo_control, frecuencia,
                       owner_rol, estado
                FROM control_interno
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "controles": [
                {
                    "id": str(r["id"]),
                    "codigo": r["codigo"],
                    "nombre": r["nombre"],
                    "tipo_control": r["tipo_control"],
                    "frecuencia": r["frecuencia"],
                    "owner_rol": r["owner_rol"],
                    "estado": r["estado"],
                }
                for r in rows
            ],
            "total": count_rows,
        }


# ---------------------------------------------------------------------------
# Control interno — detail
# ---------------------------------------------------------------------------


@router.get(
    "/controles/{control_id}",
    response_model=ControlInternoDetail,
    operation_id="get_control",
)
async def get_control(control_id: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, nombre, descripcion, tipo_control, frecuencia,
                       owner_rol, sistema_apoyo, estado, created_at, updated_at
                FROM control_interno
                WHERE id = :cid
                LIMIT 1
                """
            ),
            {"cid": control_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Control interno no encontrado"})

        # Fetch pruebas for this control (via riesgo_control_link)
        pruebas = db.execute(
            text(
                """
                SELECT pc.id, pc.fecha_prueba, pc.resultado,
                       pc.evidencia_descripcion, pc.ejecutado_por
                FROM prueba_control pc
                JOIN riesgo_control_link rcl ON rcl.id = pc.link_id
                WHERE rcl.control_id = :cid AND pc.activo = true
                ORDER BY pc.fecha_prueba DESC
                """
            ),
            {"cid": control_id},
        ).mappings()

        pruebas_list = [
            {
                "id": str(p["id"]),
                "fecha_prueba": _fmt_date(p["fecha_prueba"]),
                "resultado": p["resultado"],
                "evidencia_descripcion": p["evidencia_descripcion"],
                "ejecutado_por": p["ejecutado_por"],
            }
            for p in pruebas
        ]

        return {
            "id": str(row["id"]),
            "codigo": row["codigo"],
            "nombre": row["nombre"],
            "descripcion": row["descripcion"],
            "tipo_control": row["tipo_control"],
            "frecuencia": row["frecuencia"],
            "owner_rol": row["owner_rol"],
            "sistema_apoyo": row["sistema_apoyo"],
            "estado": row["estado"],
            "pruebas": pruebas_list,
            "created_at": _fmt_ts(row["created_at"]),
            "updated_at": _fmt_ts(row["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Control interno — create
# ---------------------------------------------------------------------------


@router.post(
    "/controles",
    response_model=ControlInternoDetail,
    operation_id="crear_control",
)
async def crear_control(body: ControlInternoCreate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM control_interno WHERE codigo = :codigo LIMIT 1"),
            {"codigo": body.codigo},
        ).mappings().first()

        if existing:
            raise HTTPException(status_code=409, detail={"error": f"El codigo '{body.codigo}' ya existe"})

        result = db.execute(
            text(
                """
                INSERT INTO control_interno (
                    codigo, nombre, descripcion, tipo_control, frecuencia,
                    owner_rol, sistema_apoyo, estado
                ) VALUES (
                    :codigo, :nombre, :descripcion, :tipo_control, :frecuencia,
                    :owner_rol, :sistema_apoyo, :estado
                )
                RETURNING id, codigo, nombre, descripcion, tipo_control, frecuencia,
                          owner_rol, sistema_apoyo, estado, created_at, updated_at
                """
            ),
            {
                "codigo": body.codigo,
                "nombre": body.nombre,
                "descripcion": body.descripcion,
                "tipo_control": body.tipo_control,
                "frecuencia": body.frecuencia,
                "owner_rol": body.owner_rol,
                "sistema_apoyo": body.sistema_apoyo,
                "estado": body.estado,
            },
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "codigo": result["codigo"],
            "nombre": result["nombre"],
            "descripcion": result["descripcion"],
            "tipo_control": result["tipo_control"],
            "frecuencia": result["frecuencia"],
            "owner_rol": result["owner_rol"],
            "sistema_apoyo": result["sistema_apoyo"],
            "estado": result["estado"],
            "pruebas": [],
            "created_at": _fmt_ts(result["created_at"]),
            "updated_at": _fmt_ts(result["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Control interno — update
# ---------------------------------------------------------------------------


@router.patch(
    "/controles/{control_id}",
    response_model=ControlInternoDetail,
    operation_id="actualizar_control",
)
async def actualizar_control(control_id: str, body: ControlInternoUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM control_interno WHERE id = :cid LIMIT 1"),
            {"cid": control_id},
        ).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Control interno no encontrado"})

        updates = []
        params: dict = {"cid": control_id}

        for field, param_name in [
            ("nombre", "nombre"),
            ("descripcion", "descripcion"),
            ("tipo_control", "tipo_control"),
            ("frecuencia", "frecuencia"),
            ("owner_rol", "owner_rol"),
            ("sistema_apoyo", "sistema_apoyo"),
            ("estado", "estado"),
        ]:
            value = getattr(body, param_name, None)
            if value is not None:
                updates.append(f"{field} = :{param_name}")
                params[param_name] = value

        if not updates:
            raise HTTPException(status_code=400, detail={"error": "Ningun campo valido para actualizar"})

        updates.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now()

        result = db.execute(
            text(
                f"""
                UPDATE control_interno
                SET {', '.join(updates)}
                WHERE id = :cid
                RETURNING id, codigo, nombre, descripcion, tipo_control, frecuencia,
                          owner_rol, sistema_apoyo, estado, created_at, updated_at
                """
            ),
            params,
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "codigo": result["codigo"],
            "nombre": result["nombre"],
            "descripcion": result["descripcion"],
            "tipo_control": result["tipo_control"],
            "frecuencia": result["frecuencia"],
            "owner_rol": result["owner_rol"],
            "sistema_apoyo": result["sistema_apoyo"],
            "estado": result["estado"],
            "pruebas": [],
            "created_at": _fmt_ts(result["created_at"]),
            "updated_at": _fmt_ts(result["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Riesgo-Control link — create
# ---------------------------------------------------------------------------


@router.post(
    "/links",
    response_model=RiesgoControlLinkDetail,
    operation_id="crear_riesgo_control_link",
)
async def crear_riesgo_control_link(body: RiesgoControlLinkCreate):
    with db_session() as db:
        # Validate risk exists
        riesgo = db.execute(
            text("SELECT id FROM riesgo_regulatorio WHERE id = :rid LIMIT 1"),
            {"rid": body.riesgo_id},
        ).mappings().first()
        if not riesgo:
            raise HTTPException(status_code=404, detail={"error": "Riesgo no encontrado"})

        # Validate control exists
        control = db.execute(
            text("SELECT id FROM control_interno WHERE id = :cid LIMIT 1"),
            {"cid": body.control_id},
        ).mappings().first()
        if not control:
            raise HTTPException(status_code=404, detail={"error": "Control no encontrado"})

        # Check duplicate mapping
        existing = db.execute(
            text(
                "SELECT id FROM riesgo_control_link WHERE riesgo_id = :rid AND control_id = :cid LIMIT 1"
            ),
            {"rid": body.riesgo_id, "cid": body.control_id},
        ).mappings().first()

        if existing:
            raise HTTPException(status_code=409, detail={"error": "Ya existe un vinculo entre este riesgo y control"})

        result = db.execute(
            text(
                """
                INSERT INTO riesgo_control_link (
                    riesgo_id, control_id, efectividad, riesgo_residual,
                    frecuencia_prueba, criterio_suficiencia, caducidad_dias
                ) VALUES (
                    :rid, :cid, :efectividad, :riesgo_residual,
                    :frecuencia_prueba, :criterio_suficiencia, :caducidad_dias
                )
                RETURNING id, efectividad, riesgo_residual, frecuencia_prueba,
                          criterio_suficiencia, caducidad_dias, activo,
                          created_at, updated_at
                """
            ),
            {
                "rid": body.riesgo_id,
                "cid": body.control_id,
                "efectividad": body.efectividad,
                "riesgo_residual": body.riesgo_residual,
                "frecuencia_prueba": body.frecuencia_prueba,
                "criterio_suficiencia": body.criterio_suficiencia,
                "caducidad_dias": body.caducidad_dias,
            },
        ).mappings().first()

        db.commit()

        # Fetch risk and control names
        rc = db.execute(
            text("SELECT codigo, nombre FROM riesgo_regulatorio WHERE id = :rid"),
            {"rid": body.riesgo_id},
        ).mappings().first()
        ci = db.execute(
            text("SELECT codigo, nombre FROM control_interno WHERE id = :cid"),
            {"cid": body.control_id},
        ).mappings().first()

        return {
            "id": str(result["id"]),
            "riesgo_codigo": rc["codigo"],
            "riesgo_nombre": rc["nombre"],
            "control_codigo": ci["codigo"],
            "control_nombre": ci["nombre"],
            "efectividad": result["efectividad"],
            "riesgo_residual": result["riesgo_residual"],
            "frecuencia_prueba": result["frecuencia_prueba"],
            "criterio_suficiencia": result["criterio_suficiencia"],
            "caducidad_dias": result["caducidad_dias"],
            "activo": result["activo"],
            "pruebas": [],
            "created_at": _fmt_ts(result["created_at"]),
            "updated_at": _fmt_ts(result["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Riesgo-Control link — list
# ---------------------------------------------------------------------------


@router.get(
    "/links",
    response_model=RiesgoControlLinkListResponse,
    operation_id="listar_riesgo_control_links",
)
async def listar_riesgo_control_links(
    riesgo_id: str | None = Query(None, description="Filtrar por riesgo"),
    control_id: str | None = Query(None, description="Filtrar por control"),
    efectividad: str | None = Query(None, description="Filtrar por efectividad"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    filters = ["rcl.activo = true"]
    params: dict = {"skip": skip, "limit": limit}

    if riesgo_id:
        filters.append("rcl.riesgo_id = :riesgo_id")
        params["riesgo_id"] = riesgo_id
    if control_id:
        filters.append("rcl.control_id = :control_id")
        params["control_id"] = control_id
    if efectividad:
        filters.append("rcl.efectividad = :efectividad")
        params["efectividad"] = efectividad

    where_clause = " AND ".join(filters)

    with db_session() as db:
        count_rows = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM riesgo_control_link rcl
                WHERE {where_clause}
                """
            ),
            {k: v for k, v in params.items() if k not in ("skip", "limit")},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT rcl.id, rcl.efectividad, rcl.riesgo_residual,
                       rcl.frecuencia_prueba, rcl.criterio_suficiencia,
                       rcl.caducidad_dias, rcl.activo,
                       rc.codigo AS riesgo_codigo, rc.nombre AS riesgo_nombre,
                       ci.codigo AS control_codigo, ci.nombre AS control_nombre
                FROM riesgo_control_link rcl
                JOIN riesgo_regulatorio rc ON rc.id = rcl.riesgo_id
                JOIN control_interno ci ON ci.id = rcl.control_id
                WHERE {where_clause}
                ORDER BY rcl.created_at DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "links": [
                {
                    "id": str(r["id"]),
                    "riesgo_codigo": r["riesgo_codigo"],
                    "riesgo_nombre": r["riesgo_nombre"],
                    "control_codigo": r["control_codigo"],
                    "control_nombre": r["control_nombre"],
                    "efectividad": r["efectividad"],
                    "riesgo_residual": r["riesgo_residual"],
                    "frecuencia_prueba": r["frecuencia_prueba"],
                    "criterio_suficiencia": r["criterio_suficiencia"],
                    "caducidad_dias": r["caducidad_dias"],
                    "activo": r["activo"],
                }
                for r in rows
            ],
            "total": count_rows,
        }


# ---------------------------------------------------------------------------
# Riesgo-Control link — detail with pruebas
# ---------------------------------------------------------------------------


@router.get(
    "/links/{link_id}",
    response_model=RiesgoControlLinkDetail,
    operation_id="get_riesgo_control_link",
)
async def get_riesgo_control_link(link_id: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT rcl.id, rcl.efectividad, rcl.riesgo_residual,
                       rcl.frecuencia_prueba, rcl.criterio_suficiencia,
                       rcl.caducidad_dias, rcl.activo,
                       rcl.created_at, rcl.updated_at,
                       rc.codigo AS riesgo_codigo, rc.nombre AS riesgo_nombre,
                       ci.codigo AS control_codigo, ci.nombre AS control_nombre
                FROM riesgo_control_link rcl
                JOIN riesgo_regulatorio rc ON rc.id = rcl.riesgo_id
                JOIN control_interno ci ON ci.id = rcl.control_id
                WHERE rcl.id = :lid
                LIMIT 1
                """
            ),
            {"lid": link_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Vinculo riesgo-control no encontrado"})

        # Fetch pruebas
        pruebas = db.execute(
            text(
                """
                SELECT id, fecha_prueba, resultado, evidencia_descripcion,
                       ejecutado_por, activo, created_at, updated_at
                FROM prueba_control
                WHERE link_id = :lid AND activo = true
                ORDER BY fecha_prueba DESC
                """
            ),
            {"lid": link_id},
        ).mappings()

        pruebas_list = [
            {
                "id": str(p["id"]),
                "fecha_prueba": _fmt_date(p["fecha_prueba"]),
                "resultado": p["resultado"],
                "evidencia_descripcion": p["evidencia_descripcion"],
                "ejecutado_por": p["ejecutado_por"],
            }
            for p in pruebas
        ]

        return {
            "id": str(row["id"]),
            "riesgo_codigo": row["riesgo_codigo"],
            "riesgo_nombre": row["riesgo_nombre"],
            "control_codigo": row["control_codigo"],
            "control_nombre": row["control_nombre"],
            "efectividad": row["efectividad"],
            "riesgo_residual": row["riesgo_residual"],
            "frecuencia_prueba": row["frecuencia_prueba"],
            "criterio_suficiencia": row["criterio_suficiencia"],
            "caducidad_dias": row["caducidad_dias"],
            "activo": row["activo"],
            "pruebas": pruebas_list,
            "created_at": _fmt_ts(row["created_at"]),
            "updated_at": _fmt_ts(row["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Prueba control — create
# ---------------------------------------------------------------------------


@router.post(
    "/pruebas",
    response_model=PruebaControlDetail,
    operation_id="crear_prueba_control",
)
async def crear_prueba_control(body: PruebaControlCreate):
    with db_session() as db:
        # Validate link exists
        link = db.execute(
            text("SELECT id FROM riesgo_control_link WHERE id = :lid LIMIT 1"),
            {"lid": body.link_id},
        ).mappings().first()
        if not link:
            raise HTTPException(status_code=404, detail={"error": "Vinculo riesgo-control no encontrado"})

        # Parse date
        try:
            fecha = date.fromisoformat(body.fecha_prueba)
        except (ValueError, TypeError) as err:
            raise HTTPException(
                status_code=400, detail={"error": "Formato de fecha invalido. Usar YYYY-MM-DD"}
            ) from err

        result = db.execute(
            text(
                """
                INSERT INTO prueba_control (
                    link_id, fecha_prueba, resultado, evidencia_descripcion,
                    evidencia_url, ejecutado_por, nota
                ) VALUES (
                    :lid, :fecha, :resultado, :evidencia_descripcion,
                    :evidencia_url, :ejecutado_por, :nota
                )
                RETURNING id, link_id, fecha_prueba, resultado,
                          evidencia_descripcion, evidencia_url, ejecutado_por,
                          nota, activo, created_at, updated_at
                """
            ),
            {
                "lid": body.link_id,
                "fecha": fecha,
                "resultado": body.resultado,
                "evidencia_descripcion": body.evidencia_descripcion,
                "evidencia_url": body.evidencia_url,
                "ejecutado_por": body.ejecutado_por,
                "nota": body.nota,
            },
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "link_id": str(result["link_id"]),
            "fecha_prueba": _fmt_date(result["fecha_prueba"]),
            "resultado": result["resultado"],
            "evidencia_descripcion": result["evidencia_descripcion"],
            "evidencia_url": result["evidencia_url"],
            "ejecutado_por": result["ejecutado_por"],
            "nota": result["nota"],
            "activo": result["activo"],
            "created_at": _fmt_ts(result["created_at"]),
            "updated_at": _fmt_ts(result["updated_at"]),
        }


# ---------------------------------------------------------------------------
# Prueba control — list (by link_id)
# ---------------------------------------------------------------------------


@router.get(
    "/pruebas",
    response_model=PruebaControlListResponse,
    operation_id="listar_pruebas_control",
)
async def listar_pruebas_control(
    link_id: str = Query(..., description="ID del riesgo_control_link"),
    resultado: str | None = Query(None, description="Filtrar por resultado"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    filters = ["prueba_control.link_id = :link_id"]
    params: dict = {"link_id": link_id, "skip": skip, "limit": limit}

    if resultado:
        filters.append("prueba_control.resultado = :resultado")
        params["resultado"] = resultado

    where_clause = " AND ".join(filters)

    with db_session() as db:
        # Validate link exists
        link = db.execute(
            text("SELECT id FROM riesgo_control_link WHERE id = :lid LIMIT 1"),
            {"lid": link_id},
        ).mappings().first()
        if not link:
            raise HTTPException(status_code=404, detail={"error": "Vinculo riesgo-control no encontrado"})

        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM prueba_control WHERE {where_clause}"),
            {k: v for k, v in params.items() if k not in ("skip", "limit")},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, fecha_prueba, resultado, evidencia_descripcion, ejecutado_por
                FROM prueba_control
                WHERE {where_clause}
                ORDER BY fecha_prueba DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "pruebas": [
                {
                    "id": str(r["id"]),
                    "fecha_prueba": _fmt_date(r["fecha_prueba"]),
                    "resultado": r["resultado"],
                    "evidencia_descripcion": r["evidencia_descripcion"],
                    "ejecutado_por": r["ejecutado_por"],
                }
                for r in rows
            ],
            "total": count_rows,
        }


# ---------------------------------------------------------------------------
# Control gaps — aggregate view
# ---------------------------------------------------------------------------


@router.get(
    "/gaps",
    response_model=ControlGapsResponse,
    operation_id="control_gaps",
)
async def control_gaps(
    estado: str | None = Query(None, description="Filtrar por estado de gap (sin_control, parcial, completo)"),
    area: str | None = Query(None, description="Filtrar por area responsable"),
):
    with db_session() as db:
        filters = ["1=1"]
        params: dict = {}

        if area:
            filters.append("rr.area_responsable = :area")
            params["area"] = area

        where_clause = " AND ".join(filters)

        rows = db.execute(
            text(
                f"""
                SELECT rr.codigo AS riesgo_codigo, rr.nombre AS riesgo_nombre,
                       rr.severidad, rr.obligacion_codigo, rr.estado AS riesgo_estado,
                       COUNT(DISTINCT CASE WHEN rcl.activo THEN rcl.control_id END) AS controles_asignados,
                       COUNT(DISTINCT CASE WHEN rcl.efectividad = 'efectivo' THEN rcl.control_id END) AS controles_efectivos,
                       MAX(pc.fecha_prueba) AS ultima_prueba_fecha,
                       (SELECT pc2.resultado
                        FROM prueba_control pc2
                        JOIN riesgo_control_link rcl2 ON rcl2.id = pc2.link_id
                        WHERE rcl2.riesgo_id = rr.id AND pc2.activo = true
                        ORDER BY pc2.fecha_prueba DESC
                        LIMIT 1) AS ultima_prueba_resultado
                FROM riesgo_regulatorio rr
                LEFT JOIN riesgo_control_link rcl ON rcl.riesgo_id = rr.id AND rcl.activo = true
                LEFT JOIN prueba_control pc ON pc.link_id = rcl.id AND pc.activo = true
                WHERE {where_clause}
                GROUP BY rr.id, rr.codigo, rr.nombre, rr.severidad, rr.obligacion_codigo, rr.estado
                ORDER BY
                    CASE rr.severidad
                        WHEN 'critica' THEN 1
                        WHEN 'alta' THEN 2
                        WHEN 'media' THEN 3
                        WHEN 'baja' THEN 4
                        ELSE 5
                    END
                """
            ),
            params,
        ).mappings()

        gaps = []
        resumen = {"sin_control": 0, "parcial": 0, "completo": 0, "total": 0}

        for r in rows:
            asignados = r["controles_asignados"] or 0
            efectivos = r["controles_efectivos"] or 0

            if asignados == 0:
                gap_estado = "sin_control"
            elif efectivos < asignados:
                gap_estado = "parcial"
            else:
                gap_estado = "completo"

            # If risk itself is not active, still show but mark appropriately
            if r["riesgo_estado"] in ("cerrado",):
                gap_estado = "completo"

            gaps.append(
                {
                    "riesgo_codigo": r["riesgo_codigo"],
                    "riesgo_nombre": r["riesgo_nombre"],
                    "severidad": r["severidad"],
                    "obligacion_codigo": r["obligacion_codigo"],
                    "controles_asignados": asignados,
                    "controles_efectivos": efectivos,
                    "estado": gap_estado,
                    "ultima_prueba_fecha": _fmt_date(r["ultima_prueba_fecha"]),
                    "ultima_prueba_resultado": r["ultima_prueba_resultado"],
                }
            )

            resumen[gap_estado] = resumen.get(gap_estado, 0) + 1
            resumen["total"] += 1

        # Apply estado filter if requested
        if estado:
            gaps = [g for g in gaps if g["estado"] == estado]
            # Recompute resumen after filter
            resumen = {
                "sin_control": sum(1 for g in gaps if g["estado"] == "sin_control"),
                "parcial": sum(1 for g in gaps if g["estado"] == "parcial"),
                "completo": sum(1 for g in gaps if g["estado"] == "completo"),
                "total": len(gaps),
            }

        return {
            "gaps": gaps,
            "total": len(gaps),
            "resumen": resumen,
        }
