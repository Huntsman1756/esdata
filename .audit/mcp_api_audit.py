"""MCP + API Surface Audit Script for esdata.

Runs inside the esdata-api-1 container. Performs:
1. MCP tools/list and invocation audit
2. REST API surface audit (30 representative endpoints)
3. Ground-truth benchmark
4. Audit log coverage
5. Determinism check
6. Uncertainty handling
"""

import json
import time
import hashlib
import requests

BASE = "http://127.0.0.1:8000"
API_KEY = "dev-key"
MCP_KEY = "dev-mcp-key"
HEADERS_API = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
HEADERS_MCP = {"X-API-Key": MCP_KEY, "Content-Type": "application/json", "Accept": "application/json"}

PROVENANCE_FIELDS = ["source_url", "boe_reference", "url_fuente", "eli_uri", "fuentes", "url_oficial", "boe_id"]
VALID_DOMAINS = ["boe.es", "eur-lex.europa.eu", "aeat.es", "aepd.es", "dgt.es",
                 "sede.agenciatributaria.gob.es", "petete.tributos.hacienda.gob.es",
                 "serviciostelematicosext.hacienda.gob.es", "sepblac.es", "cnmv.es",
                 "bde.es", "poderjudicial.es", "infosubvenciones.es", "hacienda.gob.es"]

results = {
    "mcp_tools": [],
    "critical_tools": [],
    "rest_surfaces": [],
    "audit_log": {},
    "determinism": {},
    "uncertainty": {},
    "critical_findings": [],
}


def has_provenance(data, depth=0):
    """Check if data contains provenance fields, recursively up to depth 3."""
    if depth > 3 or data is None:
        return False
    if isinstance(data, dict):
        for f in PROVENANCE_FIELDS:
            v = data.get(f)
            if v and str(v).strip():
                return True
        # Check confianza block
        if "confianza" in data:
            return True
        for v in data.values():
            if has_provenance(v, depth + 1):
                return True
    elif isinstance(data, list) and data:
        # Check first few items
        for item in data[:3]:
            if has_provenance(item, depth + 1):
                return True
    return False


def check_provenance_url_domain(data, depth=0):
    """Check if URLs in provenance fields point to valid official domains."""
    issues = []
    if depth > 3 or data is None:
        return issues
    if isinstance(data, dict):
        for f in ["source_url", "url_fuente", "eli_uri", "url_oficial"]:
            v = data.get(f)
            if v and isinstance(v, str) and v.startswith("http"):
                if not any(d in v for d in VALID_DOMAINS):
                    issues.append(f"{f}={v}")
        for val in data.values():
            issues.extend(check_provenance_url_domain(val, depth + 1))
    elif isinstance(data, list):
        for item in data[:5]:
            issues.extend(check_provenance_url_domain(item, depth + 1))
    return issues


# ─── MCP SESSION ────────────────────────────────────────────────────────────

def mcp_initialize():
    """Initialize MCP session and return session_id."""
    # Step 1: GET /mcp with SSE accept to get session
    r = requests.get(f"{BASE}/mcp", headers={
        "X-API-Key": MCP_KEY,
        "Accept": "text/event-stream",
    }, stream=True, timeout=10)
    session_id = r.headers.get("Mcp-Session-Id", "")
    r.close()

    if not session_id:
        # Try POST initialize directly
        r2 = requests.post(f"{BASE}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "audit", "version": "1.0"},
            }
        }, headers=HEADERS_MCP, timeout=10)
        if r2.status_code == 200:
            data = r2.json()
            session_id = r2.headers.get("Mcp-Session-Id", "")
            if not session_id:
                session_id = data.get("result", {}).get("sessionId", "fallback")
        return session_id, r2.json() if r2.status_code == 200 else {}

    # Step 2: POST initialize
    r2 = requests.post(f"{BASE}/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "audit", "version": "1.0"},
        }
    }, headers={**HEADERS_MCP, "Mcp-Session-Id": session_id}, timeout=10)

    # Step 3: notifications/initialized
    requests.post(f"{BASE}/mcp", json={
        "jsonrpc": "2.0", "method": "notifications/initialized",
    }, headers={**HEADERS_MCP, "Mcp-Session-Id": session_id}, timeout=5)

    return session_id, r2.json() if r2.status_code == 200 else {}


