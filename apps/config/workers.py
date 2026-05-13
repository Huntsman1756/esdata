"""Compatibility view of the canonical worker cadence registry.

The runtime source of truth is ``apps/api/services/worker_cadence.py``.
This module keeps older deployment checks pointed at the same data.
"""

from apps.api.services.worker_cadence import (  # noqa: F401
    WORKER_CADENCE_ALIASES,
    WORKER_CADENCE_CONFIG,
    WORKER_CADENCE_EXCLUDED,
)


SCHEDULED_MARKET_WORKERS = (
    "worker-eurlex-market",
    "worker-esma-mifir-reporting",
    "worker-esma-firds",
    "worker-esma-dlt",
)
