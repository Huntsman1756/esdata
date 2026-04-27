import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    EvidenciaControlDetail,
    EvidenciaControlListResponse,
    EvidenciaControlSummary,
    EvidenciaControlUpdate,
    PlaybookOperativoCreate,
    PlaybookOperativoDetail,
    PlaybookOperativoListResponse,
    PlaybookOperativoSummary,
    PlaybookOperativoUpdate,
    PlaybookStepCreate,
    PlaybookStepDetail,
    PlaybookStepSummary,
    PlaybookStepUpdate,
)

router = APIRouter(prefix="/v1/playbooks", tags=["playbooks-operativos"])


# ---------------------------------------------------------------------------
# Playbook operativo — list
# ---------------------------------------------------------------------------

@router.get("", response_model=PlaybookOperativoListResponse, operation_id="listar_playbooks")
async def listar_playbooks(
    estado: str | None = Query(None, description="Filtrar por estado (activo, inactivo, revisar, obsoleto)"),
    obligacion: str | None = Query(None, description="Filtrar por codigo de obligacion regulatoria"),
    owner_rol: str | None = Query(None, description="Filtrar por rol responsable"),
    q: str | None = Query(None, description="Buscar por nombre"),
    skip: int = Query(0, ge=0, description="Offset de paginacion"),
    limit: int = Query(20, ge=1, le=100, description="Numero de resultados (max 100)"),
):
    filters = []
    params: dict = {"skip": skip, "limit": limit}

    if estado:
        filters.append("estado = :estado")
        params["estado"] = estado
    if obligacion:
        filters.append("obligacion_codigo = :obligacion")
        params["obligacion"] = obligacion
    if owner_rol:
        filters.append("owner_rol = :owner_rol")
        params["owner_rol"] = owner_rol
    if q:
        filters.append("LOWER(nombre) LIKE LOWER(:q)")
        params["q"] = f"%{q}%"

    where_clause = " AND ".join(filters) if filters else "1=1"

    with db_session() as db:
        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM playbook_operativo WHERE {where_clause}"),
            {k: v for k, v in params.items() if k != "skip" and k != "limit"},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, codigo, nombre, obligacion_codigo, frecuencia,
                       owner_rol, estado, version
                FROM playbook_operativo
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "playbooks": [
                {
                    "id": str(row["id"]),
                    "codigo": row["codigo"],
                    "nombre": row["nombre"],
                    "obligacion_codigo": row["obligacion_codigo"],
                    "frecuencia": row["frecuencia"],
                    "owner_rol": row["owner_rol"],
                    "estado": row["estado"],
                    "version": row["version"],
                }
                for row in rows
            ],
            "total": count_rows,
        }


# ---------------------------------------------------------------------------
# Playbook operativo — detail
# ---------------------------------------------------------------------------

