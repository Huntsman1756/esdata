#!/usr/bin/env python3
"""Seed tablas vacias restantes con datos fixture minimos para desarrollo local.

Cubre: ai_audit_log, ai_model_registry, consumer_credit_overindebtedness,
eval_run, eval_query, giin_registry, human_review, nota_editorial_interna,
prueba_control, query_audit_log, xbrl_taxonomy.

Uso:
    python scripts/data/seed_empty_tables.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

# ── ai_audit_log ──────────────────────────────────────────────────────────
AUDIT_LOGS = [
    {
        "request_id": "req-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "timestamp": "2026-04-29T10:15:30.123456+00:00",
        "componente": "retrieval",
        "accion": "query_documents",
        "configuracion": '{"model": "gpt-4", "top_k": 5, "grounding_threshold": 0.4}',
        "resultado_resumen": "Recuperados 5 documentos relevantes para consulta IRPF 2025",
        "latencia_ms": 234.5,
        "user_id": "user-dev-001",
        "ip_address": "192.168.1.100",
    },
    {
        "request_id": "req-b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "timestamp": "2026-04-29T11:22:45.654321+00:00",
        "componente": "ai_router",
        "accion": "generate_response",
        "configuracion": '{"model": "claude-3.5", "temperature": 0.1, "grounding": true}',
        "resultado_resumen": "Respuesta generada con 3 citas documentales",
        "latencia_ms": 1456.2,
        "user_id": "user-dev-002",
        "ip_address": "10.0.0.50",
        "error": None,
    },
]

# ── ai_model_registry ─────────────────────────────────────────────────────
AI_MODELS = [
    {
        "model_id": "gpt-4-0125-preview",
        "nombre": "GPT-4 Turbo",
        "version": "2024-01-25",
        "tipo": "chat",
        "proveedor": "openai",
        "hash_modelo": "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        "descripcion": "Modelo principal para respuestas con grounding",
        "fecha_despliegue": "2026-01-15",
        "activo": True,
        "configuracion": '{"max_tokens": 4096, "temperature": 0.1, "top_p": 0.9}',
    },
    {
        "model_id": "claude-3-5-sonnet-20241022",
        "nombre": "Claude 3.5 Sonnet",
        "version": "2024-10-22",
        "tipo": "chat",
        "proveedor": "anthropic",
        "hash_modelo": "sha256:b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
        "descripcion": "Modelo secundario para consultas complejas de derecho tributario",
        "fecha_despliegue": "2026-02-01",
        "activo": True,
        "configuracion": '{"max_tokens": 8192, "temperature": 0.1, "top_p": 0.95}',
    },
    {
        "model_id": "text-embedding-3-small",
        "nombre": "Text Embedding 3 Small",
        "version": "2024-01-15",
        "tipo": "embedding",
        "proveedor": "openai",
        "hash_modelo": "sha256:c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
        "descripcion": "Embeddings para busqueda semantica",
        "fecha_despliegue": "2026-01-10",
        "activo": True,
        "configuracion": '{"dimensions": 512}',
    },
]

# ── consumer_credit_overindebtedness ──────────────────────────────────────
OVERINDEBTEDNESS = [
    {
        "borrower_id": 1,
        "declared_date": "2025-11-15",
        "total_debt": 125000.00,
        "monthly_income": 2800.00,
        "unsecured_debt": 85000.00,
        "procedure_status": "declared",
        "court_reference": "Juzgado de lo Mercantil 3 de Madrid — Expediente 145/2025",
    },
    {
        "borrower_id": 2,
        "declared_date": "2026-01-20",
        "total_debt": 67500.00,
        "monthly_income": 1950.00,
        "unsecured_debt": 42000.00,
        "procedure_status": "in_progress",
        "court_reference": "Juzgado de lo Mercantil 5 de Barcelona — Expediente 89/2026",
    },
    {
        "borrower_id": 3,
        "declared_date": "2026-03-05",
        "total_debt": 210000.00,
        "monthly_income": 3200.00,
        "unsecured_debt": 150000.00,
        "procedure_status": "approved",
        "court_reference": "Juzgado de lo Mercantil 1 de Valencia — Expediente 22/2026",
    },
]

# ── eval_run ──────────────────────────────────────────────────────────────
EVAL_RUNS = [
    {
        "api_url": "http://localhost:8000",
        "golden_version": "v1.2.0",
        "global_score": 0.847,
        "total_queries": 50,
        "total_failures": 8,
        "source_hit_rate": 0.92,
        "avg_latency_ms": 345.6,
    },
    {
        "api_url": "http://localhost:8000",
        "golden_version": "v1.1.0",
        "global_score": 0.723,
        "total_queries": 50,
        "total_failures": 15,
        "source_hit_rate": 0.86,
        "avg_latency_ms": 412.3,
    },
]

# ── eval_query ────────────────────────────────────────────────────────────
EVAL_QUERIES = [
    {
        "query_id": "eq-001",
        "dominio": "irpf",
        "pregunta": "Cual es el tipo de retencion para rendimientos del capital mobiliario en 2025?",
        "score_compuesto": 0.95,
        "acierto_fuente": True,
        "acierto_articulo": True,
        "acierto_vigencia": True,
        "chunk_precision": 0.92,
        "recall_top3": True,
        "recall_top5": True,
        "posicion_fuente": 1,
        "acierto_doctrina": True,
        "acierto_modelo": True,
        "falla": False,
        "latencia_consulta_ms": 120.5,
        "latencia_buscar_ms": 85.3,
        "latencia_doctrina_ms": 45.2,
        "fuentes_encontradas": "BOE-A-2006-18559,BOE-A-2014-12611",
        "fuentes_esperadas": "BOE-A-2006-18559",
        "articulos_encontrados": "Art. 44 LIRPF, Art. 17 LIS",
    },
    {
        "query_id": "eq-002",
        "dominio": "iva",
        "pregunta": "Que tipos impositivos del IVA aplican a entregas de bienes en 2025?",
        "score_compuesto": 0.88,
        "acierto_fuente": True,
        "acierto_articulo": True,
        "acierto_vigencia": True,
        "chunk_precision": 0.85,
        "recall_top3": True,
        "recall_top5": True,
        "posicion_fuente": 2,
        "acierto_doctrina": False,
        "acierto_modelo": True,
        "falla": False,
        "latencia_consulta_ms": 98.7,
        "latencia_buscar_ms": 67.1,
        "latencia_doctrina_ms": 120.4,
        "fuentes_encontradas": "BOE-A-1992-2880",
        "fuentes_esperadas": "BOE-A-1992-2880",
        "articulos_encontrados": "Art. 71-77 LIVA",
    },
    {
        "query_id": "eq-003",
        "dominio": "is",
        "pregunta": "Cual es el tipo general del Impuesto sobre Sociedades en 2025?",
        "score_compuesto": 0.72,
        "acierto_fuente": True,
        "acierto_articulo": False,
        "acierto_vigencia": True,
        "chunk_precision": 0.68,
        "recall_top3": False,
        "recall_top5": True,
        "posicion_fuente": 4,
        "acierto_doctrina": False,
        "acierto_modelo": False,
        "falla": True,
        "latencia_consulta_ms": 234.1,
        "latencia_buscar_ms": 156.8,
        "latencia_doctrina_ms": 200.5,
        "fuentes_encontradas": "BOE-A-2014-12611",
        "fuentes_esperadas": "BOE-A-2014-12611",
        "articulos_encontrados": "Art. 2 LIS",
    },
]

# ── giin_registry ─────────────────────────────────────────────────────────
GIIN_ENTRIES = [
    {
        "giin": "GJIIJN4MIB1GZA3Y4N14",
        "entidad_nombre": "Banco Sabadell, S.A.",
        "entidad_pais": "ES",
        "tipo_entidad": "Financial Institution",
        "estado_fatca": "active",
        "fecha_registro": "2020-03-15",
        "fecha_expiracion": "2027-03-15",
        "es_exempt_beneficial_owner": False,
        "es_sponsored_ffo": False,
        "nota": "Entidad reportante activa — modelo 01",
    },
    {
        "giin": "GJIIES7890ABCDEF1234",
        "entidad_nombre": "Bankinter, S.A.",
        "entidad_pais": "ES",
        "tipo_entidad": "Financial Institution",
        "estado_fatca": "active",
        "fecha_registro": "2019-07-22",
        "fecha_expiracion": "2026-07-22",
        "es_exempt_beneficial_owner": False,
        "es_sponsored_ffo": False,
        "nota": "Entidad reportante activa — modelo 04",
    },
    {
        "giin": "GJIIPT5678XYZW901234",
        "entidad_nombre": "Millennium BCP, S.A.",
        "entidad_pais": "PT",
        "tipo_entidad": "Financial Institution",
        "estado_fatca": "active",
        "fecha_registro": "2021-01-10",
        "fecha_expiracion": "2028-01-10",
        "es_exempt_beneficial_owner": True,
        "es_sponsored_ffo": False,
        "nota": "Exempt beneficial owner — cuentas exentas art. 2.15",
    },
]

# ── human_review ──────────────────────────────────────────────────────────
HUMAN_REVIEWS = [
    {
        "review_id": "rev-001",
        "request_id": "req-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "decision_type": "grounding_check",
        "ai_response_id": "resp-001",
        "status": "approved",
        "reviewer_id": "reviewer-admin-001",
        "action": "publish",
        "notes": "Citas verificadas — todas las afirmaciones factuales tienen respaldo documental",
        "confidence_threshold": 0.8,
        "ai_confidence": 0.92,
        "required_for": "irpf_retencion_dividendos",
        "created_at": "2026-04-29T10:20:00+00:00",
        "reviewed_at": "2026-04-29T10:25:00+00:00",
        "metadata": '{"model": "gpt-4", "chunks_reviewed": 5, "claims_verified": 3}',
    },
    {
        "review_id": "rev-002",
        "request_id": "req-b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "decision_type": "content_safety",
        "ai_response_id": "resp-002",
        "status": "rejected",
        "reviewer_id": "reviewer-admin-001",
        "action": "request_revision",
        "notes": "Falta cita para afirmacion sobre tipo IRNR en convenios DTA — requiere actualizacion",
        "confidence_threshold": 0.85,
        "ai_confidence": 0.65,
        "required_for": "irnr_convenios",
        "created_at": "2026-04-29T11:30:00+00:00",
        "reviewed_at": "2026-04-29T11:45:00+00:00",
        "metadata": '{"model": "claude-3.5", "chunks_reviewed": 8, "claims_verified": 2, "claims_failed": 1}',
    },
]

# ── nota_editorial_interna ────────────────────────────────────────────────
NOTAS_EDITORIALES = [
    {
        "titulo": "Nueva reduccion del tipo IS para startups — analisis de impacto",
        "resumen_ejecutivo": "La Ley 28/2025 introduce un tipo reducido del 15% para startups qualificadas durante los primeros 3 ejercicios. Este documento analiza el impacto en la base de datos y las consultas relevantes.",
        "contexto": "Reforma fiscal aprobada en Consejo de Ministros del 15/03/2025. Entrada en vigor: 01/01/2026.",
        "impacto_practico": "Aplicable a entidades que cumplan definicion art. 34 LIS (modificado). Afecta a ~2.300 entidades en España.",
        "advertencias": "Pendiente de desarrollo reglamentario. Tipo reducido no aplicable a entidades con actividad financiera.",
        "fuente_oficial_referencia": "BOE-A-2025-4567",
        "documento_origen_id": 1,
        "autor_id": "editor-admin-001",
        "estado": "revision",
        "tipo_contenido": "analisis_impacto",
        "fecha_creacion": "2026-04-20",
        "fecha_revision": None,
    },
    {
        "titulo": "Actualizacion tablas IRPF 2026 — cambios en tramos autonomicos",
        "resumen_ejecutivo": "Las CCAA de Madrid, Cataluña y Andalucia han publicado sus ordenanzas fiscales para 2026 con cambios significativos en los tramos autonomicos del IRPF.",
        "contexto": "Publicacion de ordenanzas fiscales 2026 por parte de las principales CCAA. Plazo de presentacion: enero 2026.",
        "impacto_practico": "Afecta a autoliquidaciones IRPF 2026. Las tablas de irpf_brackets necesitan actualizacion en 3 jurisdicciones.",
        "advertencias": "Verificar vigencia con BOE oficial antes de publicar. Algunas CCAA mantienen tramos sin cambios.",
        "fuente_oficial_referencia": "BOE-A-2025-8901",
        "documento_origen_id": 2,
        "autor_id": "editor-admin-001",
        "revisor_id": "editor-admin-002",
        "estado": "borrador",
        "tipo_contenido": "actualizacion_tablas",
        "fecha_creacion": "2026-04-25",
        "fecha_revision": None,
    },
]

# ── prueba_control ────────────────────────────────────────────────────────
PRUEBAS_CONTROL = [
    {
        "link_id": 1,
        "fecha_prueba": "2026-04-01",
        "resultado": "pass",
        "evidencia_descripcion": "Verificacion de RLS en tabla documentos — access denied para usuario anonimo confirmado",
        "evidencia_url": None,
        "ejecutado_por": "security-audit-001",
        "nota": "Control de seguridad S-TIER — Regla 2 (RLS)",
        "activo": True,
    },
    {
        "link_id": 2,
        "fecha_prueba": "2026-04-10",
        "resultado": "pass",
        "evidencia_descripcion": "Validacion de esquema Pydantic en endpoint PUT /v1/mica/crypto-assets — mass assignment bloqueado",
        "evidencia_url": None,
        "ejecutado_por": "security-audit-001",
        "nota": "Control de seguridad S-TIER — Regla 3 (Mass assignment)",
        "activo": True,
    },
    {
        "link_id": 3,
        "fecha_prueba": "2026-04-15",
        "resultado": "fail",
        "evidencia_descripcion": "Webhook de prueba sin verificacion de firma — identificado en Fase 42, fix en progreso",
        "evidencia_url": None,
        "ejecutado_por": "security-audit-001",
        "nota": "Control de seguridad S-TIER — Regla 5 (Webhook signatures) — pendiente fix",
        "activo": True,
    },
]

# ── query_audit_log ───────────────────────────────────────────────────────
QUERY_AUDIT_LOGS = [
    {
        "entry_id": "entry-001",
        "request_id": "req-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "user_id": "user-dev-001",
        "path": "/api/v1/search",
        "query_text": "tipo retencion dividendos IRPF 2025",
        "retrieved_chunks": '[{"doc_id": 1, "chunk": 3, "score": 0.92}, {"doc_id": 2, "chunk": 1, "score": 0.87}]',
        "response_summary": "Tipo de retencion 19% para dividendos nacionales, 24% para no residentes",
        "model_version": "gpt-4-0125-preview",
        "config_version": "v0001",
        "created_at": "2026-04-29T10:15:30+00:00",
        "grounding_status": "grounded",
        "grounding_summary": '{"total_claims": 3, "grounded_claims": 3, "ungrounded_claims": 0}',
    },
    {
        "entry_id": "entry-002",
        "request_id": "req-b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "user_id": "user-dev-002",
        "path": "/api/v1/consulta",
        "query_text": "tipo IS startups 2026",
        "retrieved_chunks": '[{"doc_id": 5, "chunk": 0, "score": 0.88}]',
        "response_summary": "Tipo reducido 15% para startups qualificadas desde 01/01/2026",
        "model_version": "claude-3-5-sonnet-20241022",
        "config_version": "v0001",
        "created_at": "2026-04-29T11:22:45+00:00",
        "grounding_status": "partially_grounding",
        "grounding_summary": '{"total_claims": 2, "grounded_claims": 1, "ungrounded_claims": 1}',
    },
]

# ── xbrl_taxonomy ─────────────────────────────────────────────────────────
XBRL_TAXONOMY = [
    # ESEF Core — Balance Sheet (EN)
    {"concept_qname": "esga:TotalAssets", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Total Assets", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalLiabilities", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Total Liabilities", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalEquity", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Total Equity", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    # ESEF Core — Income Statement (EN)
    {"concept_qname": "esga:NetIncome", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Net Income", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:OperatingRevenue", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Operating Revenue", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
    # ESEF Core — Banking (EN)
    {"concept_qname": "esga:LoanPortfolio", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Loan Portfolio", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:CustomerDeposits", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Customer Deposits", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:CommonEquityTier1Ratio", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Common Equity Tier 1 Ratio", "label_language": "en", "label_role": "label", "standard": "ESEF", "data_type": "xbrli:pureItemType", "period_type": "instant", "is_monetary": False, "is_negative_allowed": False},
    # IFRS labels (ES)
    {"concept_qname": "esga:TotalAssets", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Activo Total", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalLiabilities", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Pasivo Total", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:TotalEquity", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Patrimonio Neto Total", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "instant", "is_monetary": True, "is_negative_allowed": True},
    {"concept_qname": "esga:NetIncome", "namespace": "http://esg.esef.eu/2021/arcrole/de", "label": "Resultado Neto", "label_language": "es", "label_role": "label", "standard": "IFRS", "data_type": "xbrli:monetaryItemType", "period_type": "duration", "is_monetary": True, "is_negative_allowed": True},
]


def upsert_audit_log(cur, row):
    cur.execute(
        """INSERT INTO ai_audit_log (request_id, timestamp, componente, accion,
           configuracion, resultado_resumen, latencia_ms, error, user_id, ip_address)
           VALUES (%s, %s, %s, %s, %s::json, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["request_id"], row["timestamp"], row["componente"], row["accion"],
         row["configuracion"], row["resultado_resumen"], row["latencia_ms"],
         row.get("error"), row.get("user_id"), row.get("ip_address")),
    )


