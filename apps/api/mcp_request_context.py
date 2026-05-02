from __future__ import annotations

from contextvars import ContextVar


_MCP_INTERNAL_REQUEST: ContextVar[bool] = ContextVar("mcp_internal_request", default=False)


def is_mcp_internal_request() -> bool:
    return _MCP_INTERNAL_REQUEST.get()


class mcp_internal_request:
    def __enter__(self):
        self._token = _MCP_INTERNAL_REQUEST.set(True)
        return self

    def __exit__(self, exc_type, exc, tb):
        _MCP_INTERNAL_REQUEST.reset(self._token)
        return False
