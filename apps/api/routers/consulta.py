"""Consulta fiscal inteligente — responde preguntas naturales devolviendo modelos, obligaciones y normativa."""

import logging
import re
import unicodedata

from db import db_session
from fastapi import APIRouter, Query, Request
from middleware.metrics import (
    record_consulta_metrics,
    record_faithfulness_histogram,
    record_query_memory,
)
from schemas import ConsultaFiscalResponse
from services.ai_disclaimer import get_ai_version
from services.faithfulness import compute_faithfulness
from services.grounding import validate_claim_grounding
from services.human_review import check_review_required
from services.query_audit import get_query_audit_service
from request_context import get_request_id, get_user_id
from services.domain_availability import get_domain_availability
from services.reranker import normalize_rerank_score, rerank
from services.search import search_legislacion
from services.unified_multi_source_search import unified_multi_source_search
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ── Sinonimos juridicos para expansion semantica ──────────────────────────
SINONIMOS_JURIDICOS = {
    "no residente": ["irnr", "extranjero", "residente fuera"],
    "intracomunitario": ["ue", "union europea", "comunitario", "intracom"],
    "dividendos": ["distribuciones", "rentas capital financiero"],
    "retencion": ["retenciones", "ingresos a cuenta", "reintegro"],
    "entregas bienes": ["suministros", "traslados", "ventas"],
    "prestacion servicios": ["servicios", "prestaciones"],
    "irpf": ["rendimientos", "renta personas fisicas"],
    "iva": ["impuesto valorado", "impuesto valor añadido"],
    "blanqueo capitales": ["lavado", "aml", "anti lavado"],
    "hacendario": ["aeat", "agencia tributaria", "hacienda"],
}

#  Mapeo termino → tipo resultado preferido
TERMINO_TIPO = {
    "modelo": ["modelo", "formulario", "aeat"],
    "normativa": ["articulo", "ley", "real decreto", "disposicion", "vigente"],
    "doctrina": ["dgt", "teac", "consulta vinculante", "criterio", "criterio interpretativo"],
    "obligacion": ["obligacion", "deber", "comunicar", "presentar", "reportar"],
}

#  Boost por tipo de resultado
RESULTADO_BOOST = {
    "modelo": 2.0,
    "normativa": 1.5,
    "obligacion": 1.3,
    "doctrina": 1.0,
}

FAITHFULNESS_REVIEW_THRESHOLD = 0.5
FAITHFULNESS_AUTO_APPROVE_THRESHOLD = 0.95
QUERY_AUDIT_CONFIG_VERSION = "consulta-faithfulness-v1"
RERANK_TOP_K = 5
GROUNDING_THRESHOLD = 0.4
UNVERIFIED_EVIDENCE_AVISO = (
    "NO VERIFICADO: evidencia insuficiente para responder con fiabilidad; "
    "revise la fuente oficial antes de tomar decisiones"
)

router = APIRouter(prefix="", tags=["consulta"])


DOMAIN_AVAILABILITY_QUERY_MAP: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("casp", "crypto-asset service provider", "proveedor de servicios de criptoactivos"), ("casp",)),
    (("criptoactivo mica", "crypto asset"), ("crypto_asset", "tokenized_asset")),
    (("wallet custodian", "custodio wallet", "custodia wallet"), ("wallet_custodian",)),
    (("dora", "ict risk", "riesgo tic", "incidente tic"), ("dora_ict_risk_register", "dora_tic_incident", "dora_third_party_provider")),
    (("sfdr", "pai", "paci", "producto sfdr", "precontractual sfdr"), ("sfdr_product", "sfdr_paci_indicator", "sfdr_pre_contractual", "sfdr_annual_report")),
    (("csrd report", "informe csrd", "esg data point", "dato esg"), ("csrd_entity_report", "csrd_esg_data_point", "csrd_company")),
    (("aifmd", "ucits", "priips kid", "kid priips", "solvency ii"), ("aifmd_fund", "ucits_fund", "priips_kid", "solvency_ii_entity")),
    (("psd2 consent", "consentimiento psd2", "psd2 incident", "incidente psd2"), ("psd2_consent", "psd2_incident_report")),
    (("ubo", "beneficial owner", "titular real", "titularidad real"), ("beneficial_owner_record", "ubo_record", "ownership_relation", "ownership_share")),
    (("screening entries", "screening match", "sanciones screening", "lista sanciones"), ("screening_entries", "screening_matches")),
    (("xbrl filing", "ixbrl", "esef", "xbrl fact", "hecho xbrl"), ("xbrl_filing", "xbrl_fact", "xbrl_company")),
    (("fatca giin", "giin registry", "registro giin"), ("giin_registry",)),
]


def _ci_like(column: str, param_name: str) -> str:
    return f"LOWER({column}) LIKE LOWER(:{param_name})"


def _normalize_query_text(value: str | None) -> str:
    text_value = value or ""
    normalized = unicodedata.normalize("NFKD", text_value)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_text.lower()


def _availability_probe_tables(query: str, sources: str | None = None) -> list[str]:
    haystack = _normalize_query_text(" ".join(filter(None, [query, sources or ""])))
    tables: list[str] = []
    for markers, candidate_tables in DOMAIN_AVAILABILITY_QUERY_MAP:
        if any(marker in haystack for marker in markers):
            tables.extend(candidate_tables)
    return list(dict.fromkeys(tables))


def _availability_blockers(db, query: str, sources: str | None = None) -> list[dict]:
    blockers: list[dict] = []
    for table in _availability_probe_tables(query, sources):
        record = get_domain_availability(db, table)
        if record and record.get("safe_to_answer") is False:
            blockers.append(record)
    return blockers


