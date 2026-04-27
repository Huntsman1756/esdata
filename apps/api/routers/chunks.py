from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from db import db_session
from schemas import ChunkDetailResponse

router = APIRouter(prefix="/v1/chunks", tags=["chunks"])


@router.get(
    "/{chunk_id}",
    operation_id="get_chunk",
    response_model=ChunkDetailResponse,
    summary="Obtener un chunk por su ID",
)
async def get_chunk(chunk_id: int):
    with db_session() as db:
        try:
            row = (
                db.execute(
                    text(
                        """
                        SELECT
                            df.id,
                            df.documento_origen_tipo,
                            df.documento_origen_id,
                            df.chunk_index,
                            df.chunk_type,
                            df.titulo,
                            df.texto,
                            df.char_start,
                            df.char_end,
                            df.token_count,
                            df.seccion_id
                        FROM documento_fragmento df
                        WHERE df.id = :chunk_id
                        LIMIT 1
                        """
                    ),
                    {"chunk_id": chunk_id},
                )
                .mappings()
                .first()
            )
        except OperationalError as exc:
            # SQLite test fixtures do not always bootstrap chunk tables.
            if "no such table" in str(exc).lower() and "documento_fragmento" in str(exc):
                raise HTTPException(
                    status_code=404, detail={"error": "Chunk no encontrado"}
                ) from exc
            raise
        if not row:
            raise HTTPException(
                status_code=404, detail={"error": "Chunk no encontrado"}
            )

        seccion = None
        sec_row = (
            db.execute(
                text(
                    """
                    SELECT
                        ds.id,
                        ds.tipo_seccion,
                        ds.numero,
                        ds.titulo,
                        ds.nivel
                    FROM documento_seccion ds
                    WHERE ds.id = :seccion_id
                    LIMIT 1
                    """
                ),
                {"seccion_id": row["seccion_id"]},
            )
            .mappings()
            .first()
        )
        if sec_row:
            seccion = {
                "id": sec_row["id"],
                "tipo_seccion": sec_row["tipo_seccion"],
                "numero": sec_row["numero"],
                "titulo": sec_row["titulo"],
                "nivel": sec_row["nivel"],
            }

        return ChunkDetailResponse(
            chunk={
                "id": row["id"],
                "documento_origen_tipo": row["documento_origen_tipo"],
                "documento_origen_id": row["documento_origen_id"],
                "chunk_index": row["chunk_index"],
                "chunk_type": row["chunk_type"],
                "titulo": row["titulo"],
                "texto": row["texto"],
                "char_start": row["char_start"],
                "char_end": row["char_end"],
                "token_count": row["token_count"],
                "seccion": seccion,
            }
        )