def mcp_tools_list(session_id):
    """Get tools list from MCP."""
    r = requests.post(f"{BASE}/mcp", json={
        "jsonrpc": "2.0", "id": 2, "method": "tools/list",
    }, headers={**HEADERS_MCP, "Mcp-Session-Id": session_id}, timeout=10)
    if r.status_code == 200:
        return r.json()
    return {"error": f"status={r.status_code}"}


def mcp_tool_call(session_id, name, arguments, call_id=3):
    """Call a tool via MCP."""
    r = requests.post(f"{BASE}/mcp", json={
        "jsonrpc": "2.0", "id": call_id, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }, headers={**HEADERS_MCP, "Mcp-Session-Id": session_id}, timeout=30)
    if r.status_code == 200:
        return r.json()
    return {"error": {"code": r.status_code, "message": r.text[:500]}}


# ─── REST API ───────────────────────────────────────────────────────────────

def api_get(path, params=None):
    """GET an API endpoint."""
    r = requests.get(f"{BASE}{path}", params=params, headers=HEADERS_API, timeout=15)
    return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def api_get_openapi():
    """Fetch OpenAPI spec."""
    r = requests.get(f"{BASE}/openapi.json", headers=HEADERS_API, timeout=10)
    return r.json() if r.status_code == 200 else {}


# ─── AUDIT LOG ──────────────────────────────────────────────────────────────

def count_audit_log():
    """Count audit log entries."""
    status, data = api_get("/v1/query-audit", {"limit": 1})
    if status == 200 and isinstance(data, dict):
        return data.get("total", len(data.get("entries", [])))
    return -1


# ─── MAIN AUDIT ─────────────────────────────────────────────────────────────

