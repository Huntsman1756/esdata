import os
import subprocess
import sys
import urllib.error
import urllib.request


def _ping_healthchecks(url: str | None) -> None:
    if not url:
        return

    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10):
            return
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[healthchecks] ping failed for {url}: {exc}", file=sys.stderr)


def _build_ping_url(status: str) -> str | None:
    base_url = os.getenv("HEALTHCHECKS_PING_URL", "").strip().rstrip("/")
    if not base_url:
        return None
    if status == "success":
        return base_url
    return f"{base_url}/{status}"


def main() -> int:
    worker_cmd = os.getenv("WORKER_CMD", "").strip()
    if not worker_cmd:
        print("WORKER_CMD is required", file=sys.stderr)
        return 2

    _ping_healthchecks(_build_ping_url("start"))
    completed = subprocess.run(worker_cmd, shell=True)

    if completed.returncode == 0:
        _ping_healthchecks(_build_ping_url("success"))
    else:
        _ping_healthchecks(_build_ping_url("fail"))

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
