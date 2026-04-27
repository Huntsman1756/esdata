import csv
import hashlib
import io
import json


def pgc_etag(data: dict) -> str:
    """Generate an ETag hash for PGC response data."""
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def check_pgc_etag(request, etag: str) -> "Response | None":
    """Check If-None-Match header. Returns 304 if client has current version."""
    if_match = request.headers.get("if-none-match", "").strip('"')
    if if_match == etag:
        return Response(status_code=304)
    return None


def pgc_to_csv(data: list[dict]) -> str:
    """Convert list of dicts to CSV string."""
    if not data:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return buffer.getvalue()