def upsert_ai_model(cur, row):
    cur.execute(
        """INSERT INTO ai_model_registry (model_id, nombre, version, tipo, proveedor,
           hash_modelo, descripcion, fecha_despliegue, activo, configuracion)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::json)
           ON CONFLICT (model_id) DO UPDATE SET
               nombre = EXCLUDED.nombre, version = EXCLUDED.version, activo = EXCLUDED.activo""",
        (row["model_id"], row["nombre"], row["version"], row["tipo"],
         row["proveedor"], row["hash_modelo"], row.get("descripcion"),
         row["fecha_despliegue"], row["activo"], row.get("configuracion")),
    )


def upsert_overindebtedness(cur, row):
    cur.execute(
        """INSERT INTO consumer_credit_overindebtedness (borrower_id, declared_date,
           total_debt, monthly_income, unsecured_debt, procedure_status, court_reference)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["borrower_id"], row.get("declared_date"), row.get("total_debt"),
         row.get("monthly_income"), row.get("unsecured_debt"),
         row["procedure_status"], row.get("court_reference")),
    )


def upsert_eval_run(cur, row):
    cur.execute(
        """INSERT INTO eval_run (api_url, golden_version, global_score, total_queries,
           total_failures, source_hit_rate, avg_latency_ms)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING
           RETURNING id""",
        (row["api_url"], row["golden_version"], row["global_score"],
         row["total_queries"], row["total_failures"],
         row["source_hit_rate"], row["avg_latency_ms"]),
    )
    return cur.fetchone()[0]


def upsert_eval_query(cur, row, run_id):
    cur.execute(
        """INSERT INTO eval_query (id, run_id, query_id, dominio, pregunta,
           score_compuesto, acierto_fuente, acierto_articulo, acierto_vigencia,
           chunk_precision, recall_top3, recall_top5, posicion_fuente,
           acierto_doctrina, acierto_modelo, falla, latencia_consulta_ms,
           latencia_buscar_ms, latencia_doctrina_ms, fuentes_encontradas,
           fuentes_esperadas, articulos_encontrados)
           VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s,
                   %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (run_id, row["query_id"], row["dominio"], row["pregunta"],
         row.get("score_compuesto"), row.get("acierto_fuente"),
         row.get("acierto_articulo"), row.get("acierto_vigencia"),
         row.get("chunk_precision"), row.get("recall_top3"),
         row.get("recall_top5"), row.get("posicion_fuente"),
         row.get("acierto_doctrina"), row.get("acierto_modelo"),
         row.get("falla"), row.get("latencia_consulta_ms"),
         row.get("latencia_buscar_ms"), row.get("latencia_doctrina_ms"),
         row.get("fuentes_encontradas"), row.get("fuentes_esperadas"),
         row.get("articulos_encontrados")),
    )


