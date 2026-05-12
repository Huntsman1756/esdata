import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKERS_DIR = ROOT / "apps" / "workers"
COMPOSE_FILE = ROOT / "infra" / "deploy" / "docker-compose.prod.yml"
INVENTORY_FILE = ROOT / "docs" / "worker-inventory.md"
PRD_FILE = ROOT / "prd.json"


def _worker_files() -> set[str]:
    return {path.name for path in WORKERS_DIR.glob("*.py") if path.name != "__init__.py"}


def _compose_worker_files() -> dict[str, list[str]]:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    result: dict[str, list[str]] = {}
    for match in re.finditer(
        r"^  (?P<service>[A-Za-z0-9_-]+):\n(?P<body>(?:    .*(?:\n|$))*)",
        text,
        re.MULTILINE,
    ):
        command = re.search(r"WORKER_CMD:\s*python\s+([A-Za-z0-9_]+\.py)", match.group("body"))
        if not command:
            continue
        result.setdefault(command.group(1), []).append(match.group("service"))
    return result


def _inventory_files() -> set[str]:
    text = INVENTORY_FILE.read_text(encoding="utf-8")
    files = set(re.findall(r"`([^`]+\.py)`", text))
    return {path.split("/")[-1] for path in files if not path.startswith("scripts/")}


def test_worker_inventory_mentions_every_worker_module_once_or_more():
    assert _worker_files() <= _inventory_files()


def test_worker_inventory_deployed_count_matches_compose_worker_commands():
    text = INVENTORY_FILE.read_text(encoding="utf-8")
    compose_files = _compose_worker_files()
    deployed_section = text.split("### With Docker Service (23 files)", 1)[1]
    deployed_section = deployed_section.split("### Existing Worker Modules Not Deployed", 1)[0]

    assert "### With Docker Service (23 files)" in text
    assert len(compose_files) == 23
    for worker_file, services in compose_files.items():
        row_match = re.search(rf"\| `{re.escape(worker_file)}` \| (?P<services>[^|]+) \|", deployed_section)
        assert row_match, worker_file
        documented_services = set(re.findall(r"`([^`]+)`", row_match.group("services")))
        assert documented_services == set(services)


def test_worker_inventory_prd_backlog_covers_undeployed_type_c_modules():
    text = INVENTORY_FILE.read_text(encoding="utf-8")
    prd = json.loads(PRD_FILE.read_text(encoding="utf-8"))
    backlog_files = {
        file_name
        for story in prd.get("workerRemediationStories", [])
        for file_name in story.get("files", [])
    }

    undeployed_section = text.split("### Existing Worker Modules Not Deployed In Production", 1)[1]
    undeployed_section = undeployed_section.split("## TYPE-D", 1)[0]
    undeployed_files = set(re.findall(r"`([^`]+\.py)`", undeployed_section))

    assert len(undeployed_files) == 37
    assert undeployed_files <= backlog_files