def _availability_abstention_response(
    request: Request,
    query: str,
    blockers: list[dict],
) -> ConsultaFiscalResponse:
    availability_summary = {
        "blocked": True,
        "reason": "domain_availability_not_safe_to_answer",
        "tables": blockers,
    }
    aviso = (
        "NO VERIFICADO: la consulta depende de dominios/tablas sin filas reales "
        "disponibles. Se devuelve abstencion para evitar una respuesta fiscal/legal inventada."
    )
    confianza = {
        "nivel": 0,
        "nivel_texto": "baja",
        "fuentes": [],
        "aviso": aviso,
        "modelos_cubiertos": [],
        "resultados_clasificados": {},
        "faithfulness_score": 0.0,
        "faithfulness_label": "baja",
        "review_required": True,
        "availability": availability_summary,
    }
    request_id = get_request_id(request)
    user_id = get_user_id(request)
    response_payload = {
        "consulta": query or "",
        "modelos": [],
        "resultados": [],
        "total_resultados": 0,
        "confianza": confianza,
        "cited_chunks": [],
        "claim_citations": [],
    }
    get_query_audit_service().record_query(
        request_id=request_id,
        user_id=user_id,
        path="/v1/consulta",
        query_text=query,
        retrieved_chunks=[],
        response_summary=f"availability_blocked tables={','.join(str(item.get('table')) for item in blockers)}",
        model_version=get_ai_version(),
        config_version=QUERY_AUDIT_CONFIG_VERSION,
        grounding_status="availability_blocked",
        prompt_injection_detected=False,
        grounding_summary=availability_summary,
        response_payload=response_payload,
    )
    return ConsultaFiscalResponse(
        consulta=query or "",
        modelos=[],
        resultados=[],
        total_resultados=0,
        relevancia={
            "nivel": "baja",
            "score": 0.0,
            "coincidencia": "bloqueado por disponibilidad de dominio",
            "terminos_encontrados": [],
            "terminos_faltantes": list(re.findall(r"[a-zA-Z0-9]{3,}", query.lower())) if query else [],
        },
        confianza=confianza,
        cited_chunks=[],
        claim_citations=[],
    )


def _unverified_abstention_response(
    request: Request,
    query: str,
    *,
    aviso: str = UNVERIFIED_EVIDENCE_AVISO,
    grounding_status: str = "unverified_abstention",
) -> ConsultaFiscalResponse:
    request_id = get_request_id(request)
    user_id = get_user_id(request)
    get_query_audit_service().record_query(
        request_id=request_id,
        user_id=user_id,
        path="/v1/consulta",
        query_text=query,
        retrieved_chunks=[],
        response_summary=f"{grounding_status} resultados=0",
        model_version=get_ai_version(),
        config_version=QUERY_AUDIT_CONFIG_VERSION,
        grounding_status=grounding_status,
        prompt_injection_detected=False,
        grounding_summary={"blocked": True, "reason": grounding_status, "query": query},
    )
    return ConsultaFiscalResponse(
        consulta=query or "",
        modelos=[],
        resultados=[],
        total_resultados=0,
        relevancia={
            "nivel": "baja",
            "score": 0.0,
            "coincidencia": "sin resultados verificados",
            "terminos_encontrados": [],
            "terminos_faltantes": list(re.findall(r"[a-zA-Z0-9]{3,}", query.lower())) if query else [],
        },
        confianza={
            "nivel": 0,
            "nivel_texto": "baja",
            "fuentes": [],
            "aviso": aviso,
            "modelos_cubiertos": [],
            "resultados_clasificados": {},
            "faithfulness_score": 0.0,
            "faithfulness_label": "baja",
            "review_required": True,
        },
        cited_chunks=[],
        claim_citations=[],
    )

#  Keyword → modelo mapping
KEYWORD_MODELOS = {
    # FactA / intracomunitario
    "facta": ["216", "349", "124"],
    "intracomunitario": ["216", "349", "124"],
    "entregas intracomunitarias": ["216", "349"],
    "adquisiciones intracomunitarias": ["349"],
    "operaciones intracomunitarias": ["216", "349"],
    "ue": ["216", "349", "124"],
    "unión europea": ["216", "349", "124"],
    "europa": ["216", "349", "124"],
    "nif intracomunitario": ["216", "349"],
    "eu": ["216", "349", "124"],
    # IRNR / no residente
    "no residente": ["124", "216", "123", "296"],
    "irnr": ["124", "216", "123", "296"],
    "residente fuera": ["124", "216", "123", "296"],
    "residente en": ["124", "216", "123", "296"],
    "extranjero": ["124", "216", "123", "296"],
    "eeuu": ["124", "216", "123", "296"],
    "estados unidos": ["124", "216", "123", "296"],
    "alemania": ["124", "216", "349"],
    "francia": ["124", "216", "349"],
    "portugal": ["124", "216", "349"],
    # Retenciones / dividendos
    "dividendos": ["124"],
    "retención": ["124", "123", "111", "115"],
    "retenciones": ["124", "123", "111", "115"],
    "ingresos a cuenta": ["111"],
    "rentas capital": ["124"],
    "intereses": ["296"],
    "cánones": ["296"],
    "royalties": ["296"],
    "arrendamiento": ["115", "296"],
    "arrendamientos urbanos": ["115"],
    # IVA
    "iva": ["303", "349"],
    "entregas bienes": ["303", "349"],
    "prestación servicios": ["303", "349"],
    "servicios": ["303", "349"],
    "exento": ["303"],
    # IRPF
    "irpf": ["100", "190", "193"],
    "renta": ["100", "190", "193"],
    "nómina": ["100"],
    "alquiler": ["115"],
    "ganancia patrimonial": ["100"],
    "venta inmueble": ["100"],
    "acciones": ["100"],
    "mercado regulado": ["100"],
    # IS
    "impuesto sociedades": ["200"],
    "sociedad": ["200"],
    "empresa": ["200", "303"],
    "sociedades": ["200"],
    # 347 / terceros
    "terceras personas": ["347"],
    "347": ["347"],
    "operaciones terceras": ["347"],
    # 720
    "720": ["720"],
    "bienes extranjero": ["720"],
    "cuentas extranjero": ["720"],
    # Modelo 036
    "alta": ["036"],
    "censo": ["036"],
    # DAC6
    "dac6": ["DAC6"],
    "planificación agresiva": ["DAC6"],
    "mecanismos transfronterizos": ["DAC6"],
    "transparencia fiscal": ["DAC6"],
    "directiva DAC6": ["DAC6"],
    # Compliance
    "blanqueo capitales": ["SEPBLAC"],
    "sepblac": ["SEPBLAC"],
    "indicio blanqueo": ["SEPBLAC"],
    "comunicacion indicio": ["SEPBLAC"],
    "CNMV": ["CNMV"],
    "mercados valores": ["CNMV"],
    "informacion reservada": ["CNMV"],
    # ITPAJD / HL / IIEE
    "transmisiones patrimoniales": ["ITPAJD"],
    "ITPAJD": ["ITPAJD"],
    "imponible transmisiones": ["ITPAJD"],
    "tasas locales": ["HL"],
    "hacendarias municipales": ["HL"],
    "impuestos especiales": ["IIEE"],
    "hidrocarburos": ["IIEE"],
    "consumo especifico": ["IIEE"],
    # Extraer modelos explicitos de la query
    "modelo 111": ["111"],
    "modelo 115": ["115"],
    "modelo 190": ["190"],
    "modelo 193": ["193"],
    "modelo 390": ["390"],
    "modelo 347": ["347"],
    "modelo 036": ["036"],
    "modelo 296": ["296"],
    "modelo 720": ["720"],
    "modelo DAC6": ["DAC6"],
}

