import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import _resolve_gpt_openapi_path


def test_resolve_gpt_openapi_path_for_container_layout():
    tmp_root = Path(__file__).resolve().parents[3] / "tmp" / "test-main-runtime-paths"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)

    app_dir = tmp_root / "app"
    docs_dir = app_dir / "docs"
    docs_dir.mkdir(parents=True)
    spec_path = docs_dir / "openapi-gpt.json"
    spec_path.write_text("{}", encoding="utf-8")

    try:
        resolved = _resolve_gpt_openapi_path(app_dir / "main.py")
        assert resolved == spec_path
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
