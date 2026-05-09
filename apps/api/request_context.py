"""Request-context helpers for propagating IDs from middleware into routers.

The `RequestLoggingMiddleware` populates `request.state.request_id` for every
incoming HTTP request. Routers that persist audit rows should use
`get_request_id(request)` instead of reading the header directly so that:

- Requests without X-Request-ID still get a stable UUID (not 'unknown')
- Routers see the same id the middleware logged and returned in the response

`get_user_id(request)` is the analogous helper for actor attribution. It
prefers an explicit X-User-ID header (set by the platform / gateway), falls
back to the principal derived from the API key via
`request.state.principal` if set by the auth middleware, and finally returns
'anonymous' — never None — so query_audit_log.user_id stops being NULL.
"""

from __future__ import annotations

import uuid

from starlette.requests import Request


def get_request_id(request: Request) -> str:
    """Return the request id set by RequestLoggingMiddleware.

    Falls back to the X-Request-ID header (if middleware has not run yet in
    tests or if called before dispatch), and finally to a fresh UUID so we
    never return 'unknown'.
    """
    state_id = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    if state_id:
        return state_id
    header_id = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
    if header_id:
        return header_id
    return str(uuid.uuid4())


def get_user_id(request: Request) -> str:
    """Return a non-null actor id for audit persistence.

    Resolution order:
      1. X-User-ID header (explicit principal from upstream gateway)
      2. request.state.principal (set by auth middleware from API key)
      3. request.state.api_key_subject (legacy)
      4. 'anonymous' — never None
    """
    header_user = request.headers.get("x-user-id") or request.headers.get("X-User-ID")
    if header_user:
        return header_user
    if hasattr(request, "state"):
        principal = getattr(request.state, "principal", None)
        if principal:
            return str(principal)
        api_subject = getattr(request.state, "api_key_subject", None)
        if api_subject:
            return str(api_subject)
    return "anonymous"