#  Sujeto → modelo mapping
SUJETO_MODELOS = {
    "no_residente": ["124", "216", "123", "296"],
    "retenedor": ["124", "123"],
    "contribuyente": ["100"],
    "sociedad_contribuyente": ["200"],
    "empresario": ["349"],
    "empresario_intracomunitario": ["349"],
}


def _extract_keywords(q: str, sujeto: str) -> list[str]:
    """Extract relevant keywords and subject hints from the query."""
    q_lower = q.lower()
    keywords = []

    sorted_kw = sorted(KEYWORD_MODELOS.keys(), key=len, reverse=True)
    for kw in sorted_kw:
        pattern = rf"(?<!\w){re.escape(kw.lower())}(?!\w)"
        if re.search(pattern, q_lower):
            keywords.append(kw)

    if sujeto:
        s = sujeto.lower().replace(" ", "_")
        if s in SUJETO_MODELOS:
            keywords.append(f"_subject_{s}")

    return keywords


def _resolve_modelos(keywords: list[str]) -> list[str]:
    """Resolve keywords to a prioritized list of model codes.
    
    Prioritizes longer/more specific keywords over generic ones.
    E.g., "irnr" (2 chars, tax-specific) beats "renta" (5 chars, generic).
    Also prioritizes subject hints over keyword matches.
    """
    # Group keywords by specificity: longer keywords first, then by position
    # This ensures "irnr" (matched from query) beats "renta" (generic)
    sorted_keywords = sorted(keywords, key=lambda k: (len(k), keywords.index(k)), reverse=True)

    # Track how many models each keyword contributes
    keyword_models = {}
    seen = set()

    for kw in sorted_keywords:
        if kw.startswith("_subject_"):
            subj = kw.replace("_subject_", "")
            models = SUJETO_MODELOS.get(subj, [])
        else:
            models = KEYWORD_MODELOS.get(kw, [])
        keyword_models[kw] = models

    # Build priority: group by model code, score by keyword specificity
    model_scores: dict[str, int] = {}
    for kw in sorted_keywords:
        models = keyword_models.get(kw, [])
        for code in models:
            if code not in model_scores:
                # Score = length of keyword (longer = more specific) + position bonus
                model_scores[code] = len(kw) + (len(keywords) - keywords.index(kw))
            else:
                # Keep the higher score
                score = len(kw) + (len(keywords) - keywords.index(kw))
                model_scores[code] = max(model_scores[code], score)

    # Sort by score descending
    priority = sorted(model_scores.keys(), key=lambda c: model_scores[c], reverse=True)
    return priority


def _expand_keywords(q: str, keywords: list[str]) -> list[str]:
    """Expand keywords with synonyms for better matching."""
    q_lower = q.lower()
    expanded = list(keywords)
    seen_synonyms = set(expanded)

    for kw in keywords:
        if kw in SINONIMOS_JURIDICOS:
            for syn in SINONIMOS_JURIDICOS[kw]:
                if syn not in seen_synonyms and syn in q_lower:
                    expanded.append(syn)
                    seen_synonyms.add(syn)

    return expanded


def _score_resultado(r: dict, q: str, expanded_keywords: list[str]) -> dict:
    """Score a single result for relevance to the query.

    Returns the result dict augmented with '_relevancia' key containing:
    - nivel: 'alta', 'media', 'baja'
    - score: float 0-1
    - coincidencia: description
    - terminos_encontrados: list
    - terminos_faltantes: list
    """
    q_lower = q.lower()
    q_terms = set(re.findall(r"[a-záéíóúñ]{3,}", q_lower))
    if not q_terms:
        r["_relevancia"] = {"nivel": "baja", "score": 0.0, "coincidencia": "sin terminos relevantes", "terminos_encontrados": [], "terminos_faltantes": list(q_terms)}
        return r

    texto_para_buscar = ""
    for k in ["nombre", "titulo", "texto", "fragmento", "tipo_obligacion", "fuente", "organismo", "motivo_ranking"]:
        val = r.get(k)
        if val:
            texto_para_buscar += f" {val}"
    texto_lower = texto_para_buscar.lower()

    terminos_encontrados = []
    for term in q_terms:
        if term in texto_lower:
            terminos_encontrados.append(term)

    terminos_faltantes = list(q_terms - set(terminos_encontrados))

    tipo = r.get("tipo", "")
    tipo_boost = RESULTADO_BOOST.get(tipo, 0.5)

    score = 0.0
    coincidencia = ""

    if terminos_encontrados:
        proporcion = len(terminos_encontrados) / len(q_terms)
        score = proporcion * tipo_boost

        if proporcion >= 0.7 and tipo in ("modelo", "normativa"):
            score = min(score, 1.0)
            coincidencia = "coincidencia alta con terminos clave"
        elif proporcion >= 0.4:
            score = min(score, 0.8)
            coincidencia = "coincidencia media con terminos relevantes"
        else:
            score = min(score, 0.5)
            coincidencia = "coincidencia parcial"
    else:
        score = 0.1 * tipo_boost
        coincidencia = "sin coincidencia directa de terminos"

    rank = r.get("rank")
    if rank is not None and rank > 0:
        rank_normalized = min(rank / 5.0, 1.0)
        score = score * 0.6 + rank_normalized * 0.4

    r["_relevancia"] = {
        "nivel": "alta" if score >= 0.6 else ("media" if score >= 0.3 else "baja"),
        "score": round(score, 4),
        "coincidencia": coincidencia,
        "terminos_encontrados": terminos_encontrados,
        "terminos_faltantes": terminos_faltantes,
    }

    return r


