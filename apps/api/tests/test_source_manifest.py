import sys
from pathlib import Path


API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_find_manifest_uses_env_override(monkeypatch):
    from services import source_manifest

    manifest = Path(__file__).resolve().parents[3] / "docs" / "source-manifests" / "sociedad-valores-wave-1.md"
    monkeypatch.setenv("ESDATA_MANIFEST_PATH", str(manifest))

    assert source_manifest._find_manifest() == manifest


def test_find_manifest_searches_upwards_from_module(monkeypatch):
    from services import source_manifest

    monkeypatch.delenv("ESDATA_MANIFEST_PATH", raising=False)
    manifest = source_manifest._find_manifest()

    assert manifest.name == "sociedad-valores-wave-1.md"
    assert manifest.exists()
