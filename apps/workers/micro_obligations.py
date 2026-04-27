"""Worker seed para micro-obligaciones Fase 20.

Carga la taxonomia de micro-obligaciones MiFID/CNMV/SEPBLAC en la tabla
micro_obligacion y el mapeo N:M en obligacion_micro_obligacion.

Es idempotente: re-ejecucion produce 0 inserts.

Uso:
    python -m apps.workers.micro_obligations --run-once
    python -m apps.workers.micro_obligations --interval 3600
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from db import get_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Seed de micro-obligaciones
MICRO_OBLIGACIONES = [
    # MiFID II
    {
        "codigo": "MIFID_SUITABILITY",
        "nombre": "Evaluacion de adecuacion",
        "descripcion": "Evaluar si el producto/inversion es adecuado al perfil del cliente (art. 53 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "alta_satisfaccion",
        "frecuencia": "eventual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "MIFID_APPROPRIATENESS",
        "nombre": "Evaluacion de conveniencia",
        "descripcion": "Evaluar conocimientos y experiencia del cliente (art. 54 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "alta_satisfaccion",
        "frecuencia": "inicial",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "MIFID_BEST_EXECUTION",
        "nombre": "Ejecucion preferente",
        "descripcion": "Obtener resultado mejor posible para cliente (art. 61 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "solicitud_ordenes",
        "frecuencia": "continua",
        "owner_rol": "trading",
        "severidad": "alta",
    },
    {
        "codigo": "MIFID_CONFLICTS",
        "nombre": "Gestion de conflictos de interes",
        "descripcion": "Identificar y gestionar conflictos de interes (art. 59 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "continuo",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "MIFID_INDUCEMENTS",
        "nombre": "Inducimientos",
        "descripcion": "Registrar y gestionar inducements (art. 63 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "recepcion_inducement",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "media",
    },
    {
        "codigo": "MIFID_PRODUCT_GOVERNANCE",
        "nombre": "Gobierno de productos",
        "descripcion": "Diseñar y distribuir productos con alcance destino (art. 98 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "diseno_producto",
        "frecuencia": "continua",
        "owner_rol": "producto",
        "severidad": "alta",
    },
    {
        "codigo": "MIFIR_REPORTING",
        "nombre": "Reporte MiFIR",
        "descripcion": "Reportar operaciones transaccion en tiempo real (Reg. 1287/2014)",
        "regulacion_relacionada": "mifir",
        "ambito": "mercados",
        "trigger_evento": "ejecucion_orden",
        "frecuencia": "en_tiempo_real",
        "owner_rol": "reporting",
        "severidad": "alta",
    },
    {
        "codigo": "MIFID_INSIDER_LIST",
        "nombre": "Listas de inside",
        "descripcion": "Crear y mantener listas de personas con informacion privilegiada (art. 66 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "acceso_info_privilegiada",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "MIFID_ORDER_RECORD",
        "nombre": "Registro de ordenes",
        "descripcion": "Registrar y archivar ordenes (art. 23 RDM)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "ejecucion_orden",
        "frecuencia": "continua",
        "owner_rol": "operaciones",
        "severidad": "media",
    },
    {
        "codigo": "MIFID_CLIENT_CATEGORIES",
        "nombre": "Categorias de cliente",
        "descripcion": "Clasificar cliente como minorista/profesional/institucional (art. 52 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "alta_satisfaccion",
        "frecuencia": "inicial",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "MIFID_COMPENSATION",
        "nombre": "Politica de compensacion",
        "descripcion": "Implementar politica de compensacion alineada con riesgos (art. 95 LMCV)",
        "regulacion_relacionada": "mifid_ii",
        "ambito": "mercados",
        "trigger_evento": "continuo",
        "frecuencia": "anual",
        "owner_rol": "rrhh",
        "severidad": "media",
    },
    {
        "codigo": "MIFID_MARKET_ABUSE",
        "nombre": "Deteccion abuso mercado",
        "descripcion": "Detectar y reportar operaciones sospechosas de abuso (art. 13 MAR)",
        "regulacion_relacionada": "mar",
        "ambito": "mercados",
        "trigger_evento": "operacion_sospechosa",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    # CNMV
    {
        "codigo": "CNMV_REPORTING_RESERVADO",
        "nombre": "Reporting reservado CNMV",
        "descripcion": "Comunicaciones confidenciales a CNMV (Disp Adic 4 LMCV)",
        "regulacion_relacionada": "cnmv_lmcv",
        "ambito": "reporting_regulatorio",
        "trigger_evento": "cambios_internos",
        "frecuencia": "eventual",
        "owner_rol": "secretaria",
        "severidad": "alta",
    },
    {
        "codigo": "CNMV_TRANSPARENCIA",
        "nombre": "Transparencia emisores",
        "descripcion": "Publicar informacion periodica de emisores (RDM)",
        "regulacion_relacionada": "cnmv_lmcv",
        "ambito": "reporting_regulatorio",
        "trigger_evento": "periodicidad",
        "frecuencia": "trimestral",
        "owner_rol": "comercial",
        "severidad": "alta",
    },
    {
        "codigo": "CNMV_GOBIERNO_CORP",
        "nombre": "Gobierno corporativo",
        "descripcion": "Cumplir Codigo de Buen Gobierno (recomendaciones)",
        "regulacion_relacionada": "cnmv_lmcv",
        "ambito": "reporting_regulatorio",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "consejo",
        "severidad": "media",
    },
    {
        "codigo": "CNMV_OPS_INSTRUMENTOS_PROPIOS",
        "nombre": "Ops con instrumentos propios",
        "descripcion": "Cumplir restricciones operaciones con instrumentos propios (art. 116 TRLC)",
        "regulacion_relacionada": "cnmv_lmcv",
        "ambito": "mercados",
        "trigger_evento": "ejecucion_orden",
        "frecuencia": "continua",
        "owner_rol": "trading",
        "severidad": "alta",
    },
    {
        "codigo": "CNMV_COMUNICACION_HECHOS_ESSENTIALS",
        "nombre": "Comunicacion hechos relevantes",
        "descripcion": "Comunicacion hechos relevantes en tiempo real (art. 1 RDM)",
        "regulacion_relacionada": "cnmv_lmcv",
        "ambito": "reporting_regulatorio",
        "trigger_evento": "hecho_relevante",
        "frecuencia": "eventual",
        "owner_rol": "secretaria",
        "severidad": "alta",
    },
    {
        "codigo": "CNMV_REGISTRO_OPERACIONES_INSIDER",
        "nombre": "Registro operaciones insider",
        "descripcion": "Registrar operaciones de PPI (art. 19 MAR)",
        "regulacion_relacionada": "mar",
        "ambito": "mercados",
        "trigger_evento": "operacion_ppi",
        "frecuencia": "eventual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "CNMV_CONCILIACION",
        "nombre": "Conciliacion financiera",
        "descripcion": "Conciliacion periodica carteras clientes",
        "regulacion_relacionada": "cnmv_lmcv",
        "ambito": "reporting_regulatorio",
        "trigger_evento": "periodicidad",
        "frecuencia": "mensual",
        "owner_rol": "back_office",
        "severidad": "media",
    },
    {
        "codigo": "CNMV_DOCUMENTOS_INFORMACION",
        "nombre": "Documentos de informacion",
        "descripcion": "Elaborar y publicar DI (art. 10 RDM)",
        "regulacion_relacionada": "cnmv_lmcv",
        "ambito": "reporting_regulatorio",
        "trigger_evento": "periodicidad",
        "frecuencia": "continua",
        "owner_rol": "comercial",
        "severidad": "alta",
    },
    # SEPBLAC
    {
        "codigo": "SEPBLAC_KYC",
        "nombre": "Deber de diligencia debida",
        "descripcion": "Identificacion y verificacion cliente (RD 289/2022 art. 19)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "onboarding",
        "frecuencia": "inicial",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "SEPBLAC_MONITORING",
        "nombre": "Monitorizacion continua",
        "descripcion": "Monitorizacion continua de operaciones (RD 289/2022 art. 27)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "operacion",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "SEPBLAC_STR",
        "nombre": "Comunicacion de indicios STR",
        "descripcion": "Comunicar indicios de LP a SEPBLAC (art. 59 Ley 10/2010)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "indicio_lp",
        "frecuencia": "eventual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "SEPBLAC_SUSPENSION",
        "nombre": "Suspension operacion",
        "descripcion": "Suspender operacion si riesgo LP no mitigado (RD 289/2022 art. 23)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "riesgo_no_mitigado",
        "frecuencia": "eventual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "SEPBLAC_PEP_SCREENING",
        "nombre": "Screening PEP",
        "descripcion": "Verificar PEP en onboarding y periodicamente (RD 289/2022 art. 25)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "onboarding",
        "frecuencia": "inicial",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "SEPBLAC_RECORD_KEEPING",
        "nombre": "Conservacion documentos",
        "descripcion": "Conservar documentos identificacion 6 anos (RD 289/2022 art. 42)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "continuo",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "media",
    },
    {
        "codigo": "SEPBLAC_FORMACION",
        "nombre": "Formacion AML",
        "descripcion": "Formacion empleados prevencion LP (art. 7 Ley 10/2010)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "continuo",
        "frecuencia": "anual",
        "owner_rol": "rrhh",
        "severidad": "media",
    },
    {
        "codigo": "SEPBLAC_GOBIERNO_AML",
        "nombre": "Gobierno AML interno",
        "descripcion": "Implementar controles internos prevencion LP (art. 6 Ley 10/2010)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "continuo",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "SEPBLAC_MITIGACION",
        "nombre": "Politica mitigacion riesgos",
        "descripcion": "Politica de mitigacion de riesgos LP (art. 5 Ley 10/2010)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "continuo",
        "frecuencia": "anual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "SEPBLAC_REPORTE_ANUAL",
        "nombre": "Reporte anual SEPBLAC",
        "descripcion": "Presentar memoria anual de actividades (si aplica)",
        "regulacion_relacionada": "pblcft",
        "ambito": "aml_cft",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "compliance",
        "severidad": "media",
    },
    # LECR (Ley 22/2014 — Entidades Capital Riesgo)
    {
        "codigo": "LECR_ECR_REGISTRATION",
        "nombre": "Registro en ECR",
        "descripcion": "Registro en el Registro Central de Representantes de ECR (Ley 22/2014 arts. 1-12)",
        "regulacion_relacionada": "lecr",
        "ambito": "ecr_regulatorio",
        "trigger_evento": "constitucion",
        "frecuencia": "eventual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "LECR_SGEIC",
        "nombre": "Autorizacion SGEIC / Autogestion",
        "descripcion": "Autorizacion como SGEIC opcional (art. 26 LECR) o contratar SGEIC externo",
        "regulacion_relacionada": "lecr",
        "ambito": "ecr_regulatorio",
        "trigger_evento": "constitucion",
        "frecuencia": "eventual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "LECR_DIVERSIFICATION",
        "nombre": "Diversificacion ≥50% no cotizados",
        "descripcion": "Diversificacion de posiciones: ≥50% empresas no cotizadas (art. 26 LECR)",
        "regulacion_relacionada": "lecr",
        "ambito": "ecr_regulatorio",
        "trigger_evento": "periodicidad",
        "frecuencia": "trimestral",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "LECR_MIID_DIVERSIFICATION",
        "nombre": "Diversificacion MiID ≥50%",
        "descripcion": "Diversificacion MiID (art. 134 LECR) para fondos de inversion",
        "regulacion_relacionada": "lecr",
        "ambito": "ecr_regulatorio",
        "trigger_evento": "periodicidad",
        "frecuencia": "trimestral",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "LECR_CONDUCT_RULES",
        "nombre": "Reglas de conducta MiFID II",
        "descripcion": "Cumplir reglas de conducta MiFID II (arts. 53-63 LMCV) como ECR",
        "regulacion_relacionada": "lecr",
        "ambito": "ecr_regulatorio",
        "trigger_evento": "continuo",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "LECR_FISCAL_NON_RESIDENT",
        "nombre": "95% exencion dividendos no residentes",
        "descripcion": "Exencion 95% dividendos y plusvalias para no residentes (art. 21 Ley IS + art. 30 Ley 22/2014)",
        "regulacion_relacionada": "lecr",
        "ambito": "tributario",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "media",
    },
    # SOCIMI (Ley 11/2009)
    {
        "codigo": "SOCIMI_ASSET_COMPOSITION",
        "nombre": "≥80% activos inmobiliarios arrendados",
        "descripcion": "Mantener ≥80% del valor del activo en inmuebles arrendados (art. 3 Ley 11/2009)",
        "regulacion_relacionada": "socimi",
        "ambito": "societario_fiscal",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "alta",
    },
    {
        "codigo": "SOCIMI_DISTRIBUTION",
        "nombre": "≥80% distribucion de resultados",
        "descripcion": "Distribuir ≥80% de los resultados imponibles (art. 12 Ley 11/2009)",
        "regulacion_relacionada": "socimi",
        "ambito": "societario_fiscal",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "alta",
    },
    {
        "codigo": "SOCIMI_TAX_UNDISTRIBUTED",
        "nombre": "Gravamen 15-19% beneficios no distribuidos",
        "descripcion": "Gravamen 15-19% sobre beneficios no distribuidos (art. 24 Ley 11/2009)",
        "regulacion_relacionada": "socimi",
        "ambito": "tributario",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "media",
    },
    {
        "codigo": "SOCIMI_TAX_REGIME",
        "nombre": "Régimen fiscal SOCIMI 0% IS",
        "descripcion": "Aplicar régimen fiscal SOCIMI con tipo 0% si distribuye ≥80% beneficios (art. 23 Ley 11/2009)",
        "regulacion_relacionada": "socimi",
        "ambito": "tributario",
        "trigger_evento": "continuo",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "alta",
    },
    {
        "codigo": "SOCIMI_80_20_RULE",
        "nombre": "Regla 80/20 SOCIMI",
        "descripcion": "80% activo inmobiliario arrendado + 20% liquidez maxima (art. 3 Ley 11/2009)",
        "regulacion_relacionada": "socimi",
        "ambito": "societario_fiscal",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "alta",
    },
    # CSDR (Reglamento UE 909/2014)
    {
        "codigo": "CSDR_SETTLEMENT",
        "nombre": "T+2 settlement / T+1 inminente",
        "descripcion": "Cumplir T+2 settlement vigente, preparar T+1 (Reglamento 909/2014)",
        "regulacion_relacionada": "csdr",
        "ambito": "infraestructuras_csd",
        "trigger_evento": "ejecucion_orden",
        "frecuencia": "continua",
        "owner_rol": "operaciones",
        "severidad": "alta",
    },
    {
        "codigo": "CSDR_REPORTING",
        "nombre": "Segregacion y reporting CSDR",
        "descripcion": "Segregacion de posiciones y reporting a CSD (Reglamento 909/2014)",
        "regulacion_relacionada": "csdr",
        "ambito": "infraestructuras_csd",
        "trigger_evento": "periodicidad",
        "frecuencia": "mensual",
        "owner_rol": "reporting",
        "severidad": "alta",
    },
    {
        "codigo": "CSDR_SETTLEMENT_FAILURE",
        "nombre": "Gestion fallidos de settlement CSDR",
        "descripcion": "Gestion de fallidos de settlement y multas CSDR (Reglamento 909/2014)",
        "regulacion_relacionada": "csdr",
        "ambito": "infraestructuras_csd",
        "trigger_evento": "fallido_settlement",
        "frecuencia": "eventual",
        "owner_rol": "operaciones",
        "severidad": "alta",
    },
    # CNMV ECR (Estados Confidenciales Reservados)
    {
        "codigo": "CNMV_ECR_REPORTING",
        "nombre": "Reporte estados reservados CNMV ECR",
        "descripcion": "Comunicacion de estados reservados a CNMV via ECR (XML requerimientos)",
        "regulacion_relacionada": "cnmv_ecr",
        "ambito": "reporting_cnmv_ecr",
        "trigger_evento": "periodicidad",
        "frecuencia": "trimestral",
        "owner_rol": "reporting",
        "severidad": "alta",
    },
    {
        "codigo": "CNMV_ECR_XML_FORMAT",
        "nombre": "XML formatos ECR CNMV",
        "descripcion": "Generar XML segun formatos requeridos por CNMV para ECR",
        "regulacion_relacionada": "cnmv_ecr",
        "ambito": "reporting_cnmv_ecr",
        "trigger_evento": "periodicidad",
        "frecuencia": "trimestral",
        "owner_rol": "reporting",
        "severidad": "media",
    },
    {
        "codigo": "CNMV_ECR_ACTIVE_LIST",
        "nombre": "Listado FCR/SCR activos CNMV",
        "descripcion": "Mantener listado actualizado de FCR/SCR inscritos en CNMV",
        "regulacion_relacionada": "cnmv_ecr",
        "ambito": "reporting_cnmv_ecr",
        "trigger_evento": "continuo",
        "frecuencia": "mensual",
        "owner_rol": "compliance",
        "severidad": "alta",
    },
    {
        "codigo": "CNMV_ECR_FAQS",
        "nombre": "FAQs criterios interpretativos CNMV",
        "descripcion": "Seguir FAQs y criterios interpretativos de CNMV para ECR",
        "regulacion_relacionada": "cnmv_ecr",
        "ambito": "reporting_cnmv_ecr",
        "trigger_evento": "continuo",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "media",
    },
    # Doctrina DGT
    {
        "codigo": "DGT_SOCIMI_GRAVAMENES",
        "nombre": "Doctrina DGT gravamenes SOCIMI",
        "descripcion": "Aplicar doctrina DGT V0992-20 sobre gravamenes a socios >5% en SOCIMI",
        "regulacion_relacionada": "doctrina_dgt",
        "ambito": "doctrina_dgt",
        "trigger_evento": "continuo",
        "frecuencia": "continua",
        "owner_rol": "finanzas",
        "severidad": "alta",
    },
    {
        "codigo": "DGT_SOCIMI_DISTRIBUCION",
        "nombre": "Doctrina DGT distribucion SOCIMI",
        "descripcion": "Interpretar doctrina DGT sobre obligacion de distribucion de beneficios en SOCIMI",
        "regulacion_relacionada": "doctrina_dgt",
        "ambito": "doctrina_dgt",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "media",
    },
    {
        "codigo": "DGT_ETI_EMISORES",
        "nombre": "Doctrina DGT ETI emisores MiFID",
        "descripcion": "Interpretar doctrina DGT sobre emisores con ETI y folletos MiFID",
        "regulacion_relacionada": "doctrina_dgt",
        "ambito": "doctrina_dgt",
        "trigger_evento": "continuo",
        "frecuencia": "continua",
        "owner_rol": "compliance",
        "severidad": "media",
    },
    {
        "codigo": "DGT_FCR_EXENCIONES",
        "nombre": "Doctrina DGT exenciones FCR/SCR",
        "descripcion": "Aplicar doctrina DGT V2424-20 sobre exenciones fiscales similares para FCR/SCR",
        "regulacion_relacionada": "doctrina_dgt",
        "ambito": "doctrina_dgt",
        "trigger_evento": "periodicidad",
        "frecuencia": "anual",
        "owner_rol": "finanzas",
        "severidad": "media",
    },
]

# Mapeos: obligacion_regulatoria -> micro_obligacion por fuente
# Se resuelve en el worker buscando por fuente/ambito de la obligacion
MAPEOS = [
    {"obligacion_fuente": "cnmv", "micro_regulacion": "cnmv_lmcv"},
    {"obligacion_fuente": "cnmv", "micro_regulacion": "mar"},
    {"obligacion_fuente": "sepblac", "micro_regulacion": "pblcft"},
    {"obligacion_fuente": "boe", "micro_regulacion": "mifid_ii"},
    {"obligacion_fuente": "boe", "micro_regulacion": "mifir"},
    {"obligacion_fuente": "boe", "micro_regulacion": "mar"},
    {"obligacion_fuente": "boe", "micro_regulacion": "lecr"},
    {"obligacion_fuente": "boe", "micro_regulacion": "socimi"},
    {"obligacion_fuente": "eurlex", "micro_regulacion": "csdr"},
    {"obligacion_fuente": "cnmv", "micro_regulacion": "cnmv_ecr"},
    {"obligacion_fuente": "dgt", "micro_regulacion": "doctrina_dgt"},
]


def _upsert_micro_obligaciones(db) -> int:
    """Insertar micro-obligaciones de forma idempotente. Retorna count de inserts."""
    count = 0
    for mo in MICRO_OBLIGACIONES:
        db.execute(
            text(
                """
                INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada,
                    ambito, trigger_evento, frecuencia, owner_rol, severidad)
                VALUES (:codigo, :nombre, :descripcion, :regulacion_relacionada,
                    :ambito, :trigger_evento, :frecuencia, :owner_rol, :severidad)
                ON CONFLICT (codigo) DO NOTHING
                """
            ),
            mo,
        )
        count += 1
    return count


def _upsert_mapeos(db) -> int:
    """Crear mapeos N:M obligacion -> micro_obligacion por fuente/regulacion."""
    count = 0
    for mapeo in MAPEOS:
        db.execute(
            text(
                """
                INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden, evidencia_requerida)
                SELECT o.id, m.id, 0, NULL
                FROM obligacion_regulatoria o, micro_obligacion m
                WHERE o.fuente = :fuente
                  AND m.regulacion_relacionada = :regulacion
                ON CONFLICT DO NOTHING
                """
            ),
            {"fuente": mapeo["obligacion_fuente"], "regulacion": mapeo["micro_regulacion"]},
        )
        count += 1
    return count


def run_once():
    """Ejecutar seed una vez."""
    engine = get_engine()
    inserts = 0
    with engine.connect() as conn:
        inserts += _upsert_micro_obligaciones(conn)
        inserts += _upsert_mapeos(conn)
        conn.commit()
    logger.info("Fase 20 seed completado: %d micro-obligaciones insertadas, mapeos creados", inserts)
    return inserts


def main():
    parser = argparse.ArgumentParser(description="Seed micro-obligaciones Fase 20")
    parser.add_argument("--run-once", action="store_true", help="Ejecutar una vez")
    parser.add_argument("--interval", type=int, default=0, help="Intervalo en segundos (0 = una vez)")
    args = parser.parse_args()

    if args.run_once:
        run_once()
    elif args.interval > 0:
        while True:
            run_once()
            logger.info("Siguiente ejecucion en %ds...", args.interval)
            import time
            time.sleep(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
