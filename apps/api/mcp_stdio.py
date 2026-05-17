"""MCP stdio server for esdata — exposes consulta_fiscal as a tool for LLM clients."""

import json
import sys
import uuid
from typing import Any

import anyio
import httpx

# FastAPI app must be imported before any DB access
from db import db_session
from main import app
from mcp_catalog import get_stdio_tool_definitions
from mcp_tools_perfil import (
    PerfilNotFoundError,
    calendario_obligaciones_perfil,
    listar_perfiles_entidad,
    obtener_obligaciones_perfil,
)
from mcp_request_context import (
    get_mcp_request_id,
    get_mcp_user_id,
    mcp_internal_request,
    mcp_request_scope,
)


def _next_stdio_request_id() -> str:
    return f"mcp-{uuid.uuid4().hex[:12]}"


def _advertised_stdio_tool_names() -> set[str]:
    return {tool["name"] for tool in get_stdio_tool_definitions()}


def _response_summary_from_payload(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or json.dumps(error, ensure_ascii=False))[:4000]

    result = payload.get("result")
    if not isinstance(result, dict):
        return ""

    content = result.get("content")
    if isinstance(content, list):
        text_blocks = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text")
        ]
        if text_blocks:
            return "\n".join(text_blocks)[:4000]

    structured_content = result.get("structuredContent")
    if structured_content is not None:
        return json.dumps(structured_content, ensure_ascii=False)[:4000]

    return ""


def _get_correlated_http_entry(request_id: str):
    from services.query_audit import get_query_audit_service

    entries = get_query_audit_service().get_by_request_id(request_id)
    for entry in reversed(entries):
        if not entry.path.startswith("/mcp/tools/"):
            return entry
    return None


def _log_mcp_call(
    tool_name: str,
    arguments: dict,
    request_id: str,
    user_id: str,
    response_payload: dict[str, Any],
    response_time_ms: float,
) -> None:
    """Log MCP stdio tool call to query audit log for E2E traceability."""

    from services.query_audit import get_query_audit_service

    correlated_entry = _get_correlated_http_entry(request_id)
    response_summary = _response_summary_from_payload(response_payload)
    if not response_summary:
        response_summary = f"tool={tool_name} duration={response_time_ms:.0f}ms"

    retrieved_chunks: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    confidence: dict[str, Any] = {"score": 0.0, "label": "no_verificado"}
    completeness = "parcial"
    verified = False
    model_version = "mcp-stdio"
    config_version = None
    grounding_status = "n/a"
    prompt_injection_detected = False
    grounding_summary: dict[str, Any] = {}

    if correlated_entry is not None:
        retrieved_chunks = correlated_entry.retrieved_chunks
        sources = correlated_entry.sources
        confidence = correlated_entry.confidence
        completeness = correlated_entry.completeness
        verified = correlated_entry.verified
        model_version = correlated_entry.model_version or model_version
        config_version = correlated_entry.config_version
        grounding_status = correlated_entry.grounding_status or grounding_status
        prompt_injection_detected = correlated_entry.prompt_injection_detected
        grounding_summary = correlated_entry.grounding_summary

    get_query_audit_service().record_query(
        request_id=request_id,
        user_id=user_id,
        path=f"/mcp/tools/{tool_name}",
        query_text=json.dumps(arguments, ensure_ascii=False)[:2000],
        retrieved_chunks=retrieved_chunks,
        response_summary=response_summary,
        response_payload=response_payload,
        tool_name=tool_name,
        sources=sources,
        confidence=confidence,
        completeness=completeness,
        verified=verified,
        model_version=model_version,
        config_version=config_version,
        grounding_status=grounding_status,
        prompt_injection_detected=prompt_injection_detected,
        grounding_summary=grounding_summary,
    )


