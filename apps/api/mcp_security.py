import os
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

_LOCAL_MCP_HOSTS = {"127.0.0.1", "localhost", "::1", "test", "testserver", "api"}


def reset_mcp_rate_limit_state() -> None:
    try:
        from middleware.rate_limit import _rate_limiter

        _rate_limiter._buckets.clear()
    except Exception:
        pass


def _normalize_host(host: str | None) -> str | None:
    if not host:
        return None
    value = host.strip()
    parsed = urlsplit(value if "://" in value else f"//{value}")
    normalized = (parsed.hostname or "").strip().lower().rstrip(".")
    return normalized or None


def _origin_host(origin: str | None) -> str | None:
    if not origin:
        return None
    parsed = urlsplit(origin.strip())
    if parsed.scheme not in {"http", "https"}:
        return None
    normalized = (parsed.hostname or "").strip().lower().rstrip(".")
    return normalized or None


def _configured_mcp_hosts() -> set[str]:
    hosts = set(_LOCAL_MCP_HOSTS)
    api_domain = os.getenv("API_DOMAIN", "").strip()
    if api_domain:
        normalized_api_domain = _normalize_host(api_domain)
        if normalized_api_domain:
            hosts.add(normalized_api_domain)

    allowed_hosts = os.getenv("ESDATA_MCP_ALLOWED_HOSTS", "")
    for value in allowed_hosts.split(","):
        normalized = _normalize_host(value)
        if normalized:
            hosts.add(normalized)
    return hosts


def _configured_mcp_origins() -> set[str]:
    origins = set(_configured_mcp_hosts())
    raw_cors_origins = os.getenv("ESDATA_CORS_ORIGINS", "")
    for value in raw_cors_origins.split(","):
        normalized = _origin_host(value)
        if normalized:
            origins.add(normalized)
    return origins


def _reject_mcp_request(detail: str, status_code: int, request: Request) -> JSONResponse:
    response = JSONResponse({"detail": detail}, status_code=status_code)
    request_id = request.headers.get("x-request-id")
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


async def guard_mcp_http(request: Request, call_next):
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    request_host = _normalize_host(request.headers.get("host"))
    if request_host not in _configured_mcp_hosts():
        return _reject_mcp_request("Invalid MCP Host header", 421, request)

    origin = request.headers.get("origin")
    if origin and _origin_host(origin) not in _configured_mcp_origins():
        return _reject_mcp_request("Invalid MCP Origin header", 403, request)

    provided_key = request.headers.get("X-API-Key", "")
    required_key = os.getenv("MCP_API_KEY", "").strip()
    if required_key and provided_key != required_key:
        return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)
    if not required_key and os.environ.get("APP_ENV", "").lower() != "test":
        return JSONResponse({"detail": "Invalid or missing MCP API key"}, status_code=401)

    if request.method == "GET":
        accept = request.headers.get("accept", "")
        if "text/event-stream" not in accept.lower():
            response = JSONResponse(
                {"detail": "MCP requires Accept: text/event-stream for GET requests"},
                status_code=406,
            )
            request_id = request.headers.get("x-request-id")
            if request_id:
                response.headers["X-Request-ID"] = request_id
            return response

    return await call_next(request)