@router.get("/{playbook_id}", response_model=PlaybookOperativoDetail, operation_id="get_playbook")
async def get_playbook(playbook_id: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, nombre, obligacion_codigo, descripcion,
                       frecuencia, owner_rol, owner_id, sistema_apoyo,
                       errores_frecuentes, estado, version, version_anterior_id,
                       created_at, updated_at
                FROM playbook_operativo
                WHERE id = :playbook_id
                LIMIT 1
                """
            ),
            {"playbook_id": playbook_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Playbook operativo no encontrado"})

        # Fetch steps
        steps = db.execute(
            text(
                """
                SELECT id, orden, titulo, descripcion, tipo_paso,
                       responsable_rol, input_requerido, output_esperado,
                       prerrequisito_step_id, checklist, activo,
                       created_at, updated_at
                FROM playbook_step
                WHERE playbook_id = :playbook_id AND activo = true
                ORDER BY orden
                """
            ),
            {"playbook_id": playbook_id},
        ).mappings()

        pasos = [
            {
                "id": str(s["id"]),
                "orden": s["orden"],
                "titulo": s["titulo"],
                "descripcion": s["descripcion"],
                "tipo_paso": s["tipo_paso"],
                "responsable_rol": s["responsable_rol"],
                "input_requerido": s["input_requerido"],
                "output_esperado": s["output_esperado"],
                "prerrequisito_step_id": str(s["prerrequisito_step_id"]) if s["prerrequisito_step_id"] else None,
                "checklist": s["checklist"] if isinstance(s["checklist"], list) else [],
                "activo": s["activo"],
                "created_at": str(s["created_at"]) if s["created_at"] else None,
                "updated_at": str(s["updated_at"]) if s["updated_at"] else None,
            }
            for s in steps
        ]

        # Fetch evidence
        evidencias = db.execute(
            text(
                """
                SELECT id, codigo, nombre, descripcion, tipo_evidencia,
                       formato_requerido, conservacion_dias, obligatoria,
                       estado, capturado_en, verificado_por, verificado_en,
                       nota, created_at, updated_at
                FROM evidencia_control
                WHERE playbook_id = :playbook_id
                ORDER BY created_at
                """
            ),
            {"playbook_id": playbook_id},
        ).mappings()

        evidencias_list = [
            {
                "id": str(e["id"]),
                "codigo": e["codigo"],
                "nombre": e["nombre"],
                "descripcion": e["descripcion"],
                "tipo_evidencia": e["tipo_evidencia"],
                "formato_requerido": e["formato_requerido"],
                "conservacion_dias": e["conservacion_dias"],
                "obligatoria": e["obligatoria"],
                "estado": e["estado"],
                "capturado_en": str(e["capturado_en"]) if e["capturado_en"] else None,
                "verificado_por": e["verificado_por"],
                "verificado_en": str(e["verificado_en"]) if e["verificado_en"] else None,
                "nota": e["nota"],
                "created_at": str(e["created_at"]) if e["created_at"] else None,
                "updated_at": str(e["updated_at"]) if e["updated_at"] else None,
            }
            for e in evidencias
        ]

        return {
            "id": str(row["id"]),
            "codigo": row["codigo"],
            "nombre": row["nombre"],
            "obligacion_codigo": row["obligacion_codigo"],
            "descripcion": row["descripcion"],
            "frecuencia": row["frecuencia"],
            "owner_rol": row["owner_rol"],
            "owner_id": row["owner_id"],
            "sistema_apoyo": row["sistema_apoyo"],
            "errores_frecuentes": row["errores_frecuentes"],
            "estado": row["estado"],
            "version": row["version"],
            "version_anterior_id": str(row["version_anterior_id"]) if row["version_anterior_id"] else None,
            "pasos": pasos,
            "evidencias": evidencias_list,
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        }


# ---------------------------------------------------------------------------
# Playbook operativo — create
# ---------------------------------------------------------------------------

@router.post("", response_model=PlaybookOperativoDetail, operation_id="crear_playbook")
async def crear_playbook(body: PlaybookOperativoCreate):
    with db_session() as db:
        # Check unique code
        existing = db.execute(
            text("SELECT id FROM playbook_operativo WHERE codigo = :codigo LIMIT 1"),
            {"codigo": body.codigo},
        ).mappings().first()

        if existing:
            raise HTTPException(status_code=409, detail={"error": f"El codigo '{body.codigo}' ya existe"})

        result = db.execute(
            text(
                """
                INSERT INTO playbook_operativo (
                    codigo, nombre, obligacion_codigo, descripcion,
                    frecuencia, owner_rol, owner_id, sistema_apoyo,
                    errores_frecuentes, estado, version
                ) VALUES (
                    :codigo, :nombre, :obligacion_codigo, :descripcion,
                    :frecuencia, :owner_rol, :owner_id, :sistema_apoyo,
                    :errores_frecuentes, :estado, 1
                )
                RETURNING id, codigo, nombre, obligacion_codigo, descripcion,
                          frecuencia, owner_rol, owner_id, sistema_apoyo,
                          errores_frecuentes, estado, version,
                          created_at, updated_at
                """
            ),
            {
                "codigo": body.codigo,
                "nombre": body.nombre,
                "obligacion_codigo": body.obligacion_codigo,
                "descripcion": body.descripcion,
                "frecuencia": body.frecuencia,
                "owner_rol": body.owner_rol,
                "owner_id": body.owner_id,
                "sistema_apoyo": body.sistema_apoyo,
                "errores_frecuentes": body.errores_frecuentes,
                "estado": body.estado,
            },
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "codigo": result["codigo"],
            "nombre": result["nombre"],
            "obligacion_codigo": result["obligacion_codigo"],
            "descripcion": result["descripcion"],
            "frecuencia": result["frecuencia"],
            "owner_rol": result["owner_rol"],
            "owner_id": result["owner_id"],
            "sistema_apoyo": result["sistema_apoyo"],
            "errores_frecuentes": result["errores_frecuentes"],
            "estado": result["estado"],
            "version": result["version"],
            "version_anterior_id": None,
            "pasos": [],
            "evidencias": [],
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }


# ---------------------------------------------------------------------------
# Playbook operativo — update
# ---------------------------------------------------------------------------

@router.patch("/{playbook_id}", response_model=PlaybookOperativoDetail, operation_id="actualizar_playbook")
async def actualizar_playbook(playbook_id: str, body: PlaybookOperativoUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM playbook_operativo WHERE id = :playbook_id LIMIT 1"),
            {"playbook_id": playbook_id},
        ).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Playbook operativo no encontrado"})

        updates = []
        params: dict = {"playbook_id": playbook_id}

        for field, param_name in [
            ("nombre", "nombre"),
            ("descripcion", "descripcion"),
            ("frecuencia", "frecuencia"),
            ("owner_rol", "owner_rol"),
            ("owner_id", "owner_id"),
            ("sistema_apoyo", "sistema_apoyo"),
            ("errores_frecuentes", "errores_frecuentes"),
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
                UPDATE playbook_operativo
                SET {', '.join(updates)}
                WHERE id = :playbook_id
                RETURNING id, codigo, nombre, obligacion_codigo, descripcion,
                          frecuencia, owner_rol, owner_id, sistema_apoyo,
                          errores_frecuentes, estado, version,
                          created_at, updated_at
                """
            ),
            params,
        ).mappings().first()

        db.commit()

        # Fetch steps and evidencias for the detail response
        pasos = []
        evidencias_list = []

        return {
            "id": str(result["id"]),
            "codigo": result["codigo"],
            "nombre": result["nombre"],
            "obligacion_codigo": result["obligacion_codigo"],
            "descripcion": result["descripcion"],
            "frecuencia": result["frecuencia"],
            "owner_rol": result["owner_rol"],
            "owner_id": result["owner_id"],
            "sistema_apoyo": result["sistema_apoyo"],
            "errores_frecuentes": result["errores_frecuentes"],
            "estado": result["estado"],
            "version": result["version"],
            "version_anterior_id": None,
            "pasos": pasos,
            "evidencias": evidencias_list,
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }


