"""Data lineage and quality tracking backed by durable SQL storage."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from db import engine
from pydantic import BaseModel, Field
from services.persistence import ensure_governance_tables, rows_to_dicts
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DataLineageEntry(BaseModel):
    entry_id: str = Field(description="Unique lineage entry identifier")
    tabla: str
    campo: str
    fuente_origen: str
    transformacion: str = ""
    fecha_ingestion: str
    worker_correspondiente: str = "unknown"
    calidad_score: float = Field(ge=0, le=100, default=100.0)
    observaciones: str = ""


class DataLineageService:
    def __init__(self):
        ensure_governance_tables()

    def _next_id(self) -> str:
        with engine.begin() as conn:
            last_id = conn.execute(text("SELECT COUNT(*) FROM data_lineage")).scalar_one()
        return f"ln-{int(last_id) + 1:06d}"

    def record_lineage(
        self,
        tabla: str,
        campo: str,
        fuente_origen: str,
        transformacion: str = "",
        worker_correspondiente: str = "unknown",
        calidad_score: float = 100.0,
        observaciones: str = "",
    ) -> DataLineageEntry:
        entry = DataLineageEntry(
            entry_id=self._next_id(),
            tabla=tabla,
            campo=campo,
            fuente_origen=fuente_origen,
            transformacion=transformacion,
            fecha_ingestion=datetime.now(UTC).isoformat(),
            worker_correspondiente=worker_correspondiente,
            calidad_score=calidad_score,
            observaciones=observaciones,
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO data_lineage
                    (entry_id, tabla, campo, fuente_origen, transformacion, fecha_ingestion, worker_correspondiente, calidad_score, observaciones)
                    VALUES
                    (:entry_id, :tabla, :campo, :fuente_origen, :transformacion, :fecha_ingestion, :worker_correspondiente, :calidad_score, :observaciones)
                    """
                ),
                entry.model_dump(),
            )
        logger.info("Lineage recorded: %s.%s <- %s", tabla, campo, fuente_origen)
        return entry

    def _rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict]:
        with engine.begin() as conn:
            return rows_to_dicts(conn.execute(text(sql), params or {}))

    def get_lineage(self, tabla: str, campo: str | None = None) -> list[DataLineageEntry]:
        sql = "SELECT * FROM data_lineage WHERE tabla = :tabla"
        params: dict[str, Any] = {"tabla": tabla}
        if campo:
            sql += " AND campo = :campo"
            params["campo"] = campo
        sql += " ORDER BY fecha_ingestion ASC"
        return [DataLineageEntry(**row) for row in self._rows(sql, params)]

    def get_full_lineage(self, tabla: str, campo: str) -> list[DataLineageEntry]:
        return self.get_lineage(tabla, campo)

    def get_data_quality(self, tabla: str) -> dict[str, Any]:
        rows = self._rows(
            "SELECT calidad_score FROM data_lineage WHERE tabla = :tabla",
            {"tabla": tabla},
        )
        scores = [row["calidad_score"] for row in rows]
        if not scores:
            return {"tabla": tabla, "avg_score": 0.0, "min_score": 0.0, "max_score": 0.0, "total_records": 0}
        return {
            "tabla": tabla,
            "avg_score": round(sum(scores) / len(scores), 2),
            "min_score": min(scores),
            "max_score": max(scores),
            "total_records": len(scores),
        }

    def get_all_quality_scores(self) -> list[dict[str, Any]]:
        rows = self._rows("SELECT DISTINCT tabla FROM data_lineage ORDER BY tabla")
        return sorted([self.get_data_quality(row["tabla"]) for row in rows], key=lambda x: x["avg_score"])

    def get_data_catalog(self) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM data_lineage ORDER BY tabla, campo")
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            entry = grouped.setdefault(
                row["tabla"],
                {
                    "tabla": row["tabla"],
                    "campos": set(),
                    "source_tables": set(),
                    "workers": set(),
                    "scores": [],
                    "total_lineage_records": 0,
                },
            )
            entry["campos"].add(row["campo"])
            entry["source_tables"].add(row["fuente_origen"])
            entry["workers"].add(row["worker_correspondiente"])
            entry["scores"].append(row["calidad_score"])
            entry["total_lineage_records"] += 1
        catalog = []
        for tabla, entry in grouped.items():
            avg_score = round(sum(entry["scores"]) / len(entry["scores"]), 2) if entry["scores"] else 0.0
            catalog.append(
                {
                    "tabla": tabla,
                    "campos": sorted(entry["campos"]),
                    "total_campos": len(entry["campos"]),
                    "total_lineage_records": entry["total_lineage_records"],
                    "avg_quality_score": avg_score,
                    "source_tables": sorted(entry["source_tables"]),
                    "workers": sorted(entry["workers"]),
                }
            )
        return sorted(catalog, key=lambda x: x["tabla"])

    def get_catalog_entry(self, tabla: str) -> dict[str, Any] | None:
        for entry in self.get_data_catalog():
            if entry["tabla"] == tabla:
                return entry
        return None

    @property
    def total_records(self) -> int:
        with engine.begin() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM data_lineage")).scalar_one())

    @property
    def table_count(self) -> int:
        with engine.begin() as conn:
            return int(conn.execute(text("SELECT COUNT(DISTINCT tabla) FROM data_lineage")).scalar_one())


_service: DataLineageService | None = None


def get_data_lineage_service() -> DataLineageService:
    global _service
    if _service is None:
        _service = DataLineageService()
    return _service


def reset_data_lineage_service() -> None:
    global _service
    ensure_governance_tables()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM data_lineage"))
    _service = DataLineageService()