def upsert_giin(cur, row):
    cur.execute(
        """INSERT INTO giin_registry (giin, entidad_nombre, entidad_pais, tipo_entidad,
           estado_fatca, fecha_registro, fecha_expiracion, es_exempt_beneficial_owner,
           es_sponsored_ffo, nota)
           VALUES (%(giin)s, %(entidad_nombre)s, %(entidad_pais)s, %(tipo_entidad)s,
                   %(estado_fatca)s, %(fecha_registro)s, %(fecha_expiracion)s,
                   %(es_exempt_beneficial_owner)s, %(es_sponsored_ffo)s, %(nota)s)
           ON CONFLICT (giin) DO UPDATE SET
               entidad_nombre = EXCLUDED.entidad_nombre,
               estado_fatca = EXCLUDED.estado_fatca""",
        row,
    )


def upsert_human_review(cur, row):
    cur.execute(
        """INSERT INTO human_review (review_id, request_id, decision_type, ai_response_id,
           status, reviewer_id, action, notes, confidence_threshold, ai_confidence,
           required_for, created_at, reviewed_at, metadata)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (review_id) DO UPDATE SET
               status = EXCLUDED.status, notes = EXCLUDED.notes""",
        (row["review_id"], row["request_id"], row["decision_type"],
         row.get("ai_response_id"), row["status"], row.get("reviewer_id"),
         row.get("action"), row.get("notes"), row["confidence_threshold"],
         row["ai_confidence"], row.get("required_for"), row["created_at"],
         row.get("reviewed_at"), row.get("metadata", "{}")),
    )


