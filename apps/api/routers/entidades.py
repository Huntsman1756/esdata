from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import EntityLeiResponse, EntitySearchResponse

router = APIRouter(prefix="/v1/entidades", tags=["entidades"])


@router.get("/lei/{lei}", response_model=EntityLeiResponse, operation_id="get_entidad_por_lei")
async def get_entidad_por_lei(lei: str):
    lei_clean = lei.upper().strip().replace(" ", "")

    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT
                    ei.id,
                    ei.lei,
                    ei.nombre_legal,
                    ei.pais,
                    ei.estado,
                    ei.vigencia_desde,
                    ei.vigencia_hasta,
                    ei.vlei_status,
                    ei.vlei_cred_url,
                    ei.fuente_ref
                FROM entity_identifiers ei
                WHERE ei.lei = :lei
                LIMIT 1
                """
            ),
            {"lei": lei_clean},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Entidad no encontrada", "lei": lei_clean}
            )

        aliases = list(
            db.execute(
                text(
                    """
                    SELECT alias, alias_normalizado, fuente, confianza
                    FROM entity_aliases
                    WHERE empresa_id = :empresa_id
                    ORDER BY confianza DESC, id ASC
                    """
                ),
                {"empresa_id": row["id"]},
            ).mappings()
        )

        return {
            "entidad": {
                **dict(row),
                "vigencia_desde": str(row["vigencia_desde"]) if row["vigencia_desde"] else None,
                "vigencia_hasta": str(row["vigencia_hasta"]) if row["vigencia_hasta"] else None,
                "aliases": [dict(a) for a in aliases],
            }
        }


@router.get("/buscar", response_model=EntitySearchResponse, operation_id="buscar_entidades")
async def buscar_entidades(
    q: str = Query(..., description="Término de búsqueda por nombre, alias o LEI"),
):
    q_lower = q.lower().strip()

    with db_session() as db:
        rows = list(db.execute(
            text(
                """
                SELECT
                    e.id AS id,
                    e.nombre,
                    ei.lei,
                    ei.nombre_legal,
                    ei.pais,
                    ei.estado,
                    MAX(
                        CASE
                            WHEN ei.lei = :q_clean THEN 1.0
                            WHEN LOWER(ei.nombre_legal) = :q_lower THEN 0.9
                            WHEN LOWER(e.nombre) = :q_lower THEN 0.8
                            WHEN LOWER(ea.alias_normalizado) = :q_lower THEN 0.7
                            WHEN LOWER(e.nombre) LIKE :q_name_like THEN 0.6
                            WHEN LOWER(ea.alias_normalizado) LIKE :q_alias_like THEN 0.5
                            ELSE 0.0
                        END
                    ) AS confianza,
                    CASE MIN(
                        CASE
                            WHEN ei.lei = :q_clean THEN 1
                            WHEN LOWER(ei.nombre_legal) = :q_lower THEN 2
                            WHEN LOWER(e.nombre) = :q_lower THEN 3
                            WHEN LOWER(ea.alias_normalizado) = :q_lower THEN 4
                            WHEN LOWER(e.nombre) LIKE :q_name_like THEN 5
                            WHEN LOWER(ea.alias_normalizado) LIKE :q_alias_like THEN 6
                            ELSE 99
                        END
                    )
                        WHEN 1 THEN 'lei_match'
                        WHEN 2 THEN 'nombre_legal_exacto'
                        WHEN 3 THEN 'nombre_exacto'
                        WHEN 4 THEN 'alias_exacto'
                        WHEN 5 THEN 'nombre'
                        WHEN 6 THEN 'alias'
                        ELSE 'fuzzy'
                    END AS motivo
                FROM empresa e
                LEFT JOIN entity_identifiers ei ON ei.empresa_id = e.id
                LEFT JOIN entity_aliases ea ON ea.empresa_id = e.id
                WHERE
                    ei.lei = :q_clean
                    OR LOWER(ei.nombre_legal) LIKE :q_like
                    OR LOWER(e.nombre) LIKE :q_name_like
                    OR LOWER(ea.alias_normalizado) LIKE :q_alias_like
                GROUP BY e.id, e.nombre, ei.lei, ei.nombre_legal, ei.pais, ei.estado
                HAVING confianza > 0
                ORDER BY confianza DESC, e.nombre ASC
                LIMIT 20
                """
            ),
            {
                "q_clean": q.upper().strip().replace(" ", ""),
                "q_lower": q_lower,
                "q_like": f"%{q_lower}%",
                "q_name_like": f"%{q_lower}%",
                "q_alias_like": f"%{q_lower}%",
            },
        ).mappings())

        resultados = []
        for row in rows:
            resultados.append({
                "id": row["id"],
                "nombre": row["nombre"],
                "lei": row["lei"],
                "nombre_legal": row["nombre_legal"],
                "pais": row["pais"],
                "estado": row["estado"],
                "confianza": float(row["confianza"]),
                "motivo": row["motivo"],
            })

        return {
            "q": q,
            "resultados": resultados,
        }


@router.get("/{empresa_id}", operation_id="get_entidad_por_empresa")
async def get_entidad_por_empresa(empresa_id: int):
    with db_session() as db:
        empresa = db.execute(
            text(
                """
                SELECT id, nombre, nif, domicilio, fuente_inicial
                FROM empresa
                WHERE id = :empresa_id
                LIMIT 1
                """
            ),
            {"empresa_id": empresa_id},
        ).mappings().first()

        if not empresa:
            raise HTTPException(
                status_code=404,
                detail={"error": "Empresa no encontrada", "empresa_id": empresa_id}
            )

        ei = db.execute(
            text(
                """
                SELECT id, lei, nombre_legal, pais, estado, vigencia_desde, vigencia_hasta, vlei_status, vlei_cred_url, fuente_ref
                FROM entity_identifiers
                WHERE empresa_id = :empresa_id
                LIMIT 1
                """
            ),
            {"empresa_id": empresa_id},
        ).mappings().first()

        aliases = list(
            db.execute(
                text(
                    """
                    SELECT alias, alias_normalizado, fuente, confianza
                    FROM entity_aliases
                    WHERE empresa_id = :empresa_id
                    ORDER BY confianza DESC, id ASC
                    """
                ),
                {"empresa_id": empresa_id},
            ).mappings()
        )

        result = {
            "empresa": dict(empresa),
        }

        if ei:
            result["entidad"] = {
                **dict(ei),
                "vigencia_desde": str(ei["vigencia_desde"]) if ei["vigencia_desde"] else None,
                "vigencia_hasta": str(ei["vigencia_hasta"]) if ei["vigencia_hasta"] else None,
                "aliases": [dict(a) for a in aliases],
            }
        else:
            result["entidad"] = None

        return result
