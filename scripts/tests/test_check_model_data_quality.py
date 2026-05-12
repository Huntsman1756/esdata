from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "maintenance" / "check_model_data_quality.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_model_data_quality", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sqlite_db_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _create_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE aeat_modelo (
                id INTEGER PRIMARY KEY,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                periodo TEXT,
                impuesto TEXT,
                url_info TEXT
            );

            CREATE TABLE modelo_campana (
                id INTEGER PRIMARY KEY,
                modelo_id INTEGER NOT NULL,
                campana TEXT NOT NULL,
                activo BOOLEAN DEFAULT 1,
                url_instrucciones TEXT,
                url_normativa TEXT,
                url_formato TEXT
            );

            CREATE TABLE modelo_casilla (
                id INTEGER PRIMARY KEY,
                campana_id INTEGER NOT NULL,
                codigo TEXT NOT NULL,
                etiqueta TEXT NOT NULL,
                activa BOOLEAN DEFAULT 1
            );

            CREATE TABLE modelo_normativa (
                id INTEGER PRIMARY KEY,
                modelo_id INTEGER NOT NULL,
                boe_id TEXT,
                titulo TEXT NOT NULL,
                url_boe TEXT
            );

            CREATE TABLE modelo_articulo (
                modelo_id INTEGER NOT NULL,
                articulo_id INTEGER,
                casilla TEXT,
                nota TEXT,
                fuente TEXT NOT NULL,
                url_fuente TEXT,
                norma TEXT,
                numero TEXT,
                metodo_enlace TEXT,
                confianza_enlace REAL
            );

            CREATE TABLE modelo_campana_operativa (
                campana_id INTEGER PRIMARY KEY,
                origen_metadato TEXT,
                estado_metadato TEXT,
                nota TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def _temp_dir():
    with tempfile.TemporaryDirectory(prefix="check-model-data-quality-") as tmp_dir:
        yield Path(tmp_dir)


def test_find_static_url_issues_flags_non_canonical_host():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        seed_file = tmp_dir / "seed-modelos.py"
        seed_file.write_text(
            'URLS = ["https://agenciatributaria.gob.es/modelo-100"]\n',
            encoding="utf-8",
        )

        findings = module.find_static_url_issues(seed_file)

        assert len(findings) == 1
        assert findings[0]["check_id"] == "static.non_canonical_host"


def test_find_static_url_issues_accepts_canonical_hosts():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        seed_file = tmp_dir / "seed-modelos.py"
        seed_file.write_text(
            'URLS = ["https://sede.agenciatributaria.gob.es/modelo-100", "https://www.boe.es/x"]\n',
            encoding="utf-8",
        )

        findings = module.find_static_url_issues(seed_file)

        assert findings == []


def test_find_db_issues_flags_weak_modelo_articulo_provenance():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        db_path = tmp_dir / "quality.sqlite3"
        _create_db(db_path)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO modelo_articulo (modelo_id, articulo_id, fuente, url_fuente, norma, numero, metodo_enlace, confianza_enlace) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (1, 1, "seed", "https://sede.agenciatributaria.gob.es/modelo-100", "LIRPF", "96", "legacy_numero_only", 0.0),
            )
            conn.commit()
        finally:
            conn.close()

        findings = module.find_db_issues(_sqlite_db_url(db_path))

        assert any(f["check_id"] == "db.modelo_articulo_weak_provenance" for f in findings)


def test_find_db_issues_flags_suspicious_modelo_articulo_norma():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        db_path = tmp_dir / "quality.sqlite3"
        _create_db(db_path)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO modelo_articulo (modelo_id, articulo_id, fuente, url_fuente, norma, numero, metodo_enlace, confianza_enlace) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (1, 1, "seed", "https://sede.agenciatributaria.gob.es/modelo-303", "IVA", "91", "manual_official", 1.0),
            )
            conn.commit()
        finally:
            conn.close()

        findings = module.find_db_issues(_sqlite_db_url(db_path))

        assert any(f["check_id"] == "db.modelo_articulo_suspicious_norma" for f in findings)