def _compute_confianza(modelos: list, resultados: list, q: str, resolved_modelos: list[str]) -> dict:
    """Compute confidence information for the query response.

    Returns a dict compatible with ConsultaConfianza schema.
    """
    q_lower = q.lower()
    fuentes = []
    tipos_conteo = {}

    for r in resultados:
        tipo = r.get("tipo", "desconocido")
        tipos_conteo[tipo] = tipos_conteo.get(tipo, 0) + 1

        fuente = r.get("fuente_norma") or r.get("fuente") or r.get("organismo") or r.get("tipo_doc")
        if fuente and fuente not in fuentes:
            fuentes.append(fuente)

    if modelos:
        fuentes.append("aeat_modelos")
    if resolved_modelos:
        for m in resolved_modelos:
            if m not in fuentes:
                fuentes.append(f"modelo_{m}")

    nivel = 0
    nivel_texto = "baja"
    aviso = None

    if tipos_conteo.get("modelo", 0) > 0 and tipos_conteo.get("normativa", 0) > 0:
        nivel = 2
        nivel_texto = "alta"
    elif tipos_conteo.get("modelo", 0) > 0 or tipos_conteo.get("normativa", 0) > 0:
        nivel = 1
        nivel_texto = "media"
        if len(resultados) <= 2:
            aviso = "pocos resultados, considerar ampliar la consulta"
    elif len(resultados) > 0:
        nivel = 1
        nivel_texto = "media"
    else:
        nivel = 0
        nivel_texto = "baja"
        aviso = "no se encontraron resultados relevantes"

    if not q:
        nivel = 0
        nivel_texto = "baja"
        aviso = "consulta vacia"

    if not q:
        faithfulness_score = 0.0
    else:
        chunks_para_faithfulness = []
        for resultado in resultados:
            texto = _result_text(resultado)
            if not texto:
                continue
            chunks_para_faithfulness.append(
                {
                    "chunk_id": _result_citation_id(resultado) or "unknown",
                    "text": texto,
                }
            )

        answer_proxy = " ".join(filter(None, [_result_text(resultado) for resultado in resultados[:3]]))
        faithfulness_score = compute_faithfulness(answer_proxy, chunks_para_faithfulness)

    faithfulness_label = "alta" if faithfulness_score >= 0.75 else ("media" if faithfulness_score >= FAITHFULNESS_REVIEW_THRESHOLD else "baja")
    review_check = check_review_required(
        faithfulness_score,
        confidence_threshold=FAITHFULNESS_REVIEW_THRESHOLD,
        auto_threshold=FAITHFULNESS_AUTO_APPROVE_THRESHOLD,
    )

    return {
        "nivel": nivel,
        "nivel_texto": nivel_texto,
        "fuentes": fuentes,
        "aviso": aviso,
        "modelos_cubiertos": [m for m in resolved_modelos if m],
        "resultados_clasificados": tipos_conteo,
        "faithfulness_score": faithfulness_score,
        "faithfulness_label": faithfulness_label,
        "review_required": review_check["requires_review"],
    }


def _build_query_audit_chunks(resultados: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for resultado in resultados:
        evidencia = resultado.get("evidencia") or {}
        chunk_id = evidencia.get("chunk_id") or resultado.get("chunk_id")
        source_hash = evidencia.get("source_hash") or resultado.get("source_hash")
        source_url = evidencia.get("source_url") or resultado.get("source_url")
        if not any([chunk_id, source_hash, source_url]):
            continue
        chunks.append(
            {
                "tipo": resultado.get("tipo"),
                "norma": resultado.get("norma"),
                "articulo": resultado.get("articulo"),
                "codigo": resultado.get("codigo"),
                "referencia": resultado.get("referencia"),
                "chunk_id": chunk_id,
                "source_hash": source_hash,
                "source_url": source_url,
                "rerank_score": resultado.get("_rerank_score"),
                "motivo_ranking": evidencia.get("motivo_ranking") or resultado.get("motivo_ranking"),
                "rank": resultado.get("rank"),
            }
        )
    return chunks


def _result_text(resultado: dict) -> str | None:
    evidencia = resultado.get("evidencia") or {}
    return (
        evidencia.get("fragmento_exacto")
        or resultado.get("fragmento")
        or resultado.get("texto")
        or resultado.get("nombre")
        or resultado.get("titulo")
    )


def _result_source_document(resultado: dict) -> str | None:
    return (
        resultado.get("norma")
        or resultado.get("referencia")
        or resultado.get("codigo")
        or resultado.get("fuente_norma")
        or resultado.get("fuente")
        or resultado.get("organismo")
        or resultado.get("tipo")
    )


def _result_article_number(resultado: dict) -> str | None:
    value = resultado.get("articulo") or resultado.get("numero")
    if value in (None, ""):
        return None
    return str(value)


def _result_citation_id(resultado: dict) -> str | None:
    evidencia = resultado.get("evidencia") or {}
    value = (
        evidencia.get("chunk_id")
        or resultado.get("chunk_id")
        or evidencia.get("source_hash")
        or resultado.get("source_hash")
        or resultado.get("referencia")
        or resultado.get("codigo")
        or (
            f"{resultado.get('norma')}:{resultado.get('articulo')}"
            if resultado.get("norma") and resultado.get("articulo")
            else None
        )
        or resultado.get("norma")
    )
    if value in (None, ""):
        return None
    return str(value)


def _build_rerank_candidates(resultados: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    seen_ids: set[str] = set()
    for resultado in resultados:
        chunk_id = _result_citation_id(resultado)
        text = _result_text(resultado)
        source_document = _result_source_document(resultado)
        if not chunk_id or not text or not source_document:
            continue
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)
        candidates.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "source_document": str(source_document),
                "article_number": _result_article_number(resultado),
            }
        )
    return candidates


def _apply_rerank_scores(resultados: list[dict], ranked_chunks: list) -> list[dict]:
    score_map = {chunk.chunk_id: chunk.rerank_score for chunk in ranked_chunks}
    rescored: list[dict] = []
    for resultado in resultados:
        chunk_id = _result_citation_id(resultado)
        rerank_score = score_map.get(chunk_id)
        if rerank_score is None:
            rescored.append(resultado)
            continue

        updated = dict(resultado)
        relevancia = dict(updated.get("_relevancia") or {})
        normalized = normalize_rerank_score(rerank_score)
        base_score = float(relevancia.get("score", 0.0))
        combined_score = round(min(1.0, (base_score * 0.6) + (normalized * 0.4)), 4)
        relevancia["score"] = combined_score
        relevancia["rerank_score"] = float(rerank_score)
        relevancia["rerank_score_normalized"] = round(normalized, 4)
        if combined_score >= 0.6:
            relevancia["nivel"] = "alta"
        elif combined_score >= 0.3:
            relevancia["nivel"] = "media"
        else:
            relevancia["nivel"] = "baja"
        updated["_relevancia"] = relevancia
        updated["_rerank_score"] = float(rerank_score)
        rescored.append(updated)
    return rescored