def upsert_nota_editorial(cur, row):
    cur.execute(
        """INSERT INTO nota_editorial_interna (id, titulo, resumen_ejecutivo, contexto,
           impacto_practico, advertencias, fuente_oficial_referencia, documento_origen_id,
           autor_id, revisor_id, estado, tipo_contenido, fecha_creacion, fecha_revision)
           VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["titulo"], row.get("resumen_ejecutivo"), row.get("contexto"),
         row.get("impacto_practico"), row.get("advertencias"),
         row.get("fuente_oficial_referencia"), row.get("documento_origen_id"),
         row["autor_id"], row.get("revisor_id"), row["estado"],
         row.get("tipo_contenido"), row["fecha_creacion"], row.get("fecha_revision")),
    )


def upsert_prueba_control(cur, row):
    cur.execute(
        """INSERT INTO prueba_control (link_id, fecha_prueba, resultado,
           evidencia_descripcion, evidencia_url, ejecutado_por, nota, activo)
           VALUES (%(link_id)s, %(fecha_prueba)s, %(resultado)s,
                   %(evidencia_descripcion)s, %(evidencia_url)s, %(ejecutado_por)s,
                   %(nota)s, %(activo)s)
           ON CONFLICT DO NOTHING""",
        row,
    )


def upsert_query_audit(cur, row):
    cur.execute(
        """INSERT INTO query_audit_log (entry_id, request_id, user_id, path, query_text,
           retrieved_chunks, response_summary, model_version, config_version, created_at,
           grounding_status, prompt_injection_detected, grounding_summary)
           VALUES (%s, %s, %s, %s, %s, %s::json, %s, %s, %s, %s, %s, %s, %s::text)
           ON CONFLICT DO NOTHING""",
        (row["entry_id"], row["request_id"], row.get("user_id"), row["path"],
         row["query_text"], row["retrieved_chunks"], row.get("response_summary"),
         row.get("model_version"), row.get("config_version"), row["created_at"],
         row.get("grounding_status"), row.get("prompt_injection_detected", 0),
         row.get("grounding_summary")),
    )


def upsert_taxonomy(cur, row):
    cur.execute(
        """INSERT INTO xbrl_taxonomy (concept_qname, namespace, label, label_language,
           label_role, standard, data_type, period_type, is_monetary, is_negative_allowed)
           VALUES (%(concept_qname)s, %(namespace)s, %(label)s, %(label_language)s,
                   %(label_role)s, %(standard)s, %(data_type)s, %(period_type)s,
                   %(is_monetary)s, %(is_negative_allowed)s)
           ON CONFLICT (concept_qname, label_language, label_role) DO UPDATE SET
               standard = EXCLUDED.standard,
               data_type = EXCLUDED.data_type,
               period_type = EXCLUDED.period_type,
               is_monetary = EXCLUDED.is_monetary,
               is_negative_allowed = EXCLUDED.is_negative_allowed""",
        row,
    )


def main():
    parser = argparse.ArgumentParser(description="Seed empty tables with fixture data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        counts = {
            "ai_audit_log": len(AUDIT_LOGS),
            "ai_model_registry": len(AI_MODELS),
            "consumer_credit_overindebtedness": len(OVERINDEBTEDNESS),
            "eval_run": len(EVAL_RUNS),
            "eval_query": len(EVAL_QUERIES),
            "giin_registry": len(GIIN_ENTRIES),
            "human_review": len(HUMAN_REVIEWS),
            "nota_editorial_interna": len(NOTAS_EDITORIALES),
            "prueba_control": len(PRUEBAS_CONTROL),
            "query_audit_log": len(QUERY_AUDIT_LOGS),
            "xbrl_taxonomy": len(XBRL_TAXONOMY),
        }
        total = sum(counts.values())
        print(f"[DRY RUN] Would insert {total} rows across {len(counts)} tables:")
        for table, count in counts.items():
            print(f"  {table}: {count}")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # 1. ai_audit_log
    for row in AUDIT_LOGS:
        upsert_audit_log(cur, row)
    print(f"  ai_audit_log: {len(AUDIT_LOGS)} rows")

    # 2. ai_model_registry
    for row in AI_MODELS:
        upsert_ai_model(cur, row)
    print(f"  ai_model_registry: {len(AI_MODELS)} rows")

    # 3. consumer_credit_overindebtedness
    for row in OVERINDEBTEDNESS:
        upsert_overindebtedness(cur, row)
    print(f"  consumer_credit_overindebtedness: {len(OVERINDEBTEDNESS)} rows")

    # 4. eval_run (parent of eval_query)
    run_ids = []
    for row in EVAL_RUNS:
        run_id = upsert_eval_run(cur, row)
        run_ids.append(run_id)
    print(f"  eval_run: {len(EVAL_RUNS)} rows")

    # 5. eval_query (depends on eval_run)
    for i, row in enumerate(EVAL_QUERIES):
        run_id = run_ids[i % len(run_ids)]
        upsert_eval_query(cur, row, run_id)
    print(f"  eval_query: {len(EVAL_QUERIES)} rows")

    # 6. giin_registry
    for row in GIIN_ENTRIES:
        upsert_giin(cur, row)
    print(f"  giin_registry: {len(GIIN_ENTRIES)} rows")

    # 7. human_review
    for row in HUMAN_REVIEWS:
        upsert_human_review(cur, row)
    print(f"  human_review: {len(HUMAN_REVIEWS)} rows")

    # 8. nota_editorial_interna
    for row in NOTAS_EDITORIALES:
        upsert_nota_editorial(cur, row)
    print(f"  nota_editorial_interna: {len(NOTAS_EDITORIALES)} rows")

    # 9. prueba_control
    for row in PRUEBAS_CONTROL:
        upsert_prueba_control(cur, row)
    print(f"  prueba_control: {len(PRUEBAS_CONTROL)} rows")

    # 10. query_audit_log
    for row in QUERY_AUDIT_LOGS:
        upsert_query_audit(cur, row)
    print(f"  query_audit_log: {len(QUERY_AUDIT_LOGS)} rows")

    # 11. xbrl_taxonomy
    for row in XBRL_TAXONOMY:
        upsert_taxonomy(cur, row)
    print(f"  xbrl_taxonomy: {len(XBRL_TAXONOMY)} rows")

    conn.commit()
    total = sum([
        len(AUDIT_LOGS), len(AI_MODELS), len(OVERINDEBTEDNESS),
        len(EVAL_RUNS), len(EVAL_QUERIES), len(GIIN_ENTRIES),
        len(HUMAN_REVIEWS), len(NOTAS_EDITORIALES), len(PRUEBAS_CONTROL),
        len(QUERY_AUDIT_LOGS), len(XBRL_TAXONOMY),
    ])
    print(f"OK: {total} rows inserted across {11} tables")
    conn.close()


if __name__ == "__main__":
    main()
