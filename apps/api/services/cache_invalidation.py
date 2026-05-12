"""Cache invalidation service for compliance data changes.

When regulatory data changes (legislation updates, IVA rate changes, etc.),
this service triggers invalidation of affected in-memory caches.
"""

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Registry of invalidation callbacks
_invalidation_callbacks: list[tuple[str, Callable]] = []


def register_invalidation_callback(name: str, callback: Callable) -> None:
    """Register a callback to be called when cache invalidation is triggered."""
    _invalidation_callbacks.append((name, callback))
    logger.info("Registered invalidation callback: %s", name)


def invalidate_all(reason: str = "manual") -> None:
    """Invalidate all registered caches.

    Args:
        reason: Why invalidation is happening (e.g., 'legislation_update', 'rate_change')
    """
    logger.info("Invalidating all caches (reason: %s)", reason)
    for name, callback in _invalidation_callbacks:
        try:
            callback()
            logger.info("Invalidated cache: %s", name)
        except Exception as e:
            logger.error("Failed to invalidate cache %s: %s", name, e)


def invalidate_by_type(cache_type: str, reason: str = "manual") -> None:
    """Invalidate caches of a specific type.

    Args:
        cache_type: Type of cache to invalidate ('models', 'config', 'reranker', 'all')
        reason: Why invalidation is happening
    """
    if cache_type == "all":
        invalidate_all(reason)
        return

    cache_type_aliases = {cache_type}
    if cache_type.endswith("s"):
        cache_type_aliases.add(cache_type[:-1])

    for name, callback in _invalidation_callbacks:
        if any(alias in name for alias in cache_type_aliases):
            try:
                callback()
                logger.info("Invalidated cache %s (type: %s)", name, cache_type)
            except Exception as e:
                logger.error("Failed to invalidate cache %s: %s", name, e)