def _build_cited_chunks(ranked_chunks: list) -> list[dict]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "source_document": chunk.source_document,
            "article_number": chunk.article_number,
            "rerank_score": float(chunk.rerank_score),
            "excerpt": chunk.text[:200],
        }
        for chunk in ranked_chunks
    ]


def _build_claim_citations(resultados: list[dict], ranked_chunks: list, query: str) -> list[dict]:
    all_chunks = []
    seen_ids = set()
    for resultado in resultados:
        chunk_id = _result_citation_id(resultado)
        text = _result_text(resultado)
        source_document = _result_source_document(resultado)
        if not chunk_id or not text or not source_document:
            continue
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)
        all_chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "source_document": str(source_document),
            "article_number": _result_article_number(resultado),
        })

    if not all_chunks or not query:
        return [
            {
                "claim": {
                    "tipo": r.get("tipo"),
                    "codigo": r.get("codigo") or r.get("norma") or r.get("referencia"),
                    "articulo": r.get("articulo"),
                    "nombre": r.get("nombre") or r.get("titulo"),
                },
                "citations": [],
            }
            for r in resultados
            if _result_citation_id(r)
        ]

    from services.reranker import rerank as semantic_rerank

    claim_citations = []
    for resultado in resultados:
        chunk_id = _result_citation_id(resultado)
        if not chunk_id:
            continue
        claim_text = _result_text(resultado)
        if not claim_text:
            continue
        ranked = semantic_rerank(claim_text, all_chunks, top_k=3)
        citations = [{
            "chunk_id": ch.chunk_id,
            "source_document": ch.source_document,
            "article_number": ch.article_number,
            "rerank_score": float(ch.rerank_score),
            "excerpt": ch.text[:200],
        } for ch in ranked]
        claim_citations.append({
            "claim": {
                "tipo": resultado.get("tipo"),
                "codigo": resultado.get("codigo") or resultado.get("norma") or resultado.get("referencia"),
                "articulo": resultado.get("articulo"),
                "nombre": resultado.get("nombre") or resultado.get("titulo"),
            },
            "citations": citations,
        })
    return claim_citations


def _collect_uncovered_query_terms(query: str, resultados: list[dict]) -> set[str]:
    query_terms = set(re.findall(r"[a-záéíóúñ0-9]{3,}", (query or "").lower()))
    if not query_terms or not resultados:
        return query_terms

    covered_terms: set[str] = set()
    for resultado in resultados:
        searchable_parts = [
            resultado.get("norma"),
            resultado.get("codigo"),
            resultado.get("referencia"),
            resultado.get("nombre"),
            resultado.get("titulo"),
            resultado.get("texto"),
            resultado.get("fragmento"),
            resultado.get("tipo_obligacion"),
            resultado.get("fuente"),
            resultado.get("organismo"),
            resultado.get("motivo_ranking"),
        ]
        evidencia = resultado.get("evidencia") or {}
        searchable_parts.extend(
            [
                evidencia.get("fragmento_exacto"),
                evidencia.get("fuente_norma"),
            ]
        )
        searchable_text = " ".join(str(part).lower() for part in searchable_parts if part)
        for term in query_terms:
            if term in searchable_text:
                covered_terms.add(term)

    return query_terms - covered_terms


def _apply_grounding_abstention_if_needed(
    query: str,
    resultados: list[dict],
    modelos: list[dict],
    resolved_modelos: list[str],
    confianza: dict,
    cited_chunks: list[dict],
) -> tuple[list[dict], dict, list[dict]]:
    if not query:
        return resultados, confianza, []

    if resolved_modelos:
        return resultados, confianza, cited_chunks

    uncovered_terms = _collect_uncovered_query_terms(query, resultados)
    if uncovered_terms:
        confianza = dict(confianza)
        confianza["aviso"] = UNVERIFIED_EVIDENCE_AVISO
        return [], confianza, []

    if not cited_chunks:
        confianza = dict(confianza)
        confianza["aviso"] = UNVERIFIED_EVIDENCE_AVISO
        return [], confianza, []

    has_full_article_evidence = any(
        resultado.get("tipo") == "normativa"
        and not (resultado.get("chunk_id") or (resultado.get("evidencia") or {}).get("chunk_id"))
        and (
            resultado.get("source_hash")
            or (resultado.get("evidencia") or {}).get("source_hash")
        )
        and (
            resultado.get("source_url")
            or (resultado.get("evidencia") or {}).get("source_url")
        )
        for resultado in resultados
    )
    if has_full_article_evidence and confianza.get("faithfulness_score", 0.0) >= FAITHFULNESS_REVIEW_THRESHOLD:
        return resultados, confianza, cited_chunks

    best_score = normalize_rerank_score(cited_chunks[0]["rerank_score"])
    if best_score >= GROUNDING_THRESHOLD:
        return resultados, confianza, cited_chunks

    confianza = dict(confianza)
    confianza["aviso"] = UNVERIFIED_EVIDENCE_AVISO
    return [], confianza, []


def _apply_abstention_if_needed(resultados: list[dict], confianza: dict) -> tuple[list[dict], dict]:
    if confianza.get("faithfulness_score", 0.0) >= FAITHFULNESS_REVIEW_THRESHOLD:
        return resultados, confianza

    confianza = dict(confianza)
    aviso_actual = (confianza.get("aviso") or "").strip().lower()
    if aviso_actual == "consulta vacia":
        return [], confianza
    confianza["aviso"] = UNVERIFIED_EVIDENCE_AVISO
    return [], confianza


def _apply_claim_level_abstention(
    resultados: list[dict],
    claim_citations: list[dict],
) -> tuple[list[dict], dict]:
    """Remove ungrounded claims from results when grounding is insufficient."""
    grounded_keys: set[str] = set()
    for item in claim_citations:
        if item.get("grounded"):
            claim = item.get("claim", {})
            key = f"{claim.get('tipo')}:{claim.get('codigo')}:{claim.get('articulo')}"
            grounded_keys.add(key)

    if not grounded_keys:
        return [], {}

    filtered = []
    for r in resultados:
        articulo_val = r.get("articulo", "") or ""
        codigo_val = r.get("codigo", r.get("referencia", r.get("norma", "")) or "")
        key = f"{r['tipo']}:{codigo_val}:{articulo_val}"
        if key in grounded_keys:
            filtered.append(r)

    return filtered, {}


