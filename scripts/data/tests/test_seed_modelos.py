#!/usr/bin/env python
"""Tests para scripts/data/seed_modelos.py (estructura de datos, sin DB)."""

import importlib
import sys
from pathlib import Path

import pytest

SEED_DIR = Path(__file__).resolve().parents[0]  # scripts/data/tests/
TARGET = SEED_DIR.parents[0] / "seed_modelos.py"  # scripts/data/seed_modelos.py


@pytest.fixture
def seed_module():
    """Importa seed_modelos.py como módulo sin ejecutar main()."""
    spec = importlib.util.spec_from_file_location(
        "seed_modelos", TARGET,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seed_modelos"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def modelos(seed_module):
    return seed_module.MODELOS


@pytest.fixture
def instrucciones(seed_module):
    return seed_module.INSTRUCCIONES


@pytest.fixture
def obligaciones(seed_module):
    return seed_module.OBLIGACIONES


# ── MODELOS ──────────────────────────────────────────────────────────────────


class TestModeos:
    def test_es_una_lista(self, modelos):
        assert isinstance(modelos, list)

    def test_minimo_30_modelos(self, modelos):
        assert len(modelos) >= 30, (
            f"Se esperan >= 30 modelos, hay {len(modelos)}"
        )

    def test_cada_elemento_tiene_5_campos(self, modelos):
        for i, m in enumerate(modelos):
            assert len(m) == 5, f"Modelo en índice {i} tiene {len(m)} campos, esperado 5"

    def test_cada_codigo_es_estrictamente_3_o_4_digitos(self, modelos):
        for i, m in enumerate(modelos):
            codigo = m[0]
            assert codigo.isdigit(), f"Modelo índice {i}: codigo '{codigo}' no es numérico"
            assert 3 <= len(codigo) <= 4, (
                f"Modelo índice {i}: codigo '{codigo}' debe tener 3 o 4 dígitos"
            )

    def test_codigos_unicos(self, modelos):
        codigos = [m[0] for m in modelos]
        assert len(codigos) == len(set(codigos)), "Hay códigos duplicados en MODELOS"

    def test_periodos_validos(self, modelos):
        periodos_validos = {
            "mensual", "trimestral", "anual",
            "cuando-varia", "evento",
        }
        for i, m in enumerate(modelos):
            assert m[2] in periodos_validos, (
                f"Modelo índice {i}: periodo '{m[2]}' no válido"
            )

    def test_impuestos_no_vacios(self, modelos):
        for i, m in enumerate(modelos):
            assert m[3].strip(), f"Modelo índice {i}: impuesto vacío"

    def test_urls_son_https_aeat(self, modelos):
        for i, m in enumerate(modelos):
            url = m[4]
            assert url.startswith("https://"), (
                f"Modelo índice {i}: URL no empieza con https://: {url}"
            )
            assert "sede.aeat.gob.es" in url, (
                f"Modelo índice {i}: URL no apunta a sede AEAT: {url}"
            )

    def test_nombres_no_vacios(self, modelos):
        for i, m in enumerate(modelos):
            assert m[1].strip(), f"Modelo índice {i}: nombre vacío"

    def test_codigos_conocidos_presentes(self, modelos):
        """Verifica que los modelos clave del seed anterior están presentes."""
        codigos_presentes = {m[0] for m in modelos}
        esperados = {"100", "303", "200", "124", "216", "349", "347", "115"}
        for c in esperados:
            assert c in codigos_presentes, (
                f"Modelo '{c}' ausente en MODELOS"
            )

    def test_nuevos_modelos_agregados(self, modelos):
        """Verifica que los 20 nuevos modelos están presentes."""
        nuevos = {
            "111", "116", "212", "348", "394", "346",
            "720", "201", "430", "431", "037", "046",
            "092", "114", "190", "878", "269", "380",
            "828", "121",
        }
        codigos_presentes = {m[0] for m in modelos}
        for c in nuevos:
            assert c in codigos_presentes, (
                f"Modelo nuevo '{c}' ausente en MODELOS"
            )


# ── INSTRUCCIONES ────────────────────────────────────────────────────────────


class TestInstrucciones:
    def test_es_un_dict(self, instrucciones):
        assert isinstance(instrucciones, dict)

    def test_claves_coinciden_con_codigos(self, instrucciones, modelos):
        codigos = {m[0] for m in modelos}
        for k in instrucciones:
            assert k in codigos, (
                f"Instrucciones para código '{k}' que no existe en MODELOS"
            )

    def test_cada_valor_tiene_tuplas_3_elementos(self, instrucciones):
        for codigo, secciones in instrucciones.items():
            for i, s in enumerate(secciones):
                assert len(s) == 3, (
                    f"Instrucciones {codigo} índice {i}: "
                    f"tupla de {len(s)} elementos, esperado 3"
                )

    def test_cada_seccion_tiene_seccion_titulo_contenido(self, instrucciones):
        for codigo, secciones in instrucciones.items():
            for s in secciones:
                seccion, titulo, contenido = s
                assert isinstance(seccion, str), (
                    f"Instrucciones {codigo}: sección no es string"
                )
                assert seccion.strip(), (
                    f"Instrucciones {codigo}: sección vacía"
                )
                assert isinstance(titulo, str), (
                    f"Instrucciones {codigo} '{seccion}': título no es string"
                )
                assert titulo.strip(), (
                    f"Instrucciones {codigo} '{seccion}': título vacío"
                )
                assert isinstance(contenido, str), (
                    f"Instrucciones {codigo} '{seccion}': contenido no es string"
                )
                assert contenido.strip(), (
                    f"Instrucciones {codigo} '{seccion}': contenido vacío"
                )

    def test_modelos_clave_tienen_instrucciones(self, instrucciones, modelos):
        codigos_clave = {"100", "303", "200", "124", "216", "349"}
        codigos_presentes = {m[0] for m in modelos}
        for c in codigos_clave:
            if c in codigos_presentes:
                assert c in instrucciones, (
                    f"Modelo clave '{c}' no tiene instrucciones"
                )


# ── OBLIGACIONES ─────────────────────────────────────────────────────────────


class TestObligaciones:
    def test_es_una_lista(self, obligaciones):
        assert isinstance(obligaciones, list)

    def test_minimo_20_obligaciones(self, obligaciones):
        assert len(obligaciones) >= 20, (
            f"Se esperan >= 20 obligaciones, hay {len(obligaciones)}"
        )

    def test_cada_elemento_tiene_30_o_31_campos(self, obligaciones):
        for i, o in enumerate(obligaciones):
            assert len(o) in (30, 31), (
                f"Obligación índice {i}: {len(o)} campos, esperado 30 o 31"
            )

    def test_codigos_unicos(self, obligaciones):
        codigos = [o[0] for o in obligaciones]
        assert len(codigos) == len(set(codigos)), (
            "Hay códigos duplicados en OBLIGACIONES"
        )

    def test_nombres_no_vacios(self, obligaciones):
        for i, o in enumerate(obligaciones):
            assert o[1].strip(), f"Obligación índice {i}: nombre vacío"

    def test_periodicidades_validas(self, obligaciones):
        validas = {
            "mensual", "trimestral", "anual",
            "mensual/trimestral", "cuando-varia", "evento",
        }
        for i, o in enumerate(obligaciones):
            assert o[6] in validas, (
                f"Obligación índice {i}: periodicidad '{o[6]}' no válida"
            )

    def test_reporte_modelo_no_vacio(self, obligaciones):
        for i, o in enumerate(obligaciones):
            assert o[7].strip(), (
                f"Obligación índice {i}: reporte_modelo vacío"
            )

    def test_obligaciones_nuevas_tienen_codigos_unicos(self, obligaciones):
        nuevos_codigos = {
            "IRPF_RETRIBUCIONES", "IRNR_ACTIVIDADES", "IRNR_DIVIDENDOS",
            "RESUMEN_SII", "BIENES_EXTRANJERO", "IS_NO_RESIDENTES",
            "RETRIBUCIONES_ANUAL", "OPS_ADUANERAS", "IRNR_ACTIV_ANUAL",
            "IRNR_PROVEEDORES", "IS_TRAMO_ESTATAL", "FACTA_NC_INTRACOM",
            "OPS_ART79_4",
        }
        codigos_presentes = {o[0] for o in obligaciones}
        for c in nuevos_codigos:
            assert c in codigos_presentes, (
                f"Obligación '{c}' ausente en OBLIGACIONES"
            )


# ── main() estructura ────────────────────────────────────────────────────────


class TestMainStructure:
    def test_main_existe(self, seed_module):
        assert callable(seed_module.main)

    def test_models_with_campaign_cubre_modelos(self, seed_module):
        """models_with_campaign debe cubrir todos los modelos del seed."""
        # Leemos el código fuente directamente para verificar
        src = TARGET.read_text(encoding="utf-8")
        assert "models_with_campaign" in src
        # Verificar que los modelos clave están en la lista
        for codigo in ["100", "303", "124", "216", "349", "200"]:
            assert f'"{codigo}"' in src, (
                f"Modelo '{codigo}' no encontrado en src"
            )


# ── Integración con DB (si está disponible) ──────────────────────────────────


class TestSeedIntegration:
    """Tests de integración con BD (marcados como slow, se saltan sin DB)."""

    @pytest.fixture(scope="class")
    def db_available(self):
        """Verifica si la BD está disponible."""
        try:
            import psycopg
            conn = psycopg.connect("postgresql://esdata:esdata_dev@postgres:5432/esdata", timeout=5)
            conn.close()
            return True
        except Exception:
            return False

    @pytest.mark.skip(reason="Requires running PostgreSQL")
    def test_seed_inserta_modelos(self, db_available):
        if not db_available:
            pytest.skip("No database available")
        import psycopg
        conn = psycopg.connect("postgresql://esdata:esdata_dev@postgres:5432/esdata")
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM aeat_modelo")
        count = cur.fetchone()[0]
        assert count >= 30, f"Esperamos >= 30 modelos en DB, hay {count}"
        conn.close()

    @pytest.mark.skip(reason="Requires running PostgreSQL")
    def test_seed_inserta_obligaciones(self, db_available):
        if not db_available:
            pytest.skip("No database available")
        import psycopg
        conn = psycopg.connect("postgresql://esdata:esdata_dev@postgres:5432/esdata")
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM obligacion_regulatoria")
        count = cur.fetchone()[0]
        assert count >= 20, f"Esperamos >= 20 obligaciones en DB, hay {count}"
        conn.close()
