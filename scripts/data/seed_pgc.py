#!/usr/bin/env python3
"""Seed PGC — Plan General de Contable espanol.

Inyecta cuentas del PGC (grupos 1-7), marco conceptual, normas de
valoracion y referencias fiscales para la sociedad de valores espanola.

Uso:
    python scripts/data/seed_pgc.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"


MARCO_DATA = [
    {"codigo": "MARCO-001", "titulo": "Marco Conceptual — IFRS", "tipo": "framework", "anio": 2018, "texto": "Marco Conceptual para los Informes Financieros Internacionales", "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2010-9226", "vigente": True},
    {"codigo": "MARCO-002", "titulo": "PGC aprobado por RDL 15/2007", "tipo": "normativa", "anio": 2007, "texto": "Real Decreto Legislativo 1/2007, por el que se aprueba el texto refundido del Plan General de Contabilidad", "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20422", "vigente": True},
    {"codigo": "MARCO-003", "titulo": "Normas NIIF/NCV", "tipo": "norma_valoracion", "anio": 2024, "texto": "Normas de Contabilidad y Valoracion", "url_boe": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20422", "vigente": True},
]


CUENTA_DATA = [
    # CLASE 1 — Financiaciacion permanente
    {"codigo": "1", "descripcion": "Financiaciacion permanente", "nivel": 0, "padre_codigo": None, "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "10", "descripcion": "Capital", "nivel": 1, "padre_codigo": "1", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "100", "descripcion": "Capital social", "nivel": 2, "padre_codigo": "10", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "101", "descripcion": "Capital desembolsado pendiente", "nivel": 2, "padre_codigo": "10", "grupo": "1", "clase": "1", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "106", "descripcion": "Acciones de propia", "nivel": 2, "padre_codigo": "10", "grupo": "1", "clase": "1", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "11", "descripcion": "Fondos propios", "nivel": 1, "padre_codigo": "1", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "110", "descripcion": "Reserva legal", "nivel": 2, "padre_codigo": "11", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "112", "descripcion": "Reservas por accion de propia", "nivel": 2, "padre_codigo": "11", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "113", "descripcion": "Otras reservas", "nivel": 2, "padre_codigo": "11", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "114", "descripcion": "Reserva para acciones de propia", "nivel": 2, "padre_codigo": "11", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "115", "descripcion": "Subvenciones, donaciones y otros aportes de socios", "nivel": 2, "padre_codigo": "11", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "119", "descripcion": "Otras reservas", "nivel": 2, "padre_codigo": "11", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "12", "descripcion": "Resultado de la ejercicio", "nivel": 1, "padre_codigo": "1", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "120", "descripcion": "Resultado neto consolidado", "nivel": 2, "padre_codigo": "12", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "121", "descripcion": "Partida correspondente a participaciones netas de terceros", "nivel": 2, "padre_codigo": "12", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "122", "descripcion": "Partida correspondiente al Grupo", "nivel": 2, "padre_codigo": "12", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "14", "descripcion": "Subvenciones, donaciones y otros aportes no monetarios", "nivel": 1, "padre_codigo": "1", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "140", "descripcion": "Subvenciones oficiales de capital", "nivel": 2, "padre_codigo": "14", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "141", "descripcion": "Otras subvenciones", "nivel": 2, "padre_codigo": "14", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "145", "descripcion": "Donaciones y aportes de socios, empresas u otras entidades para dotar reservas o hacer frente a pérdidas", "nivel": 2, "padre_codigo": "14", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "149", "descripcion": "Otras subvenciones, donaciones y otros aportes no monetarios", "nivel": 2, "padre_codigo": "14", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "17", "descripcion": "Deudas a largo plazo con entidades de credito", "nivel": 1, "padre_codigo": "1", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "170", "descripcion": "Deuda a largo plazo. Bancos e ICAs", "nivel": 2, "padre_codigo": "17", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "171", "descripcion": "Deuda a largo plazo. Fondos hipotecarios", "nivel": 2, "padre_codigo": "17", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "172", "descripcion": "Deuda a largo plazo. Otras entidades", "nivel": 2, "padre_codigo": "17", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "173", "descripcion": "Deudas a largo plazo. Acreedores diversos", "nivel": 2, "padre_codigo": "17", "grupo": "1", "clase": "1", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    # CLASE 2 — Activo no corriente
    {"codigo": "2", "descripcion": "Activo no corriente", "nivel": 0, "padre_codigo": None, "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "21", "descripcion": "Inmovilizado material", "nivel": 1, "padre_codigo": "2", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "210", "descripcion": "Terrenos y bienes naturales", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "211", "descripcion": "Construcciones", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "213", "descripcion": "Maquinaria", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "214", "descripcion": "Utillaje y otros instrumentos", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "215", "descripcion": "Montajes en curso", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "216", "descripcion": "Elementos de transporte", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "217", "descripcion": "Mobiliario", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "218", "descripcion": "Equipos para procesos de informacion", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "219", "descripcion": "Inversiones inmobiliarias", "nivel": 2, "padre_codigo": "21", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "22", "descripcion": "Inmovilizado material", "nivel": 1, "padre_codigo": "2", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "220", "descripcion": "Estudios e investigaciones", "nivel": 2, "padre_codigo": "22", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "221", "descripcion": "Propiedad industrial", "nivel": 2, "padre_codigo": "22", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "222", "descripcion": "Concesiones administrativas", "nivel": 2, "padre_codigo": "22", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "223", "descripcion": "Software", "nivel": 2, "padre_codigo": "22", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "224", "descripcion": "Fondo de comercio", "nivel": 2, "padre_codigo": "22", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "24", "descripcion": "Inversiones a largo plazo", "nivel": 1, "padre_codigo": "2", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "240", "descripcion": "Participaciones a largo plazo en entidades vinculadas", "nivel": 2, "padre_codigo": "24", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "241", "descripcion": "Valores a largo plazo de renta fija", "nivel": 2, "padre_codigo": "24", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "242", "descripcion": "Valores a largo plazo de renta variable", "nivel": 2, "padre_codigo": "24", "grupo": "2", "clase": "2", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    # CLASE 3 — Existencias
    {"codigo": "3", "descripcion": "Existencias", "nivel": 0, "padre_codigo": None, "grupo": "3", "clase": "3", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "30", "descripcion": "Mercaderias A", "nivel": 1, "padre_codigo": "3", "grupo": "3", "clase": "3", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "31", "descripcion": "Materias Prima", "nivel": 1, "padre_codigo": "3", "grupo": "3", "clase": "3", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "34", "descripcion": "Productos terminados", "nivel": 1, "padre_codigo": "3", "grupo": "3", "clase": "3", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "35", "descripcion": "Productos en curso", "nivel": 1, "padre_codigo": "3", "grupo": "3", "clase": "3", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "36", "descripcion": "Subproductos, materiales reciclables y desechos", "nivel": 1, "padre_codigo": "3", "grupo": "3", "clase": "3", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "39", "descripcion": "Pérdidas de valor de las existencias", "nivel": 1, "padre_codigo": "3", "grupo": "3", "clase": "3", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    # CLASE 4 — Acreedores y deudores
    {"codigo": "4", "descripcion": "Ciclos operativo y financiero", "nivel": 0, "padre_codigo": None, "grupo": "4", "clase": "4", "saldo_normal": None, "tipo_cuenta": "balance"},
    {"codigo": "40", "descripcion": "Acreedores por compras", "nivel": 1, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "41", "descripcion": "Deudores", "nivel": 1, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "43", "descripcion": "Clientes", "nivel": 1, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "430", "descripcion": "Clientes, p.p.to", "nivel": 2, "padre_codigo": "43", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "431", "descripcion": "Clientes, p.to. internacionales UE", "nivel": 2, "padre_codigo": "43", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "432", "descripcion": "Clientes internacionales (resto del mundo)", "nivel": 2, "padre_codigo": "43", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "44", "descripcion": "Deudores diversos", "nivel": 1, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "45", "descripcion": "Deudores o acreedores por operaciones en grupo", "nivel": 1, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": None, "tipo_cuenta": "balance"},
    {"codigo": "46", "descripcion": "Personal, deudor", "nivel": 1, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "47", "descripcion": "Hacienda publica, acreedora y deudora", "nivel": 1, "padre_codigo": "4", "grupo": "4", "clase": "4", "saldo_normal": None, "tipo_cuenta": "balance"},
    {"codigo": "470", "descripcion": "Hacienda publica, IVA soportado", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "472", "descripcion": "Hacienda publica, créditos a recuperar", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "473", "descripcion": "Hacienda publica, deudora", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "474", "descripcion": "Hacienda publica, creditos traspasados a S.C.O.B", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "475", "descripcion": "Hacienda publica, pendientes de aplicacion", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "476", "descripcion": "Hacienda publica, pasivo fiscal", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "477", "descripcion": "Retenciones e ingresos a cuenta de la Hacienda publica", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "478", "descripcion": "Penalizaciones, intereses de demora y recargos por declaracion extemporanea con cuota a ingresar", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": "Acreedor", "tipo_cuenta": "balance"},
    {"codigo": "479", "descripcion": "Otras deudas fiscales", "nivel": 2, "padre_codigo": "47", "grupo": "4", "clase": "4", "saldo_normal": None, "tipo_cuenta": "balance"},
    # CLASE 5 — Activo financiero
    {"codigo": "5", "descripcion": "Activo financiero", "nivel": 0, "padre_codigo": None, "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "50", "descripcion": "Valores negociables", "nivel": 1, "padre_codigo": "5", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "500", "descripcion": "Inversiones en instrumentos de patrimonio", "nivel": 2, "padre_codigo": "50", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "501", "descripcion": "Inversiones en instrumentos de patrimonio consolidado", "nivel": 2, "padre_codigo": "50", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "502", "descripcion": "Valores negociables de renta variable", "nivel": 2, "padre_codigo": "50", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "503", "descripcion": "Valores negociables de renta fija", "nivel": 2, "padre_codigo": "50", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "51", "descripcion": "Inversiones a corto plazo", "nivel": 1, "padre_codigo": "5", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "510", "descripcion": "Inversiones a corto plazo. Instrumentos de patrimonio", "nivel": 2, "padre_codigo": "51", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "511", "descripcion": "Inversiones a corto plazo. Valores de renta fija", "nivel": 2, "padre_codigo": "51", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "52", "descripcion": "Creditos", "nivel": 1, "padre_codigo": "5", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "520", "descripcion": "Creditos a corto plazo a entidades de credito", "nivel": 2, "padre_codigo": "52", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "521", "descripcion": "Creditos a corto plazo a clientes", "nivel": 2, "padre_codigo": "52", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "55", "descripcion": "Patrimonio neto de participaciones", "nivel": 1, "padre_codigo": "5", "grupo": "5", "clase": "5", "saldo_normal": None, "tipo_cuenta": "balance"},
    {"codigo": "57", "descripcion": "Inversiones temporales", "nivel": 1, "padre_codigo": "5", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "570", "descripcion": "Inversiones temporales. Valores negociables", "nivel": 2, "padre_codigo": "57", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "571", "descripcion": "Inversiones temporales. Creditos a corto plazo", "nivel": 2, "padre_codigo": "57", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
    {"codigo": "572", "descripcion": "Inversiones temporales. Valores de renta fija", "nivel": 2, "padre_codigo": "57", "grupo": "5", "clase": "5", "saldo_normal": "Deudor", "tipo_cuenta": "balance"},
]


NORMA_DATA = [
    {"norma_ref": "NCV-1", "articulo": "Art. 39-42 PGC", "descripcion": "Valoraci on de activos no corrientes y grupos de activos en venta", "tipo_operacion": "valoracion", "debe_haber": "Ambos"},
    {"norma_ref": "NCV-2", "articulo": "Art. 43 PGC", "descripcion": "Grupos de activos en venta", "tipo_operacion": "clasificacion", "debe_haber": "Ambos"},
    {"norma_ref": "NCV-3", "articulo": "Art. 44 PGC", "descripcion": "Deterioro y revisi on de valores", "tipo_operacion": "deterioro", "debe_haber": "Deudor"},
    {"norma_ref": "NCV-4", "articulo": "Art. 45-48 PGC", "descripcion": "Variaci on justa", "tipo_operacion": "valoracion", "debe_haber": "Ambos"},
    {"norma_ref": "NCV-5", "articulo": "Art. 49 PGC", "descripcion": "Ingresos", "tipo_operacion": "reconocimiento", "debe_haber": "Acreedor"},
    {"norma_ref": "NCV-6", "articulo": "Art. 50 PGC", "descripcion": "Resultado por inversiones temporales", "tipo_operacion": "resultado", "debe_haber": "Ambos"},
    {"norma_ref": "NIIF-1", "articulo": "NIIF 1", "descripcion": "Primeras aplicaciones de las NIIF", "tipo_operacion": "transicion", "debe_haber": "Ambos"},
    {"norma_ref": "NIIF-7", "articulo": "NIIF 7", "descripcion": "Instrumentos financieros: informaci on reveladora", "tipo_operacion": "revelacion", "debe_haber": "Acreedor"},
    {"norma_ref": "NIIF-9", "articulo": "NIIF 9", "descripcion": "Instrumentos financieros", "tipo_operacion": "clasificacion", "debe_haber": "Ambos"},
    {"norma_ref": "NIIF-13", "articulo": "NIIF 13", "descripcion": "Valoraci on a valor razonable", "tipo_operacion": "valoracion", "debe_haber": "Ambos"},
]


FISCAL_REF_DATA = [
    {"cuenta_id": "12", "modelo": "60", "casilla": "000", "ejercicio": "IS", "nota": "Resultado ejercicio — Impuesto Sociedades"},
    {"cuenta_id": "473", "modelo": "60", "casilla": "300", "ejercicio": "IS", "nota": "Hacienda deudora — IRPF e Impuesto Sociedades"},
    {"cuenta_id": "477", "modelo": "111", "casilla": "000", "ejercicio": "TR", "nota": "Retenciones e ingresos a cuenta — Declaracion trimestral IRPF"},
    {"cuenta_id": "470", "modelo": "303", "casilla": "000", "ejercicio": "IVA", "nota": "IVA soportado — Declaracion trimestral"},
    {"cuenta_id": "476", "modelo": "303", "casilla": "000", "ejercicio": "IVA", "nota": "Pasivo fiscal IVA — Declaracion trimestral"},
    {"cuenta_id": "640", "modelo": "111", "casilla": "000", "ejercicio": "TR", "nota": "Honorarios al consejero — Retenciones IRPF"},
    {"cuenta_id": "626", "modelo": "390", "casilla": "000", "ejercicio": "CENS", "nota": "Arrendamientos — Censo de Empresas"},
    {"cuenta_id": "700", "modelo": "036", "casilla": "000", "ejercicio": "ALTA", "nota": "Ventas de bienes y prestaciones — Alta AEAT"},
]


AEAT_REF_DATA = [
    {"cuenta_id": "12", "modelo_id": 1, "campana": "2024", "nota": "Resultado ejercicio vinculado al modelo 60 (Impuesto Sociedades)"},
    {"cuenta_id": "477", "modelo_id": 1, "campana": "2024", "nota": "Retenciones IRPF vinculadas al modelo 111"},
    {"cuenta_id": "43", "modelo_id": 3, "campana": "2024", "nota": "Clientes vinculado al modelo 347 (operaciones con terceros)"},
    {"cuenta_id": "470", "modelo_id": 5, "campana": "2024T", "nota": "IVA soportado vinculado al modelo 303 trimestral"},
    {"cuenta_id": "476", "modelo_id": 5, "campana": "2024T", "nota": "Pasivo fiscal IVA vinculado al modelo 303"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed PGC data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(MARCO_DATA)} marco entries")
        print(f"[DRY RUN] Would insert {len(CUENTA_DATA)} PGC cuentas (grupos 1-5)")
        print(f"[DRY RUN] Would insert {len(NORMA_DATA)} normas de valoracion")
        print(f"[DRY RUN] Would insert {len(FISCAL_REF_DATA)} referencias fiscales")
        print(f"[DRY RUN] Would insert {len(AEAT_REF_DATA)} referencias AEAT")
        total = len(MARCO_DATA) + len(CUENTA_DATA) + len(NORMA_DATA) + len(FISCAL_REF_DATA) + len(AEAT_REF_DATA)
        print(f"[DRY RUN] Total: {total} registros")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # Insert marco
    for m in MARCO_DATA:
        cur.execute(
            """INSERT INTO pgc_marco (codigo, titulo, tipo, anio, texto, url_boe, vigente)
               VALUES (%(codigo)s, %(titulo)s, %(tipo)s, %(anio)s, %(texto)s, %(url_boe)s, %(vigente)s)
               ON CONFLICT (codigo) DO UPDATE SET
                   titulo = EXCLUDED.titulo, tipo = EXCLUDED.tipo, vigente = EXCLUDED.vigente""",
            m,
        )

    # Insert cuentas
    for c in CUENTA_DATA:
        cur.execute(
            """INSERT INTO pgc_cuenta (codigo, descripcion, nivel, padre_codigo, grupo, clase,
               saldo_normal, tipo_cuenta, vigente)
               VALUES (%(codigo)s, %(descripcion)s, %(nivel)s, %(padre_codigo)s, %(grupo)s, %(clase)s,
                       %(saldo_normal)s, %(tipo_cuenta)s, true)
               ON CONFLICT (codigo) DO UPDATE SET
                   descripcion = EXCLUDED.descripcion, nivel = EXCLUDED.nivel,
                   saldo_normal = EXCLUDED.saldo_normal, tipo_cuenta = EXCLUDED.tipo_cuenta""",
            c,
        )

    # Insert normas
    for n in NORMA_DATA:
        cur.execute(
            """INSERT INTO pgc_norma_valoracion (norma_ref, articulo, descripcion, tipo_operacion, debe_haber)
               VALUES (%(norma_ref)s, %(articulo)s, %(descripcion)s, %(tipo_operacion)s, %(debe_haber)s)""",
            n,
        )

    # Insert fiscal refs
    for f in FISCAL_REF_DATA:
        cur.execute(
            """INSERT INTO pgc_cuenta_fiscal_ref (cuenta_id, modelo, casilla, ejercicio, nota)
                SELECT pc.id, %(modelo)s, %(casilla)s, %(ejercicio)s, %(nota)s
                FROM pgc_cuenta pc WHERE pc.codigo = %(codigo)s
                ON CONFLICT (cuenta_id, modelo, casilla, ejercicio) DO UPDATE SET
                    nota = EXCLUDED.nota""",
            {**f, "codigo": f["cuenta_id"]},
        )

    # Insert AEAT refs
    for a in AEAT_REF_DATA:
        cur.execute(
            """INSERT INTO pgc_cuenta_modelo_aeat_ref (cuenta_id, modelo_id, campana, nota)
                SELECT pc.id, %(modelo_id)s, %(campana)s, %(nota)s
                FROM pgc_cuenta pc WHERE pc.codigo = %(codigo)s""",
            {**a, "codigo": a["cuenta_id"]},
        )

    conn.commit()
    total = len(MARCO_DATA) + len(CUENTA_DATA) + len(NORMA_DATA) + len(FISCAL_REF_DATA) + len(AEAT_REF_DATA)
    print(f"OK: {total} registros PGC insertados ({len(MARCO_DATA)} marco, {len(CUENTA_DATA)} cuentas, {len(NORMA_DATA)} normas, {len(FISCAL_REF_DATA)} fiscal refs, {len(AEAT_REF_DATA)} AEAT refs)")
    conn.close()


if __name__ == "__main__":
    main()