class MCPStdioServer:
    """Minimal MCP stdio server using Streamable HTTP transport concept."""

    def __init__(self):
        self._message_id = 0
        self._http_client: httpx.AsyncClient | None = None
        self._sync_client: httpx.Client | None = None

    def _next_id(self) -> int:
        self._message_id += 1
        return self._message_id

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://apiserver",
                timeout=30.0,
            )
        return self._http_client

    async def _call_endpoint(self, method: str, path: str, params: dict | None = None) -> dict:
        client = await self._get_client()
        headers: dict[str, str] = {}
        request_id = get_mcp_request_id()
        user_id = get_mcp_user_id()
        if request_id:
            headers["x-request-id"] = request_id
        if user_id:
            headers["x-user-id"] = user_id
        with mcp_internal_request():
            response = await client.request(method.upper(), path, params=params, headers=headers)
        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
        }

    def _send(self, data: dict[str, Any]):
        payload = json.dumps(data, ensure_ascii=False)
        sys.stdout.write(f"Content-Length: {len(payload.encode('utf-8'))}\r\n\r\n{payload}")
        sys.stdout.flush()

    async def _read_exact(self, stream, content_length: int) -> bytes:
        chunks: list[bytes] = []
        remaining = content_length
        while remaining > 0:
            chunk = await stream.receive_some(remaining)
            if not chunk:
                raise EOFError("stdin closed while reading MCP payload")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    async def _read_message(self, stream) -> dict[str, Any] | None:
        raw_line = await stream.receive_line()
        if not raw_line:
            raise EOFError("stdin closed")

        line = raw_line.decode("utf-8").strip("\r\n")
        if not line:
            return None

        if line.lower().startswith("content-length:"):
            headers: dict[str, str] = {}
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
            while True:
                raw_header = await stream.receive_line()
                if raw_header in {b"\r\n", b"\n", b""}:
                    break
                header_line = raw_header.decode("utf-8").strip("\r\n")
                if not header_line:
                    break
                if ":" not in header_line:
                    raise ValueError(f"Malformed MCP stdio header: {header_line}")
                h_name, h_value = header_line.split(":", 1)
                headers[h_name.strip().lower()] = h_value.strip()

            content_length = int(headers["content-length"])
            raw = await self._read_exact(stream, content_length)
            return json.loads(raw.decode("utf-8"))

        return json.loads(line.strip())

    async def run(self):
        try:
            stdin_raw = anyio.wrap_socket(sys.stdin.detach())
            while True:
                try:
                    message = await self._read_message(stdin_raw)
                except EOFError:
                    break
                except (json.JSONDecodeError, KeyError, ValueError) as exc:
                    self._send_error(None, -32700, f"Parse error: {exc}")
                    continue
                if message is None:
                    continue

                msg_type = message.get("method", "")
                msg_id = message.get("id")

                if msg_type == "initialize":
                    self._handle_initialize(message)
                elif msg_type == "notifications/initialized":
                    pass  # ignore
                elif msg_type == "tools/list":
                    self._handle_tools_list(msg_id)
                elif msg_type == "tools/call":
                    await self._handle_tools_call(message, msg_id)
                elif msg_type == "ping":
                    self._send_jsonrpc(msg_id, None)
                else:
                    self._send_error(msg_id, -32601, f"Unknown method: {msg_type}")
        finally:
            if self._http_client:
                await self._http_client.aclose()

    def _send_jsonrpc(self, request_id: Any, result: Any | None, error: dict | None = None):
        if error:
            self._send({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": error,
            })
        else:
            self._send({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            })

    def _send_error(self, request_id: Any, code: int, message: str):
        self._send_jsonrpc(request_id, None, {"code": code, "message": message})

    def _handle_initialize(self, message: dict):
        self._send({
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "esdata-fiscal",
                    "version": "0.1.0",
                },
            },
        })

    def _handle_tools_list(self, msg_id: Any):
        tools = get_stdio_tool_definitions()
        self._send_jsonrpc(msg_id, {"tools": tools})

    async def _handle_tools_call(self, message: dict, msg_id: Any):
        params = message.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        request_id = _next_stdio_request_id()
        user_id = "mcp-client"

        import time as _time
        _start = _time.time()
        buffered_messages: list[dict[str, Any]] = []
        original_send = self._send

        def _buffer_message(data: dict[str, Any]) -> None:
            buffered_messages.append(data)

        self._send = _buffer_message

        try:
            try:
                with mcp_request_scope(request_id=request_id, user_id=user_id):
                    await self._dispatch_tool(tool_name, arguments, msg_id)
            except Exception as e:
                buffered_messages.append({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"Error executing {tool_name}: {e!s}"},
                })

            if not buffered_messages:
                buffered_messages.append({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"Tool {tool_name} produced no response."},
                })

            _elapsed = (_time.time() - _start) * 1000
            try:
                _log_mcp_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    request_id=request_id,
                    user_id=user_id,
                    response_payload=buffered_messages[-1],
                    response_time_ms=_elapsed,
                )
            except Exception as e:
                original_send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"Audit persistence error: {e!s}"},
                })
                return
        finally:
            self._send = original_send

        for payload in buffered_messages:
            original_send(payload)

    async def _dispatch_tool(self, tool_name: str, arguments: dict, msg_id: Any):
        if tool_name not in _advertised_stdio_tool_names():
            self._send_error(msg_id, -32601, f"Unknown tool: {tool_name}")
            return

        if tool_name == "consulta_fiscal":
            try:

                q = arguments.get("q", "")
                sujeto = arguments.get("sujeto", "")
                pais = arguments.get("pais", "")
                tipo_operacion = arguments.get("tipo_operacion", "")
                vigente_en = arguments.get("vigente_en")
                sources = arguments.get("sources")
                hybrid_weight = arguments.get("hybrid_weight")
                params = {"q": q, "sujeto": sujeto, "pais": pais, "tipo_operacion": tipo_operacion}
                if vigente_en:
                    params["vigente_en"] = vigente_en
                if sources:
                    params["sources"] = sources
                if hybrid_weight is not None:
                    params["hybrid_weight"] = hybrid_weight

                # Call the actual endpoint
                result = await self._call_endpoint(
                    "GET", "/v1/consulta",
                    params=params,
                )
                status_code = result["status_code"]
                data = result["data"] or {}

                if status_code == 200:
                    # Format as readable text for the LLM
                    output = self._format_response(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing consulta: {e!s}")
        elif tool_name == "listar_obligaciones_operativas":
            try:
                ambito = arguments.get("ambito")
                frecuencia = arguments.get("frecuencia")
                con_sancion = arguments.get("con_sancion", True)
                limite = arguments.get("limite", 50)

                result = await self._call_endpoint(
                    "GET", "/v1/obligaciones/operativas",
                    params={"ambito": ambito, "frecuencia": frecuencia, "con_sancion": con_sancion, "limite": limite},
                )
                status_code = result["status_code"]
                data = result["data"] or {}

                if status_code == 200:
                    output = self._format_obligaciones_operativas(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_obligaciones_operativas: {e!s}")
        elif tool_name == "listar_deadlines":
            try:
                dias_proximo = arguments.get("dias_proximo", 30)
                frecuencia = arguments.get("frecuencia")

                result = await self._call_endpoint(
                    "GET", "/v1/obligaciones/deadlines",
                    params={"dias_proximo": dias_proximo, "frecuencia": frecuencia},
                )
                status_code = result["status_code"]
                data = result["data"] or {}

                if status_code == 200:
                    output = self._format_deadlines(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_deadlines: {e!s}")

        elif tool_name == "listar_obligaciones_aplicables":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/obligaciones/aplicables",
                    params={
                        "tipo_entidad": arguments.get("tipo_entidad", "sociedad_valores"),
                        "reporting_reservado": arguments.get("reporting_reservado", True),
                        "aml_cft_reforzado": arguments.get("aml_cft_reforzado", True),
                        "cross_border_ue": arguments.get("cross_border_ue", False),
                        "limite": arguments.get("limite", 100),
                        "offset": arguments.get("offset", 0),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                output = self._format_obligaciones_aplicables(data)
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": output}],
                    "structuredContent": data,
                })
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_obligaciones_aplicables: {e!s}")
        elif tool_name == "get_obligacion_completa":
            try:
                codigo = arguments.get("codigo", "")

                result = await self._call_endpoint("GET", f"/v1/obligaciones/{codigo}")
                status_code = result["status_code"]
                data = result["data"] or {}

                if status_code == 200:
                    output = self._format_obligacion_completa(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_obligacion_completa: {e!s}")
        elif tool_name == "list_modelos_por_supuesto":
            try:
                result = await self._call_endpoint(
                    "GET",
                    "/v1/modelos/por-supuesto",
                    params={
                        "tipo_entidad": arguments.get("tipo_entidad", "sociedad_valores"),
                        "clientes_residentes": arguments.get("clientes_residentes", False),
                        "clientes_no_residentes": arguments.get("clientes_no_residentes", False),
                        "tipo_renta": arguments.get("tipo_renta"),
                        "tipo_operacion": arguments.get("tipo_operacion"),
                        "incluir_obligacion_sociedad": arguments.get("incluir_obligacion_sociedad", False),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}

                if status_code == 200:
                    output = self._format_modelos_por_supuesto(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_modelos_por_supuesto: {e!s}")
        elif tool_name == "agente_consulta":
            try:
                q = arguments.get("q", "")
                sujeto_arg = arguments.get("sujeto", "")
                tipo_entidad = arguments.get("tipo_entidad", "sociedad_valores")

                sujeto = sujeto_arg or self._entidad_to_sujeto(tipo_entidad)

                result = await self._call_endpoint(
                    "GET", "/v1/consulta",
                    params={"q": q, "sujeto": sujeto},
                )
                status_code = result["status_code"]
                data = result["data"] or {}

                if status_code == 200:
                    output = self._format_response(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing agente_consulta: {e!s}")
        elif tool_name == "agente_monitoreo_status":
            try:
                from agent_monitor import get_monitor_status

                status = get_monitor_status()
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": json.dumps(status, ensure_ascii=False, indent=2)}],
                    "structuredContent": status,
                })
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error getting monitor status: {e!s}")
        elif tool_name == "agente_compliance_resumen":
            try:
                estado = arguments.get("estado")
                limite = arguments.get("limite", 20)

                params = {}
                if estado:
                    params["estado"] = estado
                params["limite"] = limite

                result = await self._call_endpoint(
                    "GET", "/v1/compliance/workflow",
                    params=params,
                )
                status_code = result["status_code"]
                data = result["data"] or {}

                if status_code == 200:
                    output = self._format_compliance_resumen(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing agente_compliance_resumen: {e!s}")
        elif tool_name == "list_sfdr_products":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/sfdr/products",
                    params={
                        "product_type": arguments.get("product_type"),
                        "status": arguments.get("status"),
                        "search": arguments.get("search"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_sfdr_products(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_sfdr_products: {e!s}")
        elif tool_name == "get_sfdr_product":
            try:
                item_id = arguments.get("item_id")
                result = await self._call_endpoint("GET", f"/v1/sfdr/products/{item_id}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_sfdr_product_detail(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_sfdr_product: {e!s}")
        elif tool_name == "list_sfdr_pacai_indicators":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/sfdr/pacai-indicators",
                    params={
                        "product_id": arguments.get("product_id"),
                        "indicator_code": arguments.get("indicator_code"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_sfdr_pacai(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_sfdr_pacai_indicators: {e!s}")
        elif tool_name == "get_sfdr_pacai_indicator":
            try:
                result = await self._call_endpoint("GET", f"/v1/sfdr/pacai-indicators/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_sfdr_pacai_indicator: {e!s}")
        elif tool_name == "list_sfdr_entity_paci":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/sfdr/entity-paci",
                    params={
                        "entity_id": arguments.get("entity_id"),
                        "reporting_year": arguments.get("reporting_year"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_sfdr_entity_paci(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_sfdr_entity_paci: {e!s}")
        elif tool_name == "get_sfdr_entity_paci":
            try:
                result = await self._call_endpoint("GET", f"/v1/sfdr/entity-paci/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_sfdr_entity_paci: {e!s}")
        elif tool_name == "list_sfdr_pre_contractual":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/sfdr/pre-contractual",
                    params={
                        "product_id": arguments.get("product_id"),
                        "document_type": arguments.get("document_type"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_sfdr_pre_contractual(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_sfdr_pre_contractual: {e!s}")
        elif tool_name == "get_sfdr_pre_contractual":
            try:
                result = await self._call_endpoint("GET", f"/v1/sfdr/pre-contractual/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_sfdr_pre_contractual: {e!s}")
        elif tool_name == "list_sfdr_annual_reports":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/sfdr/annual-reports",
                    params={
                        "entity_id": arguments.get("entity_id"),
                        "reporting_year": arguments.get("reporting_year"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_sfdr_annual_reports(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_sfdr_annual_reports: {e!s}")
        elif tool_name == "get_sfdr_annual_report":
            try:
                result = await self._call_endpoint("GET", f"/v1/sfdr/annual-reports/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_sfdr_annual_report: {e!s}")
        elif tool_name == "list_csrd_entity_reports":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/csrd/entity-reports",
                    params={
                        "entity_id": arguments.get("entity_id"),
                        "reporting_year": arguments.get("reporting_year"),
                        "assurance_status": arguments.get("assurance_status"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_csrd_entity_reports(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_csrd_entity_reports: {e!s}")
        elif tool_name == "get_csrd_entity_report":
            try:
                result = await self._call_endpoint("GET", f"/v1/csrd/entity-reports/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_csrd_entity_report: {e!s}")
        elif tool_name == "list_csrd_esg_data_points":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/csrd/esg-data-points",
                    params={
                        "report_id": arguments.get("report_id"),
                        "topic": arguments.get("topic"),
                        "indicator_code": arguments.get("indicator_code"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_csrd_esg_data(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_csrd_esg_data_points: {e!s}")
        elif tool_name == "get_csrd_esg_data_point":
            try:
                result = await self._call_endpoint("GET", f"/v1/csrd/esg-data-points/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_csrd_esg_data_point: {e!s}")
        elif tool_name == "list_csrd_ess":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/csrd/ess",
                    params={
                        "topic": arguments.get("topic"),
                        "applicable_from_year": arguments.get("applicable_from_year"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_csrd_ess(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_csrd_ess: {e!s}")
        elif tool_name == "get_csrd_ess":
            try:
                result = await self._call_endpoint("GET", f"/v1/csrd/ess/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_csrd_ess: {e!s}")
        elif tool_name == "list_csrd_double_materiality":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/csrd/double-materiality",
                    params={"entity_id": arguments.get("entity_id")},
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_csrd_double_materiality(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_csrd_double_materiality: {e!s}")
        elif tool_name == "get_csrd_double_materiality":
            try:
                result = await self._call_endpoint("GET", f"/v1/csrd/double-materiality/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_csrd_double_materiality: {e!s}")
        elif tool_name == "list_aifmd_funds":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/aifmd/funds",
                    params={
                        "fund_type": arguments.get("fund_type"),
                        "status": arguments.get("status"),
                        "home_member_state": arguments.get("home_member_state"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_aifmd_funds(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_aifmd_funds: {e!s}")
        elif tool_name == "get_aifmd_fund":
            try:
                result = await self._call_endpoint("GET", f"/v1/aifmd/funds/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_aifmd_fund: {e!s}")
        elif tool_name == "list_aifmd_regulatory_reports":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/aifmd/regulatory-reports",
                    params={
                        "fund_id": arguments.get("fund_id"),
                        "report_type": arguments.get("report_type"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_aifmd_reports(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_aifmd_regulatory_reports: {e!s}")
        elif tool_name == "get_aifmd_regulatory_report":
            try:
                result = await self._call_endpoint("GET", f"/v1/aifmd/regulatory-reports/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_aifmd_regulatory_report: {e!s}")
        elif tool_name == "list_aifmd_liquidity_management":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/aifmd/liquidity-management",
                    params={
                        "fund_id": arguments.get("fund_id"),
                        "redemption_suspended": arguments.get("redemption_suspended"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_aifmd_liquidity(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_aifmd_liquidity_management: {e!s}")
        elif tool_name == "get_aifmd_liquidity_management":
            try:
                result = await self._call_endpoint("GET", f"/v1/aifmd/liquidity-management/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_aifmd_liquidity_management: {e!s}")
        elif tool_name == "list_ucits_funds":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/ucits/funds",
                    params={
                        "management_company": arguments.get("management_company"),
                        "status": arguments.get("status"),
                        "home_member_state": arguments.get("home_member_state"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_ucits_funds(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_ucits_funds: {e!s}")
        elif tool_name == "get_ucits_fund":
            try:
                result = await self._call_endpoint("GET", f"/v1/ucits/funds/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_ucits_fund: {e!s}")
        elif tool_name == "list_ucits_regulatory_reports":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/ucits/regulatory-reports",
                    params={
                        "fund_id": arguments.get("fund_id"),
                        "report_type": arguments.get("report_type"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_ucits_reports(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_ucits_regulatory_reports: {e!s}")
        elif tool_name == "get_ucits_regulatory_report":
            try:
                result = await self._call_endpoint("GET", f"/v1/ucits/regulatory-reports/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_ucits_regulatory_report: {e!s}")
        elif tool_name == "list_crd_capital_positions":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/crd/capital-positions",
                    params={
                        "entity_id": arguments.get("entity_id"),
                        "reporting_date": arguments.get("reporting_date"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_crd_capital(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_crd_capital_positions: {e!s}")
        # ── DTA / Convenios Doble Imposición ──
        elif tool_name == "listar_convenios_dta_internacional":
            try:
                pais_a = arguments.get("pais_a")
                pais_b = arguments.get("pais_b")
                estado = arguments.get("estado", "vigente")
                tipo_acuerdo = arguments.get("tipo_acuerdo")
                
                # Build params — only pass non-empty filters
                params = {}
                if pais_a:
                    params["pais_a"] = pais_a
                if pais_b:
                    params["pais_b"] = pais_b
                if estado:
                    params["estado"] = estado
                if tipo_acuerdo:
                    params["tipo_acuerdo"] = tipo_acuerdo
                
                result = await self._call_endpoint(
                    "GET", "/v1/internacional/convenios",
                    params=params,
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    convenios = data.get("convenios", [])
                    lines = [f"Convenios DTA: {len(convenios)} resultados (total: {data.get('total', len(convenios))})"]
                    for c in convenios[:50]:
                        firma = c.get("fecha_firma", "")
                        vigencia = c.get("fecha_vigencia", "")
                        lines.append(f"  [{c.get('codigo', '')}] {c.get('pais_origen', '')} — {c.get('fecha_vigencia', '').strftime('%Y') if hasattr(c.get('fecha_vigencia', ''), 'strftime') else c.get('fecha_vigencia', '')} | estado: {c.get('estado', '')}")
                    lines.append(f"\n... (mostrando {min(50, len(convenios))} de {len(convenios)})")
                    lines.append(f"\nPara detalle de un convenio: usar detalle_convenio_dta_internacional con codigo='{convenios[0].get('codigo', '') if convenios else 'N/A'}'")
                    output = "\n".join(lines)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_convenios_dta_internacional: {e!s}")
        elif tool_name == "detalle_convenio_dta_internacional":
            try:
                codigo = arguments.get("codigo", "")
                result = await self._call_endpoint("GET", f"/v1/internacional/convenios/{codigo}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    lines = [
                        f"Convenio DTA: {data.get('pais_origen', '')} — España",
                        f"  Codigo: {data.get('codigo', '')}",
                        f"  Fecha firma: {data.get('fecha_firma', '')}",
                        f"  Fecha vigencia: {data.get('fecha_vigencia', '')}",
                        f"  Estado: {data.get('estado', '')}",
                        f"  Tipo: {data.get('tipo_acuerdo', '')}",
                        f"  BOE ref: {data.get('boe_referencia', 'N/A')}",
                        f"  Articulos: {json.dumps(data.get('articulos', {}), ensure_ascii=False)[:500]}",
                        f"  Texto completo: {data.get('texto_completo', 'N/A')[:1000]}",
                    ]
                    output = "\n".join(lines)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing detalle_convenio_dta_internacional: {e!s}")
        elif tool_name == "listar_reglas_retencion_internacional":
            try:
                tipo_renta = arguments.get("tipo_renta")
                pais = arguments.get("pais")
                estado = arguments.get("estado", "activo")
                result = await self._call_endpoint(
                    "GET", "/v1/internacional/convenios/retenciones",
                    params={
                        "tipo_renta": tipo_renta,
                        "pais": pais,
                        "estado": estado,
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    reglas = data.get("reglas", [])
                    lines = [f"Reglas retencion internacional: {len(reglas)} resultados"]
                    for r in reglas[:30]:
                        lines.append(f"  [{r.get('codigo', '')}] {r.get('tipo_renta_espanol', r.get('tipo_renta', ''))} — Pais {r.get('pais_aplicable', 'N/A')} | Default: {r.get('tipo_retencion_default','')}% | DTA: {r.get('tipo_retencion_dta','')}%")
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": "\n".join(lines)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_reglas_retencion_internacional: {e!s}")
        elif tool_name == "calcular_retencion":
            try:
                tipo_renta = arguments.get("tipo_renta", "")
                pais_residencia = arguments.get("pais_residencia", "")
                entidad_giin = arguments.get("entidad_giin")
                result = await self._call_endpoint(
                    "POST", "/v1/internacional/convenios/retencion",
                    json={
                        "tipo_renta": tipo_renta,
                        "pais_residencia": pais_residencia,
                        "entidad_giin": entidad_giin,
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    lines = [
                        f"Calculo retencion aplicada:",
                        f"  Pais residencia: {data.get('pais_residencia', 'N/A')}",
                        f"  Tipo renta: {data.get('tipo_renta', 'N/A')}",
                        f"  Retencion aplicable: {data.get('tipo_retencion_aplicable', 'N/A')}%",
                        f"  Tiene convenio DTA: {data.get('tiene_convenio_dta', False)}",
                        f"  Convenio: {data.get('codigo_convenio', 'N/A')}",
                        f"  Requiere W-8: {data.get('requiere_w8', True)}",
                        f"  Formulario: {data.get('formulario_recomendado', 'N/A')}",
                        f"  Notas: {data.get('notas', 'N/A')}",
                    ]
                    output = "\n".join(lines)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing calcular_retencion: {e!s}")
        elif tool_name == "list_crd_capital_position":
            try:
                result = await self._call_endpoint("GET", f"/v1/crd/capital-positions/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_crd_capital_position: {e!s}")
        elif tool_name == "list_crd_stress_tests":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/crd/stress-tests",
                    params={
                        "entity_id": arguments.get("entity_id"),
                        "test_date": arguments.get("test_date"),
                        "scenario_name": arguments.get("scenario_name"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_crd_stress_tests(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_crd_stress_tests: {e!s}")
        elif tool_name == "get_crd_stress_test":
            try:
                result = await self._call_endpoint("GET", f"/v1/crd/stress-tests/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_crd_stress_test: {e!s}")
        elif tool_name == "list_brrd_bail_in":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/crd/bail-in",
                    params={"entity_id": arguments.get("entity_id")},
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_brrd_bail_in(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_brrd_bail_in: {e!s}")
        elif tool_name == "get_brrd_bail_in":
            try:
                result = await self._call_endpoint("GET", f"/v1/crd/bail-in/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_brrd_bail_in: {e!s}")
        elif tool_name == "list_emir_trade_reports":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/emir/trade-reports",
                    params={
                        "asset_class": arguments.get("asset_class"),
                        "instrument_class": arguments.get("instrument_class"),
                        "clearing_obligation_applied": arguments.get("clearing_obligation_applied"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_emir_trades(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_emir_trade_reports: {e!s}")
        elif tool_name == "get_emir_trade_report":
            try:
                result = await self._call_endpoint("GET", f"/v1/emir/trade-reports/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_emir_trade_report: {e!s}")
        elif tool_name == "list_emir_clearing_members":
            try:
                result = await self._call_endpoint(
                    "GET", "/v1/emir/clearing-members",
                    params={
                        "clearing_type": arguments.get("clearing_type"),
                        "status": arguments.get("status"),
                    },
                )
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    output = self._format_emir_clearing(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing list_emir_clearing_members: {e!s}")
        elif tool_name == "get_emir_clearing_member":
            try:
                result = await self._call_endpoint("GET", f"/v1/emir/clearing-members/{arguments.get('item_id')}")
                status_code = result["status_code"]
                data = result["data"] or {}
                if status_code == 200:
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_emir_clearing_member: {e!s}")
        elif tool_name == "listar_perfiles_entidad":
            try:
                with db_session() as db:
                    perfiles = [perfil.model_dump() for perfil in listar_perfiles_entidad(db)]
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": json.dumps(perfiles, ensure_ascii=False)}],
                    "structuredContent": {"perfiles": perfiles},
                })
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_perfiles_entidad: {e!s}")
        elif tool_name == "obtener_obligaciones_perfil":
            try:
                with db_session() as db:
                    payload = obtener_obligaciones_perfil(
                        db,
                        arguments.get("perfil_codigo", "sociedad_valores"),
                        arguments.get("dominio", "ALL"),
                    ).model_dump()
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                    "structuredContent": payload,
                })
            except PerfilNotFoundError as e:
                self._send_error(msg_id, -32602, str(e))
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing obtener_obligaciones_perfil: {e!s}")
        elif tool_name == "calendario_obligaciones_perfil":
            try:
                with db_session() as db:
                    payload = calendario_obligaciones_perfil(
                        db,
                        arguments.get("perfil_codigo", "sociedad_valores"),
                    ).model_dump()
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                    "structuredContent": payload,
                })
            except PerfilNotFoundError as e:
                self._send_error(msg_id, -32602, str(e))
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing calendario_obligaciones_perfil: {e!s}")
        else:
            self._send_error(msg_id, -32601, f"Unknown tool: {tool_name}")

    def _clip_text(self, value: str | None, limit: int) -> str:
        text = value or ""
        if len(text) <= limit:
            return text
        return f"{text[:limit]} [TRUNCATED: consultar structuredContent/citas para el texto completo]"

    def _format_modelos_por_supuesto(self, data: dict) -> str:
        lines = [
            f"Estado: {data.get('status', 'unknown')}",
            f"Verificado: {data.get('verified', False)}",
        ]
        confidence = data.get("confidence") or {}
        lines.append(f"Revision requerida: {confidence.get('review_required', not data.get('verified', False))}")
        lines.append(
            "Limite de uso: responder solo con evidencia devuelta por ESData; "
            "no afirmar obligatoriedad sin clasificacion confirmado y evidencia explicita."
        )
        if confidence.get("aviso"):
            lines.append(f"Aviso: {confidence['aviso']}")
        lines.append("")
        for item in data.get("modelos", []):
            lines.append(f"Modelo {item.get('codigo')} — {item.get('clasificacion')}")
            lines.append(f"  Ambito: {item.get('ambito')}")
            lines.append(f"  Condicion: {item.get('condicion_aplicacion')}")
            lines.append(f"  Motivo: {item.get('motivo')}")
        excluded = data.get("excluded_modelos") or []
        if excluded:
            lines.append("")
            lines.append("Modelos excluidos:")
            for item in excluded:
                lines.append(f"  {item.get('codigo')}: {item.get('reason')}")
        return "\n".join(lines)

    def _format_response(self, data: dict) -> str:
        """Format API response as readable text for LLM consumption."""
        lines = []
        lines.append(f"Consulta: {data['consulta']}")
        lines.append(f"Total resultados: {data['total_resultados']}")

        relevancia = data.get("relevancia")
        if relevancia:
            lines.append(f"Relevancia: {relevancia.get('nivel', 'N/A')} (score: {relevancia.get('score', 0):.2f})")
            terminos = relevancia.get("terminos_encontrados", [])
            if terminos:
                lines.append(f"  Terminos encontrados: {', '.join(terminos)}")

        confianza = data.get("confianza")
        if confianza:
            lines.append(f"Confianza: {confianza.get('nivel_texto', 'N/A')} (nivel: {confianza.get('nivel', 0)})")
            lines.append(f"  Revision requerida: {confianza.get('review_required', False)}")
            lines.append("  Limite de uso: responder solo con evidencia devuelta por ESData; no usar conocimiento externo.")
            aviso = confianza.get("aviso")
            if aviso:
                lines.append(f"  Aviso: {aviso}")
            modelos_cubiertos = confianza.get("modelos_cubiertos", [])
            if modelos_cubiertos:
                lines.append(f"  Modelos identificados: {', '.join(modelos_cubiertos)}")
            clasificados = confianza.get("resultados_clasificados", {})
            if clasificados:
                lines.append(f"  Resultados por tipo: {', '.join(f'{k}: {v}' for k, v in clasificados.items())}")

        result_metadata = data.get("result_metadata") or {}
        if result_metadata:
            lines.append(
                "Resultados devueltos: "
                f"{result_metadata.get('returned_count', data.get('total_resultados', 0))}; "
                f"truncated={result_metadata.get('truncated', False)}; "
                f"has_more={result_metadata.get('has_more', False)}"
            )

        lines.append("")

        for modelo in data.get("modelos", []):
            lines.append(f"=== Modelo {modelo['codigo']} — {modelo['nombre']} ===")
            if modelo.get("frecuencia"):
                lines.append(f"  Frecuencia: {modelo['frecuencia']}")
            if modelo.get("ventana"):
                lines.append(f"  Plazo: {modelo['ventana']}")
            if modelo.get("obligados_resumen"):
                lines.append(f"  Quien debe: {modelo['obligados_resumen']}")
            if modelo.get("canal"):
                lines.append(f"  Canal: {modelo['canal']}")
            if modelo.get("campana"):
                lines.append(f"  Campaa: {modelo['campana']}")

            for inst in modelo.get("instrucciones", []):
                lines.append(f"  [{inst['seccion'].upper()}] {inst['titulo']}:")
                lines.append(f"    {self._clip_text(inst.get('contenido'), 500)}")
            lines.append("")

        for resultado in data.get("resultados", []):
            relevancia_r = resultado.get("_relevancia", {})
            relevancia_str = ""
            if relevancia_r:
                relevancia_str = f" [relevancia: {relevancia_r.get('nivel', 'N/A')} (score: {relevancia_r.get('score', 0):.2f})]"

            if resultado["tipo"] == "normativa":
                lines.append(f"  Normativa: {resultado['norma']} art. {resultado['articulo']}{relevancia_str}")
                lines.append(f"    {self._clip_text(resultado.get('texto'), 300)}")
                evidencia = resultado.get("evidencia")
                if evidencia and evidencia.get("motivo_ranking"):
                    lines.append(f"    Motivo: {evidencia['motivo_ranking']}")
            elif resultado["tipo"] == "doctrina":
                lines.append(f"  Doctrina: {resultado.get('referencia', '')} — {resultado.get('titulo', '')}{relevancia_str}")
                lines.append(f"    {self._clip_text(resultado.get('fragmento'), 300)}")
            elif resultado["tipo"] == "obligacion":
                lines.append(f"  Obligacion: {resultado['nombre']}{relevancia_str}")
                lines.append(f"    {resultado.get('sujeto', '')} | {resultado.get('periodicidad', '')}")
            elif resultado["tipo"] == "modelo":
                lines.append(f"  Modelo: {resultado.get('codigo', '')} — {resultado.get('nombre', '')}{relevancia_str}")

        return "\n".join(lines)

    def _format_obligaciones_operativas(self, data: list[dict]) -> str:
        """Format operational obligations for LLM consumption."""
        if not data:
            return "No se encontraron obligaciones operativas con los filtros aplicados."

        lines = [f"Obligaciones operativas: {len(data)} resultados"]
        lines.append("")

        for obs in data:
            lines.append(f"=== {obs['codigo']} — {obs['nombre']} ===")
            lines.append(f"  Fuente: {obs['fuente']} | Organismo: {obs['organismo_emisor']}")
            lines.append(f"  Tipo: {obs['tipo_obligacion']} | Sujeto: {obs['sujeto_obligado']}")
            lines.append(f"  Ámbito: {obs['ambito']} | Vigencia: {obs['estado_vigencia']}")

            if obs.get("frecuencia_presentacion"):
                lines.append(f"  Frecuencia: {obs['frecuencia_presentacion']}")
            if obs.get("plazo_dias"):
                lines.append(f"  Plazo: {obs['plazo_dias']} días")
            if obs.get("ventana_presentacion"):
                lines.append(f"  Ventana: {obs['ventana_presentacion']}")
            if obs.get("trigger_presentacion"):
                lines.append(f"  Trigger: {obs['trigger_presentacion']}")
            if obs.get("canal_presentacion"):
                lines.append(f"  Canal: {obs['canal_presentacion']}")
            if obs.get("sancion_min") is not None or obs.get("sancion_max") is not None:
                min_val = obs["sancion_min"] if obs.get("sancion_min") else "N/A"
                max_val = obs["sancion_max"] if obs.get("sancion_max") else "N/A"
                lines.append(f"  Sanción: {min_val}€ - {max_val}€")
            if obs.get("recargo_voluntario"):
                lines.append(f"  Recargo voluntario: {obs['recargo_voluntario']}")
            if obs.get("recargo_involuntario"):
                lines.append(f"  Recargo involuntario: {obs['recargo_involuntario']}")
            if obs.get("interes_demora"):
                lines.append(f"  Interés demora: {obs['interes_demora']}")
            if obs.get("prescripcion_anos"):
                lines.append(f"  Prescripción: {obs['prescripcion_anos']} años")
            if obs.get("deposito_previo"):
                lines.append(f"  Depósito previo: {obs['deposito_previo']}")
            if obs.get("estado_metadato") == "borrador":
                lines.append("  ⚠️ Estado: borrador (no curado)")
            lines.append("")

        return "\n".join(lines)

    def _format_deadlines(self, data: list[dict]) -> str:
        """Format upcoming deadlines for LLM consumption."""
        if not data:
            return "No se encontraron obligaciones próximas a vencer."

        lines = [f"Deadlines próximos: {len(data)} obligaciones"]
        lines.append("")

        for obs in data:
            lines.append(f"=== {obs['codigo']} — {obs['nombre']} ===")
            lines.append(f"  Fuente: {obs['fuente']} | Organismo: {obs['organismo_emisor']}")
            if obs.get("frecuencia_presentacion"):
                lines.append(f"  Frecuencia: {obs['frecuencia_presentacion']}")
            if obs.get("ventana_presentacion"):
                lines.append(f"  Ventana: {obs['ventana_presentacion']}")
            if obs.get("plazo_dias"):
                lines.append(f"  Plazo: {obs['plazo_dias']} días")
            if obs.get("trigger_presentacion"):
                lines.append(f"  Trigger: {obs['trigger_presentacion']}")
            lines.append("")

        return "\n".join(lines)

    def _format_obligaciones_aplicables(self, data: dict) -> str:
        """Format applicable obligations for a regulated entity profile."""
        obligaciones = data.get("obligaciones", [])
        perfil = data.get("perfil", {})

        if not obligaciones:
            confidence = data.get("confidence") or {}
            aviso = confidence.get("aviso") or (
                "No se encontraron obligaciones aplicables verificadas para el perfil regulatorio indicado. "
                "No interpretar como inexistencia de obligaciones."
            )
            return (
                f"Perfil: {perfil.get('tipo_entidad', 'desconocido')} | "
                f"Estado: {data.get('status', 'evidence_limited')}\n"
                f"Verified: {data.get('verified', False)} | Review required: {confidence.get('review_required', True)}\n"
                f"{aviso}"
            )

        lines = [
            f"Perfil: {perfil.get('tipo_entidad', 'desconocido')} | Supervisor: {perfil.get('supervision_principal', 'N/A')}",
            f"Obligaciones aplicables: {len(obligaciones)}/{data.get('total', len(obligaciones))}",
            "",
        ]
        if data.get("has_more"):
            lines.append(
                f"[TRUNCATED] Hay mas obligaciones. Continuar con offset={data.get('next_offset')}."
            )
            lines.append("")

        for obs in obligaciones:
            lines.append(f"=== {obs['codigo']} — {obs['nombre']} ===")
            lines.append(f"  Fuente: {obs['fuente']} | Organismo: {obs['organismo_emisor']}")
            lines.append(f"  Tipo: {obs['tipo_obligacion']} | Sujeto: {obs['sujeto_obligado']}")
            lines.append(f"  Ámbito: {obs['ambito']} | Vigencia: {obs['estado_vigencia']}")
            if obs.get("frecuencia_presentacion"):
                lines.append(f"  Frecuencia: {obs['frecuencia_presentacion']}")
            if obs.get("ventana_presentacion"):
                lines.append(f"  Ventana: {obs['ventana_presentacion']}")
            lines.append("")

        return "\n".join(lines)

    def _format_obligacion_completa(self, data: dict) -> str:
        """Format complete obligation detail for LLM consumption."""
        lines = [f"Obligación: {data['codigo']} — {data['nombre']}"]
        lines.append("")
        lines.append(f"Fuente: {data['fuente']} | Organismo: {data['organismo_emisor']}")
        lines.append(f"Tipo: {data['tipo_obligacion']} | Sujeto: {data['sujeto_obligado']}")
        lines.append(f"Ámbito: {data['ambito']} | Vigencia: {data['estado_vigencia']}")
        lines.append("")

        lines.append("Datos operativos:")
        if data.get("plazo_dias"):
            lines.append(f"  Plazo: {data['plazo_dias']} días naturales")
        if data.get("frecuencia_presentacion"):
            lines.append(f"  Frecuencia: {data['frecuencia_presentacion']}")
        if data.get("ventana_presentacion"):
            lines.append(f"  Ventana: {data['ventana_presentacion']}")
        if data.get("trigger_presentacion"):
            lines.append(f"  Trigger: {data['trigger_presentacion']}")
        if data.get("canal_presentacion"):
            lines.append(f"  Canal: {data['canal_presentacion']}")
        if data.get("obligados_resumen"):
            lines.append(f"  Obligados: {data['obligados_resumen']}")
        if data.get("owner_rol_sugerido"):
            lines.append(f"  Owner sugerido: {data['owner_rol_sugerido']}")
        if data.get("criticidad"):
            lines.append(f"  Criticidad: {data['criticidad']}")
        if data.get("control_interno_sugerido"):
            lines.append(f"  Control interno: {data['control_interno_sugerido']}")
        if data.get("procedimiento_relacionado"):
            lines.append(f"  Procedimiento: {data['procedimiento_relacionado']}")
        lines.append("")

        evidencias = data.get("evidencia_requerida") or []
        if evidencias:
            lines.append("Evidencia requerida:")
            for item in evidencias:
                lines.append(f"  - {item}")
            lines.append("")

        lines.append("Sanciones:")
        if data.get("sancion_min") is not None or data.get("sancion_max") is not None:
            min_val = data["sancion_min"] if data.get("sancion_min") else "N/A"
            max_val = data["sancion_max"] if data.get("sancion_max") else "N/A"
            lines.append(f"  Rango: {min_val}€ - {max_val}€")
        if data.get("recargo_voluntario"):
            lines.append(f"  Recargo voluntario: {data['recargo_voluntario']}")
        if data.get("recargo_involuntario"):
            lines.append(f"  Recargo involuntario: {data['recargo_involuntario']}")
        if data.get("interes_demora"):
            lines.append(f"  Interés demora: {data['interes_demora']}")
        if data.get("prescripcion_anos"):
            lines.append(f"  Prescripción: {data['prescripcion_anos']} años")
        if data.get("deposito_previo"):
            lines.append(f"  Depósito previo: {data['deposito_previo']}")
        lines.append("")

        if data.get("documento_origen_ref"):
            lines.append(f"Documento origen: {data['documento_origen_tipo']} — {data['documento_origen_ref']}")
        if data.get("seccion_origen"):
            lines.append(f"  Sección: {data['seccion_origen']}")
        if data.get("nota"):
            lines.append(f"  Nota: {data['nota']}")
        lines.append("")

        if data.get("origen_metadato"):
            lines.append(f"Origen metadato: {data['origen_metadato']} | Estado: {data.get('estado_metadato', 'N/A')}")

        if data.get("documentos"):
            lines.append(f"Documentos relacionados: {len(data['documentos'])}")
            for doc in data["documentos"]:
                lines.append(f"  - {doc['referencia']} ({doc['tipo_documento']}) — {doc['tipo_relacion']}")

        return "\n".join(lines)

    def _entidad_to_sujeto(self, tipo_entidad: str) -> str:
        mapping = {
            "sociedad_valores": "contribuyente",
            "entidad_dinero_electronico": "empresa",
            "retenedor": "retenedor",
            "no_residente": "no_residente",
        }
        return mapping.get(tipo_entidad, "contribuyente")

    def _format_sfdr_products(self, data: dict) -> str:
        items = data.get("items", [])
        total = data.get("total", 0)
        lines = [f"Productos SFDR: {total} resultados"]
        for p in items:
            paci = "SI" if p.get("principal_adverse_impact") == "true" else "NO"
            lines.append(f"  [{p.get('id')}] {p.get('product_name')} | {p.get('product_type')} | {p.get('sustainability_strategy', 'N/A')} | PACI: {paci} | {p.get('status')}")
        return "\n".join(lines)

    def _format_sfdr_product_detail(self, data: dict) -> str:
        lines = [f"Producto SFDR: {data.get('product_name')}"]
        lines.append(f"  Tipo: {data.get('product_type')} | Estrategia: {data.get('sustainability_strategy', 'N/A')}")
        lines.append(f"  PACI: {data.get('principal_adverse_impact')} | Estado: {data.get('status')}")
        paci_agg = data.get("paci_aggregated")
        if paci_agg:
            lines.append(f"  PACI agregado: {json.dumps(paci_agg, ensure_ascii=False)}")
        dist = data.get("distribution_country")
        if dist:
            lines.append(f"  Distribuciòn: {', '.join(dist if isinstance(dist, list) else [])}")
        return "\n".join(lines)

    def _format_sfdr_pacai(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Indicadores PCAI SFDR: {len(items)} resultados"]
        for i in items:
            val = i.get("value")
            lines.append(f"  [{i.get('id')}] {i.get('indicator_code')} — {i.get('indicator_name')}: {val} {i.get('unit', '')} | ref: {i.get('reference_period', 'N/A')}")
        return "\n".join(lines)

    def _format_sfdr_entity_paci(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"PCAI Entidad SFDR: {len(items)} resultados"]
        for p in items:
            lines.append(f"  [{p.get('id')}] Entidad {p.get('entity_id')} | Ano: {p.get('reporting_year')} | {p.get('status')}")
        return "\n".join(lines)

    def _format_sfdr_pre_contractual(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Docs precontractuales SFDR: {len(items)} resultados"]
        for d in items:
            lines.append(f"  [{d.get('id')}] {d.get('document_type')} | Producto {d.get('product_id')} | Pub: {d.get('published_date', 'N/A')} | {d.get('status')}")
        return "\n".join(lines)

    def _format_sfdr_annual_reports(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Informes anuales SFDR: {len(items)} resultados"]
        for r in items:
            lines.append(f"  [{r.get('id')}] Entidad {r.get('entity_id')} | Ano: {r.get('reporting_year')} | {r.get('status')}")
        return "\n".join(lines)

    def _format_csrd_entity_reports(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Informes CSRD: {len(items)} resultados"]
        for r in items:
            lines.append(f"  [{r.get('id')}] Entidad {r.get('entity_id')} | Ano: {r.get('reporting_year')} | Aseguramiento: {r.get('assurance_status', 'N/A')} | {r.get('status')}")
        return "\n".join(lines)

    def _format_csrd_esg_data(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Puntos de datos ESG CSRD: {len(items)} resultados"]
        for d in items:
            val = d.get("value")
            lines.append(f"  [{d.get('id')}] {d.get('topic')} | {d.get('indicator_code', 'N/A')}: {val} {d.get('unit', '')} | scope: {d.get('scope', 'N/A')}")
        return "\n".join(lines)

    def _format_csrd_ess(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Estàndares ESRS CSRD: {len(items)} resultados"]
        for e in items:
            lines.append(f"  [{e.get('id')}] {e.get('standard_code')} — {e.get('topic', 'N/A')} | Aplica desde: {e.get('applicable_from_year', 'N/A')} | {e.get('description', '')[:100]}")
        return "\n".join(lines)

    def _format_csrd_double_materiality(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Evaluaciones doble materialidad CSRD: {len(items)} resultados"]
        for m in items:
            lines.append(f"  [{m.get('id')}] Entidad {m.get('entity_id')} | Fecha: {m.get('assessment_date', 'N/A')} | {m.get('status')}")
            impacts = m.get("key_impacts")
            if impacts:
                lines.append(f"    Impactos clave: {impacts[:200]}")
        return "\n".join(lines)

    def _format_aifmd_funds(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Fondos AIFMD: {len(items)} resultados"]
        for f in items:
            aum = f.get("total_aum_eur")
            aum_str = f"{aum:,.0f} EUR" if aum else "N/A"
            passport = "SI" if f.get("cross_border_passport") else "NO"
            lines.append(f"  [{f.get('id')}] {f.get('fund_name')} | {f.get('fund_type')} | AUM: {aum_str} | Passport: {passport} | {f.get('home_member_state', 'N/A')}")
        return "\n".join(lines)

    def _format_aifmd_reports(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Informes regulatorios AIFMD: {len(items)} resultados"]
        for r in items:
            lines.append(f"  [{r.get('id')}] Fondo {r.get('fund_id')} | {r.get('report_type')} | {r.get('reporting_period', 'N/A')} | {r.get('status')}")
        return "\n".join(lines)

    def _format_aifmd_liquidity(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Gestiòn liquidez AIFMD: {len(items)} resultados"]
        for item in items:
            susp = "SI" if item.get("redemption_suspended") else "NO"
            gate = "SI" if item.get("gating_applied") else "NO"
            swing = "SI" if item.get("swing_price_applied") else "NO"
            lines.append(f"  [{item.get('id')}] Fondo {item.get('fund_id')} | Suspensiòn: {susp} | Gate: {gate} | Swing: {swing} | Freq: {item.get('valuation_frequency', 'N/A')}")
        return "\n".join(lines)

    def _format_ucits_funds(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Fondos UCITS: {len(items)} resultados"]
        for f in items:
            aum = f.get("total_aum_eur")
            aum_str = f"{aum:,.0f} EUR" if aum else "N/A"
            passport = "SI" if f.get("cross_border_passport") else "NO"
            lines.append(f"  [{f.get('id')}] {f.get('fund_name')} | Gestor: {f.get('management_company', 'N/A')} | AUM: {aum_str} | Passport: {passport} | {f.get('risk_profile', 'N/A')}")
        return "\n".join(lines)

    def _format_ucits_reports(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Informes regulatorios UCITS: {len(items)} resultados"]
        for r in items:
            lines.append(f"  [{r.get('id')}] Fondo {r.get('fund_id')} | {r.get('report_type')} | {r.get('reporting_period', 'N/A')} | {r.get('status')}")
        return "\n".join(lines)

    def _format_crd_capital(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Posiciones capital CRD/CRR: {len(items)} resultados"]
        for p in items:
            lines.append(f"  [{p.get('id')}] Entidad {p.get('entity_id')} | Fecha: {p.get('reporting_date')} | CET1: {p.get('cet1_ratio')}% | Tier1: {p.get('tier1_ratio')}% | Total: {p.get('total_capital_ratio')}% | Leverage: {p.get('leverage_ratio')}%")
        return "\n".join(lines)

    def _format_crd_stress_tests(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Pruebas de estrès CRD: {len(items)} resultados"]
        for t in items:
            lines.append(f"  [{t.get('id')}] Entidad {t.get('entity_id')} | {t.get('scenario_name', 'N/A')} | Fecha: {t.get('test_date')} | CET1 impact: {t.get('cet1_impact_pct')}% | Autoridad: {t.get('competent_authority', 'N/A')}")
        return "\n".join(lines)

    def _format_brrd_bail_in(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Bail-in MREL BRRD: {len(items)} resultados"]
        for b in items:
            lines.append(f"  [{b.get('id')}] Entidad {b.get('entity_id')} | MREL target: {b.get('mrel_target_pct')}% | Compliance: {b.get('mrel_compliance_pct')}% | Internal MREL: {b.get('internal_mrel')}% | Resolution: {b.get('resolution_status', 'N/A')}")
        return "\n".join(lines)

    def _format_emir_trades(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Reportes operaciòn EMIR: {len(items)} resultados"]
        for t in items:
            clear = "SI" if t.get("clearing_obligation_applied") else "NO"
            lines.append(f"  [{t.get('id')}] Trade {t.get('trade_id')} | {t.get('asset_class')} | {t.get('instrument_class', 'N/A')} | Clearing: {clear} | Counterparty: {t.get('counterparty_type', 'N/A')} | Delay: {t.get('reporting_delay_days', 'N/A')}d")
        return "\n".join(lines)

    def _format_emir_clearing(self, data: dict) -> str:
        items = data.get("items", [])
        lines = [f"Miembros liquidaciòn EMIR: {len(items)} resultados"]
        for c in items:
            lines.append(f"  [{c.get('id')}] Entidad {c.get('entity_id')} | {c.get('emir_registration', 'N/A')} | {c.get('clearing_type')} | {c.get('status')}")
        return "\n".join(lines)

    def _format_compliance_resumen(self, data: list[dict]) -> str:
        if not data:
            return "No se encontraron casos de workflow con los filtros aplicados."

        lines = [f"Casos de workflow: {len(data)} resultados"]
        lines.append("")

        estados: dict[str, int] = {}
        for caso in data:
            estado = caso.get("estado", "desconocido")
            estados[estado] = estados.get(estado, 0) + 1
        lines.append(f"Por estado: {', '.join(f'{k}: {v}' for k, v in sorted(estados.items()))}")
        lines.append("")

        for caso in data:
            lines.append(f"=== Caso: {caso.get('workflow_id', 'N/A')} ===")
            lines.append(f"  Cambio: {caso.get('cambio_codigo', 'N/A')}")
            lines.append(f"  Obligacion: {caso.get('obligacion_codigo', 'N/A')}")
            lines.append(f"  Estado: {caso.get('estado', 'N/A')}")
            lines.append(f"  Owner: {caso.get('owner_rol', 'N/A')}")
            if caso.get("fecha_objetivo"):
                lines.append(f"  Fecha objetivo: {caso['fecha_objetivo']}")
            if caso.get("notas"):
                lines.append(f"  Notas: {caso['notas'][:200]}")
            lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    server = MCPStdioServer()
    anyio.run(server.run)