def test_find_db_issues_flags_curated_draft_conflict_in_modelo_campana_operativa():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        db_path = tmp_dir / "quality.sqlite3"
        _create_db(db_path)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO modelo_campana_operativa (campana_id, origen_metadato, estado_metadato, nota) VALUES (?, ?, ?, ?)",
                (1, "seed_curado", "borrador", "metadato operativo curado"),
            )
            conn.commit()
        finally:
            conn.close()

        findings = module.find_db_issues(_sqlite_db_url(db_path))

        assert any(f["check_id"] == "db.operativa_curated_state_conflict" for f in findings)


def test_find_db_issues_flags_empty_active_campaign_when_other_campaign_has_casillas():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        db_path = tmp_dir / "quality.sqlite3"
        _create_db(db_path)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO aeat_modelo (id, codigo, nombre, url_info) VALUES (?, ?, ?, ?)",
                (1, "290", "Modelo 290 FATCA", "https://sede.agenciatributaria.gob.es/modelo-290"),
            )
            conn.execute(
                "INSERT INTO modelo_campana (id, modelo_id, campana, activo) VALUES (?, ?, ?, ?)",
                (1, 1, "2013", 1),
            )
            conn.execute(
                "INSERT INTO modelo_campana (id, modelo_id, campana, activo) VALUES (?, ?, ?, ?)",
                (2, 1, "2025", 0),
            )
            conn.execute(
                "INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, activa) VALUES (?, ?, ?, ?)",
                (2, "DR:1:1", "NIF entidad declarante", 1),
            )
            conn.commit()
        finally:
            conn.close()

        findings = module.find_db_issues(_sqlite_db_url(db_path))

        assert any(
            f["check_id"] == "db.modelo_campana_active_empty_historical_fields"
            and "codigo=290" in f["location"]
            for f in findings
        )


def test_find_db_issues_uses_approved_host_check_ids():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        db_path = tmp_dir / "quality.sqlite3"
        _create_db(db_path)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO aeat_modelo (id, codigo, nombre, url_info) VALUES (?, ?, ?, ?)",
                (1, "100", "Modelo 100", "http://sede.agenciatributaria.gob.es/modelo-100"),
            )
            conn.execute(
                "INSERT INTO modelo_campana (id, modelo_id, campana, url_instrucciones) VALUES (?, ?, ?, ?)",
                (1, 1, "2025", "https://agenciatributaria.gob.es/instrucciones"),
            )
            conn.commit()
        finally:
            conn.close()

        findings = module.find_db_issues(_sqlite_db_url(db_path))
        check_ids = {finding["check_id"] for finding in findings}

        assert "db.aeat_modelo_http_url" in check_ids
        assert "db.modelo_campana_non_canonical_host" in check_ids


def test_normalize_db_url_rewrites_postgres_scheme_to_psycopg():
    module = _load_module()

    normalized = module.normalize_db_url("postgres://user:pass@localhost:5432/app")

    assert normalized == "postgresql+psycopg://user:pass@localhost:5432/app"


def test_run_returns_one_when_findings_exist_in_static_only_mode():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        seed_file = tmp_dir / "seed-modelos.py"
        seed_file.write_text('URL = "https://agenciatributaria.gob.es/modelo-100"\n', encoding="utf-8")

        exit_code, findings = module.run(
            static_paths=[seed_file],
            db_url=None,
            static_only=True,
        )

        assert exit_code == 1
        assert len(findings) == 1


def test_run_returns_zero_when_no_findings_exist_in_static_only_mode():
    module = _load_module()
    with _temp_dir() as tmp_dir:
        seed_file = tmp_dir / "seed-modelos.py"
        seed_file.write_text(
            'URL = "https://sede.agenciatributaria.gob.es/modelo-100"\n',
            encoding="utf-8",
        )

        exit_code, findings = module.run(
            static_paths=[seed_file],
            db_url=None,
            static_only=True,
        )

        assert exit_code == 0
        assert findings == []


def test_run_respects_explicit_empty_static_paths_list():
    module = _load_module()

    with _temp_dir() as tmp_dir:
        seed_file = tmp_dir / "seed-modelos.py"
        seed_file.write_text('URL = "https://agenciatributaria.gob.es/modelo-100"\n', encoding="utf-8")
        module.DEFAULT_STATIC_PATHS = [seed_file]

        exit_code, findings = module.run(
            static_paths=[],
            db_url=None,
            static_only=True,
        )

        assert exit_code == 0
        assert findings == []