# ---------------------------------------------------------------------------
# Playbook steps — list
# ---------------------------------------------------------------------------

@router.get("/{playbook_id}/steps", response_model=dict, operation_id="listar_pasos_playbook")
async def listar_pasos_playbook(
    playbook_id: str,
    tipo: str | None = Query(None, description="Filtrar por tipo de paso"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    with db_session() as db:
        pb = db.execute(
            text("SELECT id FROM playbook_operativo WHERE id = :pid LIMIT 1"),
            {"pid": playbook_id},
        ).mappings().first()

        if not pb:
            raise HTTPException(status_code=404, detail={"error": "Playbook no encontrado"})

        filters = ["playbook_id = :playbook_id"]
        params: dict = {"playbook_id": playbook_id, "skip": skip, "limit": limit}

        if tipo:
            filters.append("tipo_paso = :tipo")
            params["tipo"] = tipo

        where_clause = " AND ".join(filters)
        rows = db.execute(
            text(
                f"""
                SELECT id, orden, titulo, tipo_paso, responsable_rol, activo
                FROM playbook_step
                WHERE {where_clause}
                ORDER BY orden
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "pasos": [
                {
                    "id": str(r["id"]),
                    "orden": r["orden"],
                    "titulo": r["titulo"],
                    "tipo_paso": r["tipo_paso"],
                    "responsable_rol": r["responsable_rol"],
                    "activo": r["activo"],
                }
                for r in rows
            ],
            "playbook_id": playbook_id,
        }


# ---------------------------------------------------------------------------
# Playbook steps — create
# ---------------------------------------------------------------------------

@router.post("/{playbook_id}/steps", response_model=PlaybookStepDetail, operation_id="crear_paso_playbook")
async def crear_paso_playbook(playbook_id: str, body: PlaybookStepCreate):
    with db_session() as db:
        pb = db.execute(
            text("SELECT id FROM playbook_operativo WHERE id = :pid LIMIT 1"),
            {"pid": playbook_id},
        ).mappings().first()

        if not pb:
            raise HTTPException(status_code=404, detail={"error": "Playbook no encontrado"})

        result = db.execute(
            text(
                """
                INSERT INTO playbook_step (
                    playbook_id, orden, titulo, descripcion, tipo_paso,
                    responsable_rol, input_requerido, output_esperado,
                    prerrequisito_step_id, checklist, activo
                ) VALUES (
                    :playbook_id, :orden, :titulo, :descripcion, :tipo_paso,
                    :responsable_rol, :input_requerido, :output_esperado,
                    :prerrequisito_step_id, :checklist, true
                )
                RETURNING id, orden, titulo, descripcion, tipo_paso,
                          responsable_rol, input_requerido, output_esperado,
                          prerrequisito_step_id, checklist, activo,
                          created_at, updated_at
                """
            ),
            {
                "playbook_id": playbook_id,
                "orden": body.orden,
                "titulo": body.titulo,
                "descripcion": body.descripcion,
                "tipo_paso": body.tipo_paso,
                "responsable_rol": body.responsable_rol,
                "input_requerido": body.input_requerido,
                "output_esperado": body.output_esperado,
                "prerrequisito_step_id": body.prerrequisito_step_id,
                "checklist": json.dumps(body.checklist) if isinstance(body.checklist, list) else "[]",
            },
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "orden": result["orden"],
            "titulo": result["titulo"],
            "descripcion": result["descripcion"],
            "tipo_paso": result["tipo_paso"],
            "responsable_rol": result["responsable_rol"],
            "input_requerido": result["input_requerido"],
            "output_esperado": result["output_esperado"],
            "prerrequisito_step_id": str(result["prerrequisito_step_id"]) if result["prerrequisito_step_id"] else None,
            "checklist": result["checklist"] if isinstance(result["checklist"], list) else [],
            "activo": result["activo"],
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }


# ---------------------------------------------------------------------------
# Playbook steps — update
# ---------------------------------------------------------------------------

@router.patch("/steps/{step_id}", response_model=PlaybookStepDetail, operation_id="actualizar_paso_playbook")
async def actualizar_paso_playbook(step_id: str, body: PlaybookStepUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM playbook_step WHERE id = :step_id LIMIT 1"),
            {"step_id": step_id},
        ).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Paso de playbook no encontrado"})

        updates = []
        params: dict = {"step_id": step_id}

        for field, param_name in [
            ("orden", "orden"),
            ("titulo", "titulo"),
            ("descripcion", "descripcion"),
            ("tipo_paso", "tipo_paso"),
            ("responsable_rol", "responsable_rol"),
            ("input_requerido", "input_requerido"),
            ("output_esperado", "output_esperado"),
            ("prerrequisito_step_id", "prerrequisito_step_id"),
            ("activo", "activo"),
        ]:
            value = getattr(body, param_name, None)
            if value is not None:
                updates.append(f"{field} = :{param_name}")
                params[param_name] = value

        if body.checklist is not None:
            updates.append("checklist = :checklist")
            params["checklist"] = body.checklist if isinstance(body.checklist, list) else []

        if not updates:
            raise HTTPException(status_code=400, detail={"error": "Ningun campo valido para actualizar"})

        updates.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now()

        result = db.execute(
            text(
                f"""
                UPDATE playbook_step
                SET {', '.join(updates)}
                WHERE id = :step_id
                RETURNING id, orden, titulo, descripcion, tipo_paso,
                          responsable_rol, input_requerido, output_esperado,
                          prerrequisito_step_id, checklist, activo,
                          created_at, updated_at
                """
            ),
            params,
        ).mappings().first()

        db.commit()

        return {
            "id": str(result["id"]),
            "orden": result["orden"],
            "titulo": result["titulo"],
            "descripcion": result["descripcion"],
            "tipo_paso": result["tipo_paso"],
            "responsable_rol": result["responsable_rol"],
            "input_requerido": result["input_requerido"],
            "output_esperado": result["output_esperado"],
            "prerrequisito_step_id": str(result["prerrequisito_step_id"]) if result["prerrequisito_step_id"] else None,
            "checklist": result["checklist"] if isinstance(result["checklist"], list) else [],
            "activo": result["activo"],
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }


# ---------------------------------------------------------------------------
# Evidencia control — list
# ---------------------------------------------------------------------------

@router.get("/{playbook_id}/evidencias", response_model=EvidenciaControlListResponse, operation_id="listar_evidencias_playbook")
async def listar_evidencias_playbook(
    playbook_id: str,
    tipo: str | None = Query(None, description="Filtrar por tipo de evidencia"),
    estado: str | None = Query(None, description="Filtrar por estado (requerido, capturado, verificado, rechazado, exento)"),
    obligatoria: bool | None = Query(None, description="Filtrar por obligatoriedad"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    with db_session() as db:
        pb = db.execute(
            text("SELECT id FROM playbook_operativo WHERE id = :pid LIMIT 1"),
            {"pid": playbook_id},
        ).mappings().first()

        if not pb:
            raise HTTPException(status_code=404, detail={"error": "Playbook no encontrado"})

        filters = ["playbook_id = :playbook_id"]
        params: dict = {"playbook_id": playbook_id, "skip": skip, "limit": limit}

        if tipo:
            filters.append("tipo_evidencia = :tipo")
            params["tipo"] = tipo
        if estado:
            filters.append("estado = :estado")
            params["estado"] = estado
        if obligatoria is not None:
            filters.append("obligatoria = :obligatoria")
            params["obligatoria"] = obligatoria

        where_clause = " AND ".join(filters)
        count_rows = db.execute(
            text(f"SELECT COUNT(*) FROM evidencia_control WHERE {where_clause}"),
            {k: v for k, v in params.items() if k != "skip" and k != "limit"},
        ).scalar()

        rows = db.execute(
            text(
                f"""
                SELECT id, codigo, nombre, tipo_evidencia, obligatoria,
                       estado, conservacion_dias
                FROM evidencia_control
                WHERE {where_clause}
                ORDER BY created_at
                LIMIT :limit OFFSET :skip
                """
            ),
            params,
        ).mappings()

        return {
            "evidencias": [
                {
                    "id": str(r["id"]),
                    "codigo": r["codigo"],
                    "nombre": r["nombre"],
                    "tipo_evidencia": r["tipo_evidencia"],
                    "obligatoria": r["obligatoria"],
                    "estado": r["estado"],
                    "conservacion_dias": r["conservacion_dias"],
                }
                for r in rows
            ],
            "total": count_rows,
        }


# ---------------------------------------------------------------------------
# Evidencia control — update (capture/verify)
# ---------------------------------------------------------------------------

@router.patch("/evidencias/{evidencia_id}", response_model=EvidenciaControlDetail, operation_id="actualizar_evidencia")
async def actualizar_evidencia(evidencia_id: str, body: EvidenciaControlUpdate):
    with db_session() as db:
        existing = db.execute(
            text("SELECT id FROM evidencia_control WHERE id = :eid LIMIT 1"),
            {"eid": evidencia_id},
        ).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Evidencia no encontrada"})

        updates = []
        params: dict = {"eid": evidencia_id}

        for field, param_name in [
            ("estado", "estado"),
            ("capturado_en", "capturado_en"),
            ("verificado_por", "verificado_por"),
            ("verificado_en", "verificado_en"),
            ("nota", "nota"),
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
                UPDATE evidencia_control
                SET {', '.join(updates)}
                WHERE id = :eid
                RETURNING id, codigo, nombre, descripcion, tipo_evidencia,
                          formato_requerido, conservacion_dias, obligatoria,
                          estado, capturado_en, verificado_por, verificado_en,
                          nota, created_at, updated_at
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
            "tipo_evidencia": result["tipo_evidencia"],
            "formato_requerido": result["formato_requerido"],
            "conservacion_dias": result["conservacion_dias"],
            "obligatoria": result["obligatoria"],
            "estado": result["estado"],
            "capturado_en": str(result["capturado_en"]) if result["capturado_en"] else None,
            "verificado_por": result["verificado_por"],
            "verificado_en": str(result["verificado_en"]) if result["verificado_en"] else None,
            "nota": result["nota"],
            "created_at": str(result["created_at"]) if result["created_at"] else None,
            "updated_at": str(result["updated_at"]) if result["updated_at"] else None,
        }