def run_audit():
    print("=" * 60)
    print("MCP + API SURFACE AUDIT")
    print("=" * 60)

    # ── 1. MCP TOOLS ────────────────────────────────────────────────────────
    print("\n[1] MCP Tools Audit...")
    session_id, init_resp = mcp_initialize()
    print(f"  Session: {session_id[:20]}..." if session_id else "  Session: FAILED")

    tools_resp = mcp_tools_list(session_id)
    tools_schema = {}

    # The HTTP MCP (FastApiMCP) exposes tools from HTTP_MCP_OPERATIONS
    # The stdio MCP exposes tools from get_stdio_tool_definitions()
    # Both are accessible via /mcp endpoint

    if "result" in tools_resp:
        tools_list = tools_resp["result"].get("tools", [])
        tools_schema = tools_resp["result"]
        print(f"  Tools found: {len(tools_list)}")
    elif "error" in tools_resp:
        print(f"  ERROR listing tools: {tools_resp['error']}")
        tools_list = []
    else:
        tools_list = []

    # Save schema
    with open("/tmp/mcp-tools-schema.json", "w") as f:
        json.dump(tools_schema, f, indent=2, ensure_ascii=False)

    # Define realistic test args for each known tool
    tool_test_args = {
        # HTTP MCP tools
        "list_legislacion": {},
        "get_norma": {"codigo": "LIVA"},
        "list_articulos": {"codigo": "LIVA"},
        "get_articulo": {"codigo": "LIVA", "numero": "1"},
        "get_articulo_historial": {"codigo": "LIVA", "numero": "1"},
        "buscar": {"q": "IVA tipo reducido"},
        "buscar_legislacion": {"q": "IVA"},
        "list_materias": {},
        "get_materia": {"tipo": "iva"},
        "buscar_doctrina": {"q": "IVA"},
        "get_doctrina": {"referencia": "V0001-24"},
        "list_modelos": {},
        "list_modelos_campanas_operativas": {},
        "get_modelo": {"codigo": "303"},
        "get_modelo_articulos": {"codigo": "303"},
        "get_modelo_casillas": {"codigo": "303"},
        "get_modelo_claves": {"codigo": "303"},
        "get_modelo_instrucciones": {"codigo": "303"},
        "get_modelo_normativa": {"codigo": "303"},
        "get_modelo_artefactos": {"codigo": "303"},
        "get_modelo_campana_operativa": {"codigo": "303"},
        "get_modelo_resumen_operativo": {"codigo": "303"},
        "get_modelo_fuentes_oficiales": {"codigo": "303"},
        "listar_convenios_dta_internacional": {},
        "detalle_convenio_dta_internacional": {"pais": "FR"},
        "listar_reglas_retencion_internacional": {},
        "calcular_retencion": {"pais": "FR", "tipo_renta": "dividendos"},
        # Stdio tools
        "consulta_fiscal": {"q": "tipo reducido IVA"},
        "listar_obligaciones_operativas": {},
        "listar_deadlines": {},
        "listar_obligaciones_aplicables": {},
        "get_obligacion_completa": {"codigo": "MOD303"},
        "agente_consulta": {"q": "IVA tipo reducido"},
        "agente_monitoreo_status": {},
        "agente_compliance_resumen": {},
    }

    # Invoke each tool
    for tool_def in tools_list:
        name = tool_def.get("name", "unknown")
        schema = tool_def.get("inputSchema", {})
        required = schema.get("required", [])
        args = tool_test_args.get(name, {})

        try:
            resp = mcp_tool_call(session_id, name, args)
            is_error = "error" in resp and resp.get("error") is not None
            result_data = resp.get("result", {})

            # Check for content
            content = result_data.get("content", []) if isinstance(result_data, dict) else []
            structured = result_data.get("structuredContent") if isinstance(result_data, dict) else None
            has_content = bool(content) or bool(structured)

            # Check provenance
            prov = has_provenance(structured) if structured else has_provenance(result_data)
            if not prov and content:
                # Check text content for provenance indicators
                text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                prov = any(f in text for f in ["boe.es", "eli/es", "source_url", "boe_reference", "aeat.es"])

            verdict = "OK" if (not is_error and has_content and prov) else \
                      "WARN" if (not is_error and has_content and not prov) else \
                      "FAIL"

            results["mcp_tools"].append({
                "tool": name,
                "input_required": required,
                "response_ok": not is_error and has_content,
                "has_provenance": prov,
                "deterministic": None,  # checked later for critical tools
                "verdict": verdict,
            })
        except Exception as e:
            results["mcp_tools"].append({
                "tool": name,
                "input_required": required,
                "response_ok": False,
                "has_provenance": False,
                "deterministic": None,
                "verdict": f"ERROR: {e!s}"[:60],
            })

    # Also test tools from tool_test_args that might not be in tools_list
    listed_names = {t.get("name") for t in tools_list}
    for name, args in tool_test_args.items():
        if name not in listed_names:
            try:
                resp = mcp_tool_call(session_id, name, args)
                is_error = "error" in resp and resp.get("error") is not None
                result_data = resp.get("result", {})
                content = result_data.get("content", []) if isinstance(result_data, dict) else []
                structured = result_data.get("structuredContent") if isinstance(result_data, dict) else None
                has_content = bool(content) or bool(structured)
                prov = has_provenance(structured) if structured else False
                verdict = "OK" if (not is_error and has_content) else "FAIL"
                results["mcp_tools"].append({
                    "tool": name,
                    "input_required": [],
                    "response_ok": not is_error and has_content,
                    "has_provenance": prov,
                    "deterministic": None,
                    "verdict": verdict,
                })
            except Exception as e:
                results["mcp_tools"].append({
                    "tool": name,
                    "input_required": [],
                    "response_ok": False,
                    "has_provenance": False,
                    "deterministic": None,
                    "verdict": f"ERROR: {e!s}"[:60],
                })

    print(f"  Tools audited: {len(results['mcp_tools'])}")

    # ── 1c. CRITICAL TOOLS ──────────────────────────────────────────────────
    print("\n[1c] Critical Tools — ground truth & not-found...")
    critical_tests = [
        # Real inputs
        ("get_articulo", {"codigo": "LIVA", "numero": "91"}, True),
        ("buscar_legislacion", {"q": "IVA"}, True),
        ("get_norma", {"codigo": "LIVA"}, True),
        ("get_modelo", {"codigo": "303"}, True),
        ("buscar_doctrina", {"q": "IVA tipo reducido"}, True),
        # Fake inputs (should return not-found)
        ("get_articulo", {"codigo": "LIVA_FAKE", "numero": "99999"}, False),
        ("get_norma", {"codigo": "NORMA_INEXISTENTE_XYZ"}, False),
        ("get_modelo", {"codigo": "99999"}, False),
        ("buscar_legislacion", {"q": "xyznonexistent12345"}, True),  # search may return empty
        ("buscar_doctrina", {"q": "xyznonexistent12345"}, True),  # search may return empty
    ]

    for tool_name, args, expect_success in critical_tests:
        try:
            resp1 = mcp_tool_call(session_id, tool_name, args, call_id=10)
            resp2 = mcp_tool_call(session_id, tool_name, args, call_id=11)

            is_error1 = "error" in resp1 and resp1.get("error") is not None
            result1 = resp1.get("result", {})
            result2 = resp2.get("result", {})

            # Determinism check
            deterministic = json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)

            # Not-found handling
            if not expect_success:
                # Should get an error or empty result, NOT fabricated data
                not_found_ok = is_error1 or (
                    isinstance(result1, dict) and (
                        not result1.get("structuredContent") or
                        result1.get("structuredContent", {}).get("detail") or
                        result1.get("structuredContent", {}).get("error")
                    )
                )
                verdict = "OK" if not_found_ok else "CRITICAL-FABRICATION"
            else:
                prov = has_provenance(result1.get("structuredContent") if isinstance(result1, dict) else result1)
                verdict = "OK" if (not is_error1 and deterministic and prov) else \
                          "WARN" if (not is_error1 and deterministic) else \
                          "CRITICAL" if not deterministic else "FAIL"

            results["critical_tools"].append({
                "tool": tool_name,
                "input": json.dumps(args),
                "expect_success": expect_success,
                "response_ok": not is_error1,
                "deterministic": deterministic,
                "verdict": verdict,
            })
        except Exception as e:
            results["critical_tools"].append({
                "tool": tool_name,
                "input": json.dumps(args),
                "expect_success": expect_success,
                "response_ok": False,
                "deterministic": False,
                "verdict": f"ERROR: {e!s}"[:60],
            })

    # ── 2. REST API SURFACES ────────────────────────────────────────────────
    print("\n[2] REST API Surface Audit...")

    rest_endpoints = [
        # Legislacion
        ("/v1/legislacion", None),
        ("/v1/legislacion/LIVA", None),
        ("/v1/legislacion/LIVA/articulos", None),
        ("/v1/legislacion/LIVA/articulos/91", None),
        ("/v1/legislacion/LIVA/articulos/91/historial", None),
        ("/v1/legislacion/buscar", {"q": "IVA"}),
        ("/v1/legislacion/cobertura", None),
        # Doctrina
        ("/v1/doctrina/buscar", {"q": "IVA"}),
        # Modelos
        ("/v1/modelos", None),
        ("/v1/modelos/303", None),
        ("/v1/modelos/303/articulos", None),
        ("/v1/modelos/campanas-operativas", None),
        # Materias
        ("/v1/materias", None),
        # Buscar
        ("/v1/buscar", {"q": "IVA tipo reducido"}),
        # Consulta
        ("/v1/consulta", {"q": "tipo reducido IVA"}),
        # Sources/freshness
        ("/v1/sources/manifest", None),
        ("/v1/sources/freshness", None),
        # Observability
        ("/v1/observability/dashboard", None),
        # Status/health
        ("/health", None),
        ("/status", None),
        # CNMV
        ("/v1/cnmv", None),
        # DGT
        ("/v1/dgt/doctrina/buscar", {"q": "rendimientos"}),
        # AEPD
        ("/v1/aepd", None),
        # SEPBLAC
        ("/v1/sepblac", None),
        # BDE
        ("/v1/bde", None),
        # BORME
        ("/v1/borme", None),
        # BDNS
        ("/v1/bdns", None),
        # Query audit
        ("/v1/query-audit", {"limit": 5}),
        # Obligaciones
        ("/v1/obligaciones", None),
        # EUR-Lex
        ("/v1/eurlex", None),
    ]

    for path, params in rest_endpoints:
        try:
            status, data = api_get(path, params)
            prov = has_provenance(data) if status == 200 else False
            domain_issues = check_provenance_url_domain(data) if status == 200 else []

            verdict = "OK" if (status in (200, 404) and (status == 404 or prov)) else \
                      "WARN" if (status == 200 and not prov) else \
                      "FAIL" if status >= 500 else "OK"

            results["rest_surfaces"].append({
                "path": path,
                "status": status,
                "has_provenance": prov,
                "domain_issues": domain_issues[:3],
                "verdict": verdict,
            })
        except Exception as e:
            results["rest_surfaces"].append({
                "path": path,
                "status": -1,
                "has_provenance": False,
                "domain_issues": [],
                "verdict": f"ERROR: {e!s}"[:60],
            })

    print(f"  Endpoints audited: {len(results['rest_surfaces'])}")

    # ── 3. GROUND TRUTH BENCHMARK ───────────────────────────────────────────
    print("\n[3] Ground Truth Benchmark...")

    # 3a: get_articulo(LIVA, 91) — check BOE URL exists
    try:
        boe_url = "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740"
        r = requests.head(boe_url, timeout=10, allow_redirects=True)
        boe_url_exists = r.status_code < 400
    except Exception:
        boe_url_exists = None  # Cannot verify

    status_91, data_91 = api_get("/v1/legislacion/LIVA/articulos/91")
    gt_articulo_91 = {
        "boe_url_exists": boe_url_exists,
        "api_status": status_91,
        "has_boe_reference": "BOE-A-1992-28740" in json.dumps(data_91) if status_91 == 200 else False,
    }

    # 3b: get_norma(LIVA) — check eli_uri
    status_liva, data_liva = api_get("/v1/legislacion/LIVA")
    expected_eli = "https://www.boe.es/eli/es/l/1992/12/28/37"
    gt_norma_liva = {
        "api_status": status_liva,
        "eli_uri_match": expected_eli in json.dumps(data_liva) if status_liva == 200 else False,
        "actual_eli": data_liva.get("eli_uri", "NOT_FOUND") if isinstance(data_liva, dict) else "N/A",
    }

    # 3c: buscar_legislacion('IVA') — should return LIVA
    status_buscar, data_buscar = api_get("/v1/legislacion/buscar", {"q": "IVA"})
    gt_buscar = {
        "api_status": status_buscar,
        "has_liva": "LIVA" in json.dumps(data_buscar) if status_buscar == 200 else False,
        "result_count": len(data_buscar.get("resultados", [])) if isinstance(data_buscar, dict) else 0,
    }

    results["ground_truth"] = {
        "articulo_91": gt_articulo_91,
        "norma_liva": gt_norma_liva,
        "buscar_iva": gt_buscar,
    }

    # ── 4. AUDIT LOG COVERAGE ───────────────────────────────────────────────
    print("\n[4] Audit Log Coverage...")

    # Count before
    status_before, data_before = api_get("/v1/query-audit", {"limit": 1})
    total_before = data_before.get("total", 0) if isinstance(data_before, dict) else 0

    # Make 10 distinct tool calls
    audit_tools = [
        ("buscar_legislacion", {"q": "IRPF"}),
        ("get_norma", {"codigo": "LIVA"}),
        ("get_articulo", {"codigo": "LIVA", "numero": "1"}),
        ("buscar_doctrina", {"q": "IVA"}),
        ("list_modelos", {}),
        ("get_modelo", {"codigo": "303"}),
        ("list_materias", {}),
        ("buscar_legislacion", {"q": "sociedades"}),
        ("get_articulo", {"codigo": "LIVA", "numero": "91"}),
        ("buscar_legislacion", {"q": "IRNR"}),
    ]

    for name, args in audit_tools:
        mcp_tool_call(session_id, name, args, call_id=100)
        time.sleep(0.2)

    time.sleep(1)  # Allow async audit writes

    # Count after
    status_after, data_after = api_get("/v1/query-audit", {"limit": 1})
    total_after = data_after.get("total", 0) if isinstance(data_after, dict) else 0

    delta = total_after - total_before
    results["audit_log"] = {
        "total_before": total_before,
        "total_after": total_after,
        "delta": delta,
        "expected_min": 10,
        "verdict": "OK" if delta >= 10 else "CRITICAL" if delta == 0 else "WARN",
    }
    print(f"  Audit delta: {delta} (expected >=10)")

    # ── 5. DETERMINISM ──────────────────────────────────────────────────────
    print("\n[5] Determinism Check...")

    det_results = []
    for i in range(3):
        status, data = api_get("/v1/legislacion/buscar", {"q": "IVA"})
        det_results.append(json.dumps(data, sort_keys=True, ensure_ascii=False))
        time.sleep(0.5)

    all_same = all(r == det_results[0] for r in det_results)
    results["determinism"] = {
        "test": "buscar_legislacion('IVA') x3",
        "all_identical": all_same,
        "hashes": [hashlib.md5(r.encode()).hexdigest()[:12] for r in det_results],
        "verdict": "OK" if all_same else "CRITICAL",
    }
    if not all_same:
        results["critical_findings"].append("CRITICAL: buscar_legislacion('IVA') is NON-DETERMINISTIC")

    # ── 6. UNCERTAINTY HANDLING ─────────────────────────────────────────────
    print("\n[6] Uncertainty Handling...")

    # Check confianza in articulo response
    status_conf, data_conf = api_get("/v1/legislacion/LIVA/articulos/91")
    has_confianza = False
    if isinstance(data_conf, dict):
        has_confianza = "confianza" in data_conf or "confianza" in json.dumps(data_conf)

    # Check completeness in audit log
    status_audit, data_audit = api_get("/v1/query-audit", {"limit": 5})
    has_completeness = False
    if isinstance(data_audit, dict):
        entries = data_audit.get("entries", [])
        for entry in entries:
            if isinstance(entry, dict) and "completeness" in entry:
                has_completeness = True
                break

    results["uncertainty"] = {
        "confianza_in_articulo": has_confianza,
        "completeness_in_audit": has_completeness,
        "verdict": "OK" if (has_confianza and has_completeness) else "WARN",
    }

    # ── COMPILE CRITICAL FINDINGS ───────────────────────────────────────────
    for tool_result in results["mcp_tools"]:
        if "FAIL" in str(tool_result.get("verdict", "")):
            results["critical_findings"].append(
                f"MCP tool '{tool_result['tool']}' FAILED"
            )

    for ct in results["critical_tools"]:
        if "CRITICAL" in str(ct.get("verdict", "")):
            results["critical_findings"].append(
                f"Critical tool '{ct['tool']}' with {ct['input']}: {ct['verdict']}"
            )

    for ep in results["rest_surfaces"]:
        if ep.get("status", 0) >= 500:
            results["critical_findings"].append(
                f"REST endpoint {ep['path']} returned {ep['status']}"
            )

    print(f"\n  Critical findings: {len(results['critical_findings'])}")

    # ── SAVE RAW RESULTS ────────────────────────────────────────────────────
    with open("/tmp/audit-results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print("\n[DONE] Results saved to /tmp/audit-results.json")
    return results


if __name__ == "__main__":
    run_audit()
