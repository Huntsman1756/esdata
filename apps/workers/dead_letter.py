"""Dead-letter queue for persistently failing worker syncs."""

import logging
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)


def add_dead_letter(
    engine,
    worker_name: str,
    entity_id: str,
    entity_type: str,
    error_message: str,
    error_traceback: str = "",
    max_retries: int = 3,
) -> int:
    """Add or update a dead-letter entry for a persistently failing entity.
    
    Returns the retry_count after incrementing.
    """
    now = datetime.now(UTC).isoformat()
    
    with engine.begin() as conn:
        # Check if entity already exists in dead letter queue
        row = conn.execute(
            text(
                """
                SELECT id, retry_count, first_failed_at, last_failed_at
                FROM sync_dead_letter
                WHERE worker_name = :worker AND entity_id = :entity_id AND resolved = :resolved
                """
            ),
            {"worker": worker_name, "entity_id": entity_id, "resolved": False},
        ).mappings().first()
        
        if row:
            # Increment retry count
            retry_count = row["retry_count"] + 1
            conn.execute(
                text(
                    """
                    UPDATE sync_dead_letter
                    SET retry_count = :retry_count,
                        last_failed_at = :last_failed_at,
                        error_message = :error_message,
                        error_traceback = :error_traceback
                    WHERE id = :id
                    """
                ),
                {
                    "retry_count": retry_count,
                    "last_failed_at": now,
                    "error_message": error_message[:5000],  # Truncate
                    "error_traceback": error_traceback[:2000],  # Truncate
                    "id": row["id"],
                },
            )
        else:
            # New dead letter entry
            conn.execute(
                text(
                    """
                    INSERT INTO sync_dead_letter
                    (worker_name, entity_id, entity_type, error_message, error_traceback,
                     retry_count, max_retries, first_failed_at, last_failed_at)
                    VALUES
                    (:worker, :entity_id, :entity_type, :error_message, :error_traceback,
                     1, :max_retries, :now, :now)
                    """
                ),
                {
                    "worker": worker_name,
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "error_message": error_message[:5000],
                    "error_traceback": error_traceback[:2000],
                    "max_retries": max_retries,
                    "now": now,
                },
            )
            retry_count = 1
    
    return retry_count


def get_dead_letters(
    engine,
    worker_name: Optional[str] = None,
    resolved: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get dead-letter entries for monitoring."""
    conditions = ["resolved IS FALSE"] if not resolved else ["resolved IS TRUE"]
    params: dict = {}
    
    if worker_name:
        conditions.append("worker_name = :worker")
        params["worker"] = worker_name
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT * FROM sync_dead_letter
                WHERE {where}
                ORDER BY last_failed_at DESC
                LIMIT :limit
                """
            ),
            {**params, "limit": limit},
        ).mappings()
        return [dict(row) for row in rows]


def resolve_dead_letter(
    engine,
    dead_letter_id: int,
    resolved_by: str,
    notes: str = "",
) -> bool:
    """Mark a dead-letter entry as resolved."""
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE sync_dead_letter
                SET resolved = TRUE, resolved_at = :now, resolved_by = :resolved_by, notes = :notes
                WHERE id = :id AND resolved IS FALSE
                """
            ),
            {"id": dead_letter_id, "now": now, "resolved_by": resolved_by, "notes": notes},
        )
        return result.rowcount > 0
