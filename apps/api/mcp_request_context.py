from __future__ import annotations

from contextvars import ContextVar


_MCP_INTERNAL_REQUEST: ContextVar[bool] = ContextVar("mcp_internal_request", default=False)
_MCP_REQUEST_ID: ContextVar[str | None] = ContextVar("mcp_request_id", default=None)
_MCP_USER_ID: ContextVar[str | None] = ContextVar("mcp_user_id", default=None)


def is_mcp_internal_request() -> bool:
    return _MCP_INTERNAL_REQUEST.get()


def get_mcp_request_id() -> str | None:
    return _MCP_REQUEST_ID.get()


def get_mcp_user_id() -> str | None:
    return _MCP_USER_ID.get()


class mcp_request_scope:
    def __init__(self, request_id: str | None = None, user_id: str | None = None):
        self._request_id = request_id
        self._user_id = user_id

    def __enter__(self):
        self._request_id_token = _MCP_REQUEST_ID.set(self._request_id)
        self._user_id_token = _MCP_USER_ID.set(self._user_id)
        return self

    def __exit__(self, exc_type, exc, tb):
        _MCP_REQUEST_ID.reset(self._request_id_token)
        _MCP_USER_ID.reset(self._user_id_token)
        return False


class mcp_internal_request:
    def __enter__(self):
        self._token = _MCP_INTERNAL_REQUEST.set(True)
        return self

    def __exit__(self, exc_type, exc, tb):
        _MCP_INTERNAL_REQUEST.reset(self._token)
        return False