@router.get(
    "/v1/consulta",
    operation_id="consulta_fiscal",
    response_model=ConsultaFiscalResponse,
    summary="Consulta fiscal inteligente",
    description=(
        "Responde preguntas fiscales en lenguaje natural. Dada una pregunta, devuelve:\n"
        "- Modelos AEAT a presentar (código, nombre, plazo)\n"
        "- Obligaciones regulatorias aplicables\n"
        "- Normativa aplicable (artículos)\n"
        "- Doctrina DGT/TEAC relevante\n"
        "- Casillas/claves/instrucciones de los modelos\n\n"
        "NOTA DE TERMINOLOGÍA AEAT (para evitar confusiones):\n"
        "- 'FactA' = Modelo 216 (declaración de facturas a no residentes), NO es Facturae (factura electrónica)\n"
        "- 'FactA intracomunitaria' = Modelo 349 (solo UE/NIF intracomunitario)\n"
        "- 'FactA no intracomunitaria' = Modelo 216 (fuera de UE)\n"
        "- Facturae = Ley 58/2023 (factura electrónica obligatoria para España)\n"
        "- Modelo 216 = obligatorio para TODOS los no residentes (UE y fuera UE)\n"
        "- Modelo 349 = SOLO para intracomunitarios (UE)\n"
        "- Facturae no obligatorio para clientes fuera de la UE"
    ),
)
async def consulta_fiscal(
    request: Request,
    q: str = Query("", description="Pregunta fiscal en lenguaje natural (ej: 'facta no residente', 'irpf dividendos ue', 'iva entregas intracomunitarias')"),
    sujeto: str = Query("", description="Tipo de sujeto: contribuyente, no_residente, empresa, retenedor, etc."),
    pais: str = Query("", description="País/territorio: es, ue, intracomunitario, fuera_ue, etc."),
    tipo_operacion: str = Query("", description="Tipo de operación: entrega_bienes, prestacion_servicios, dividendos, retencion, etc."),
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
    sources: str | None = Query(None, description="Filtrar fuentes por tipo, separadas por coma. Valores: legislacion, doctrina, pgc, modelos, screening, entities, norms, articles. Si no se indica, usa todas las fuentes por defecto."),
    hybrid_weight: float = Query(0.3, ge=0.0, le=1.0, description="Peso del componente vectorial (0.0=fulltext, 0.3=hibrido, 1.0=vectorial)"),
):
    results = []
    modelos_codigo = []

    # Resolve keywords to model codes
    keywords = _extract_keywords(q, sujeto)
    resolved_modelos = _resolve_modelos(keywords)

    with db_session() as db:
        #  1. Buscar modelos por resolución de keywords
        availability_blockers = _availability_blockers(db, q, sources)
        if availability_blockers:
            return _availability_abstention_response(request, q, availability_blockers)

        if resolved_modelos:
            try:
                placeholders = ",".join([f":m{i}" for i in range(len(resolved_modelos))])
                model_rows = db.execute(
                    text(f"""
                        SELECT am.codigo, am.nombre, am.periodo, am.impuesto, am.url_info
                        FROM aeat_modelo am
                        WHERE am.codigo IN ({placeholders})
                        ORDER BY am.codigo
                    """),
                    {f"m{i}": code for i, code in enumerate(resolved_modelos)},
                ).mappings()

                for row in model_rows:
                    modelos_codigo.append(row["codigo"])
                    results.append({
                        "tipo": "modelo",
                        "codigo": row["codigo"],
                        "nombre": row["nombre"],
                        "periodo": row["periodo"],
                        "impuesto": row["impuesto"],
                    })
            except Exception:
                db.rollback()
                logger.warning("Modelo resolution failed for resolved_modelos=%s", resolved_modelos)
        if not resolved_modelos and q:
            try:
                model_rows = db.execute(
                    text("""
                        SELECT am.codigo, am.nombre, am.periodo, am.impuesto, am.url_info
                        FROM aeat_modelo am
                        WHERE {name_filter}
                           OR am.codigo = :q
                        ORDER BY am.codigo
                    """.format(name_filter=_ci_like("am.nombre", "q"))),
                    {"q": f"%{q}%"},
                ).mappings()

                for row in model_rows:
                    modelos_codigo.append(row["codigo"])
                    results.append({
                        "tipo": "modelo",
                        "codigo": row["codigo"],
                        "nombre": row["nombre"],
                        "periodo": row["periodo"],
                        "impuesto": row["impuesto"],
                    })
            except Exception:
                db.rollback()
                logger.warning("Modelo fallback search failed for query='%s'", q)
        try:
            oblig_filters = ["1=1"]
            oblig_params: dict = {}
            if q:
                oblig_filters.append(
                    "(" + " OR ".join([
                        _ci_like("o.nombre", "q"),
                        _ci_like("o.tipo_obligacion", "q"),
                        _ci_like("o.fuente", "q"),
                        _ci_like("o.nota", "q"),
                    ]) + ")"
                )
                oblig_params["q"] = f"%{q}%"
            if sujeto:
                oblig_filters.append(_ci_like("o.sujeto_obligado", "suj"))
                oblig_params["suj"] = f"%{sujeto}%"
            if pais:
                oblig_filters.append(_ci_like("o.ambito", "pai"))
                oblig_params["pai"] = f"%{pais}%"

            oblig_rows = db.execute(
                text(f"""
                    SELECT o.codigo, o.nombre, o.fuente, o.organismo_emisor, o.tipo_obligacion,
                           o.sujeto_obligado, o.periodicidad, o.reporte_modelo, o.ambito, o.estado_vigencia
                    FROM obligacion_regulatoria o
                    WHERE {' AND '.join(oblig_filters)}
                    ORDER BY o.fuente ASC, o.codigo ASC
                """),
                oblig_params,
            ).mappings()

            for row in oblig_rows.fetchall():
                results.append({
                    "tipo": "obligacion",
                    "codigo": row["codigo"],
                    "nombre": row["nombre"],
                    "fuente": row["fuente"],
                    "organismo": row["organismo_emisor"],
                    "tipo_obligacion": row["tipo_obligacion"],
                    "sujeto": row["sujeto_obligado"],
                    "periodicidad": row["periodicidad"],
                    "modelos": row["reporte_modelo"],
                    "ambito": row["ambito"],
                    "vigencia": row["estado_vigencia"],
                })
        except Exception:
            db.rollback()
            logger.warning("Obligations search failed for q='%s' sujeto='%s'", q, sujeto)
        if q:
            try:
                search_result = search_legislacion(
                    q=q,
                    vigente_en=vigente_en,
                )
                for row in search_result["resultados"]:
                    evidencia = {
                        "source_url": row.get("source_url"),
                        "fuente_norma": row.get("fuente_norma"),
                        "fragmento_exacto": row.get("fragmento"),
                        "motivo_ranking": row.get("motivo_ranking"),
                        "chunk_id": row.get("chunk_id"),
                        "source_hash": row.get("source_hash"),
                    }
                    results.append({
                        "tipo": "normativa",
                        "norma": row["norma"],
                        "articulo": row["numero"],
                        "texto": row["texto"],
                        "fragmento": row["fragmento"],
                        "vigente_desde": row["vigente_desde"],
                        "vigente_hasta": row["vigente_hasta"],
                        "rank": row["rank"],
                        "source_url": row.get("source_url"),
                        "fuente_norma": row.get("fuente_norma"),
                        "chunk_id": row.get("chunk_id"),
                        "source_hash": row.get("source_hash"),
                        "motivo_ranking": row.get("motivo_ranking"),
                        "evidencia": evidencia,
                    })
            except Exception:
                db.rollback()
                logger.warning("Legislacion search failed for q='%s'", q)
        try:
            if q:
                doc_filters = [
                    "(LOWER(d.texto) LIKE LOWER(:q) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:q))"
                ]
                doc_params = {"q": f"%{q}%"}

                doc_rows = db.execute(
                    text(f"""
                        SELECT d.referencia, d.tipo_documento, d.organismo_emisor,
                               d.titulo, d.texto, d.fecha, d.url_fuente
                        FROM documento_interpretativo d
                        WHERE {' AND '.join(doc_filters)}
                        ORDER BY d.fecha DESC
                        LIMIT 10
                    """),
                    doc_params,
                ).mappings()

                for row in doc_rows.fetchall():
                    fragmento = row["texto"][:500] if row["texto"] else None
                    results.append({
                        "tipo": "doctrina",
                        "referencia": row["referencia"],
                        "tipo_doc": row["tipo_documento"],
                        "organismo": row["organismo_emisor"],
                        "titulo": row["titulo"],
                        "fragmento": fragmento,
                        "fecha": str(row["fecha"]) if row["fecha"] else None,
                        "source_url": row.get("url_fuente"),
                        "motivo_ranking": "ILIKE titulo/texto match ordered by fecha desc",
                        "evidencia": {
                            "source_url": row.get("url_fuente"),
                            "fuente_norma": None,
                            "fragmento_exacto": fragmento,
                            "motivo_ranking": "ILIKE titulo/texto match ordered by fecha desc",
                        },
                    })
        except Exception:
            db.rollback()
            logger.warning("Doctrina search failed for q='%s'", q)

    #  5. Obtener detalle completo de modelos
    try:
        modelos_codigo = list(dict.fromkeys(modelos_codigo))
        modelos_detalle = []

        for codigo in modelos_codigo:
            rows = db.execute(
                text("""
                    SELECT am.codigo, am.nombre, am.periodo, am.impuesto, am.url_info,
                           mc.campana, mc.version_form, mc.url_normativa, mc.url_formato,
                           mi.seccion, mi.titulo, mi.contenido, mi.orden,
                           mco.categoria_obligado, mco.frecuencia_presentacion,
                           mco.ventana_presentacion, mco.canal_presentacion,
                           mco.obligados_resumen, mco.plazo_resumen, mco.norma_base
                    FROM aeat_modelo am
                    LEFT JOIN modelo_campana mc ON mc.modelo_id = am.id AND mc.activo = true
                    LEFT JOIN modelo_campana_operativa mco ON mco.campana_id = mc.id
                    LEFT JOIN modelo_instruccion mi ON mi.campana_id = mc.id
                    WHERE am.codigo = :codigo
                    ORDER BY mi.orden
                """),
                {"codigo": codigo},
            ).mappings()

            rows_list = list(rows)
            if rows_list:
                first = rows_list[0]
                instrucciones = [
                    {"seccion": r["seccion"], "titulo": r["titulo"], "contenido": r["contenido"], "orden": r["orden"]}
                    for r in rows_list if r["seccion"]
                ]
                modelos_detalle.append({
                    "codigo": first["codigo"],
                    "nombre": first["nombre"],
                    "periodo": first["periodo"],
                    "impuesto": first["impuesto"],
                    "url_info": first["url_info"],
                    "campana": first["campana"],
                    "categoria_obligado": first["categoria_obligado"],
                    "frecuencia": first["frecuencia_presentacion"],
                    "ventana": first["ventana_presentacion"],
                    "canal": first["canal_presentacion"],
                    "obligados_resumen": first["obligados_resumen"],
                    "plazo_resumen": first["plazo_resumen"],
                    "norma_base": first["norma_base"],
                    "instrucciones": instrucciones,
                })
    except Exception:
        db.rollback()
        logger.warning("Modelo detail lookup failed for codigos=%s", modelos_codigo)

    #  6. Integrated unified multi-source search (if sources filter specified)
    if sources and q:
        try:
            source_list = [s.strip() for s in sources.split(",") if s.strip()]
            unified = unified_multi_source_search(
                q=q,
                sources=source_list,
                hybrid_weight=hybrid_weight,
                limit=20,
            )
            for item in unified.get("resultados", []):
                results.append(item)
        except Exception:
            db.rollback()
            return _unverified_abstention_response(
                request,
                q,
                aviso=(
                    "NO VERIFICADO: el retrieval solicitado no esta disponible. "
                    "No se devuelven resultados parciales para evitar una respuesta fiscal/legal inventada."
                ),
                grounding_status="requested_retrieval_failed",
            )

    seen = set()
    unique_results = []
    for r in results:
        articulo_val = r.get("articulo", "") or ""
        codigo_val = r.get("codigo", r.get("referencia", r.get("norma", "")) or "")
        key = f"{r['tipo']}:{codigo_val}:{articulo_val}"
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    # Score and sort results by relevance
    expanded_keywords = _expand_keywords(q, keywords)
    scored_results = []
    for r in unique_results:
        scored_r = _score_resultado(r, q, expanded_keywords)
        scored_results.append(scored_r)

    rerank_candidates = _build_rerank_candidates(scored_results)
    ranked_chunks = rerank(q, rerank_candidates, top_k=RERANK_TOP_K) if q else []
    scored_results = _apply_rerank_scores(scored_results, ranked_chunks)
    scored_results.sort(key=lambda x: x["_relevancia"]["score"], reverse=True)
    cited_chunks = _build_cited_chunks(ranked_chunks)
    claim_citations = _build_claim_citations(scored_results, ranked_chunks, q)

    #  Grounding hard — per-claim validation
    grounding_summary = {
        "total_claims": 0,
        "grounded_claims": 0,
        "ungrounded_claims": 0,
        "grounding_status": "empty",
        "all_claims_have_evidence": True,
        "all_chunks_clean": True,
        "injection_flags": [],
        "query": q,
    }
    if claim_citations and q:
        claim_citations, grounding_summary = validate_claim_grounding(claim_citations, q)

    # Compute confidence
    confianza = _compute_confianza(modelos_detalle, scored_results, q, resolved_modelos)
    final_results, confianza, cited_chunks = _apply_grounding_abstention_if_needed(
        q,
        scored_results,
        modelos_detalle,
        resolved_modelos,
        confianza,
        cited_chunks,
    )

    # Apply claim-level abstention when grounding is insufficient
    if claim_citations and grounding_summary.get("grounding_status") in ("partial", "none"):
        final_results, _ = _apply_claim_level_abstention(
            final_results, claim_citations
        )
    elif not claim_citations and not resolved_modelos and q:
        # No claim citations and no resolved modelos — check if grounding is empty
        if not cited_chunks and confianza.get("faithfulness_score", 0.0) < FAITHFULNESS_REVIEW_THRESHOLD:
            final_results = []
            confianza = dict(confianza)
            confianza["aviso"] = UNVERIFIED_EVIDENCE_AVISO

    final_results, confianza = _apply_abstention_if_needed(final_results, confianza)
    if not final_results:
        cited_chunks = []

    # Build top-level relevancia
    total_scored = len(scored_results)
    if final_results:
        avg_score = sum(r["_relevancia"]["score"] for r in final_results) / len(final_results)
        alta_count = sum(1 for r in final_results if r["_relevancia"]["nivel"] == "alta")
        relevancia_nivel = "alta" if avg_score >= 0.6 else ("media" if avg_score >= 0.3 else "baja")
        relevancia_coins = []
        todos_terminos = set()
        encontrados = set()
        for r in final_results:
            for t in r["_relevancia"].get("terminos_encontrados", []):
                encontrados.add(t)
            for t in r["_relevancia"].get("terminos_faltantes", []):
                todos_terminos.add(t)
        todos_terminos = todos_terminos | encontrados
        faltantes = todos_terminos - encontrados
        relevancia = {
            "nivel": relevancia_nivel,
            "score": round(avg_score, 4),
            "coincidencia": f"{alta_count}/{len(final_results)} resultados con relevancia alta",
            "terminos_encontrados": list(encontrados),
            "terminos_faltantes": list(faltantes),
        }
    else:
        relevancia = {
            "nivel": "baja",
            "score": 0.0,
            "coincidencia": "sin resultados",
            "terminos_encontrados": [],
            "terminos_faltantes": list(re.findall(r"[a-záéíóúñ]{3,}", q.lower())) if q else [],
        }

    request_id = get_request_id(request)
    user_id = get_user_id(request)
    retrieved_chunks = _build_query_audit_chunks(scored_results)
    response_summary = f"resultados={len(final_results)} faithfulness={confianza.get('faithfulness_score', 0.0):.4f} review_required={confianza.get('review_required', False)} grounding={grounding_summary.get('grounding_status', 'unknown')}/{grounding_summary.get('total_claims', 0)} claims"
    get_query_audit_service().record_query(
        request_id=request_id,
        user_id=user_id,
        path="/v1/consulta",
        query_text=q or sujeto or tipo_operacion or pais,
        retrieved_chunks=retrieved_chunks,
        response_summary=response_summary,
        model_version=get_ai_version(),
        config_version=QUERY_AUDIT_CONFIG_VERSION,
        grounding_status=grounding_summary.get("grounding_status"),
        prompt_injection_detected=not grounding_summary.get("all_chunks_clean", True),
        grounding_summary=grounding_summary,
    )

    #  Observability metrics
    try:
        import logging

        import psutil

        # Use module-level logger (line 24); do not reassign here — Python would
        # treat `logger` as local in the whole function and shadow it upstream.
        process = psutil.Process()
        mem_info = process.memory_info()
        record_query_memory("api", mem_info.rss)
    except Exception:
        pass

    # Faithfulness histogram
    faith = confianza.get("faithfulness_score", 0.0)
    if isinstance(faith, (int, float)):
        record_faithfulness_histogram(float(faith))

    record_consulta_metrics("/v1/consulta", confianza)

    #  Build unified search metadata
    unified_meta = {}
    if sources and q:
        try:
            source_list = [s.strip() for s in sources.split(",") if s.strip()]
            unified = unified_multi_source_search(
                q=q,
                sources=source_list,
                hybrid_weight=hybrid_weight,
                limit=20,
            )
            unified_meta = {
                "sources_requested": source_list,
                "sources_with_results": unified.get("sources_with_results", []),
                "source_breakdown": unified.get("source_breakdown", {}),
                "search_mode": unified.get("search_mode", "fulltext"),
                "weights": unified.get("weights", {}),
            }
            for item in unified.get("resultados", []):
                results.append(item)
        except Exception:
            db.rollback()

    # Deduplicate results
    seen = set()
    deduped = []
    for r in final_results:
        key = getattr(r, "id", None) or getattr(r, "chunk_id", None) or str(r)
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return ConsultaFiscalResponse(
        consulta=q or "",
        modelos=modelos_detalle if modelos_detalle else [],
        resultados=deduped,
        total_resultados=len(deduped),
        relevancia=relevancia,
        confianza=confianza if isinstance(confianza, dict) else None,
        cited_chunks=cited_chunks if cited_chunks else [],
        claim_citations=claim_citations if claim_citations else [],
    )
