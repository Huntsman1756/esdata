"""MCP stdio server for esdata — exposes consulta_fiscal as a tool for LLM clients."""

import asyncio
import json
import sys
from typing import Any

# FastAPI app must be imported before any DB access
from main import app
from routers.consulta import consulta_fiscal
from fastapi.testclient import TestClient
from mcp_catalog import get_stdio_tool_definitions

client = TestClient(app)


class MCPStdioServer:
    """Minimal MCP stdio server using Streamable HTTP transport concept."""

    def __init__(self):
        self._message_id = 0

    def _next_id(self) -> int:
        self._message_id += 1
        return self._message_id

    def _send(self, data: dict[str, Any]):
        payload = json.dumps(data, ensure_ascii=False)
        sys.stdout.write(f"Content-Length: {len(payload.encode('utf-8'))}\r\n\r\n{payload}")
        sys.stdout.flush()

    def run(self):
        # MCP stdio uses JSON-RPC over stdin/stdout with content-length headers
        while True:
            line = sys.stdin.readline()
            if not line:
                break

            # Parse content-length header
            if "Content-Length:" in line:
                content_length = int(line.split(":")[1].strip())
                raw = sys.stdin.read(content_length)
                message = json.loads(raw)
            else:
                message = json.loads(line.strip())

            msg_type = message.get("method", "")
            msg_id = message.get("id")

            if msg_type == "initialize":
                self._handle_initialize(message)
            elif msg_type == "notifications/initialized":
                pass  # ignore
            elif msg_type == "tools/list":
                self._handle_tools_list(msg_id)
            elif msg_type == "tools/call":
                self._handle_tools_call(message, msg_id)
            elif msg_type == "ping":
                self._send_jsonrpc(msg_id, None)
            else:
                self._send_error(msg_id, -32601, f"Unknown method: {msg_type}")

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

    def _handle_tools_call(self, message: dict, msg_id: Any):
        params = message.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "consulta_fiscal":
            try:
                from fastapi import Query
                from contextlib import contextmanager

                q = arguments.get("q", "")
                sujeto = arguments.get("sujeto", "")
                pais = arguments.get("pais", "")
                tipo_operacion = arguments.get("tipo_operacion", "")

                # Call the actual endpoint
                response = client.get(
                    "/v1/consulta",
                    params={"q": q, "sujeto": sujeto, "pais": pais, "tipo_operacion": tipo_operacion},
                )

                if response.status_code == 200:
                    data = response.json()
                    # Format as readable text for the LLM
                    output = self._format_response(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing consulta: {str(e)}")
        elif tool_name == "listar_obligaciones_operativas":
            try:
                ambito = arguments.get("ambito")
                frecuencia = arguments.get("frecuencia")
                con_sancion = arguments.get("con_sancion", True)
                limite = arguments.get("limite", 50)

                response = client.get(
                    "/v1/obligaciones/operativas",
                    params={"ambito": ambito, "frecuencia": frecuencia, "con_sancion": con_sancion, "limite": limite},
                )

                if response.status_code == 200:
                    data = response.json()
                    output = self._format_obligaciones_operativas(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_obligaciones_operativas: {str(e)}")
        elif tool_name == "listar_deadlines":
            try:
                dias_proximo = arguments.get("dias_proximo", 30)
                frecuencia = arguments.get("frecuencia")

                response = client.get(
                    "/v1/obligaciones/deadlines",
                    params={"dias_proximo": dias_proximo, "frecuencia": frecuencia},
                )

                if response.status_code == 200:
                    data = response.json()
                    output = self._format_deadlines(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_deadlines: {str(e)}")

        elif tool_name == "listar_obligaciones_aplicables":
            try:
                response = client.get(
                    "/v1/obligaciones/aplicables",
                    params={
                        "tipo_entidad": arguments.get("tipo_entidad", "sociedad_valores"),
                        "reporting_reservado": arguments.get("reporting_reservado", True),
                        "aml_cft_reforzado": arguments.get("aml_cft_reforzado", True),
                        "cross_border_ue": arguments.get("cross_border_ue", False),
                    },
                )
                response.raise_for_status()
                data = response.json()
                output = self._format_obligaciones_aplicables(data)
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": output}],
                    "structuredContent": data,
                })
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing listar_obligaciones_aplicables: {str(e)}")
        elif tool_name == "get_obligacion_completa":
            try:
                codigo = arguments.get("codigo", "")

                response = client.get(f"/v1/obligaciones/{codigo}")

                if response.status_code == 200:
                    data = response.json()
                    output = self._format_obligacion_completa(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing get_obligacion_completa: {str(e)}")
        elif tool_name == "agente_consulta":
            try:
                q = arguments.get("q", "")
                sujeto_arg = arguments.get("sujeto", "")
                tipo_entidad = arguments.get("tipo_entidad", "sociedad_valores")

                sujeto = sujeto_arg or self._entidad_to_sujeto(tipo_entidad)

                response = client.get(
                    "/v1/consulta",
                    params={"q": q, "sujeto": sujeto},
                )

                if response.status_code == 200:
                    data = response.json()
                    output = self._format_response(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing agente_consulta: {str(e)}")
        elif tool_name == "agente_monitoreo_status":
            try:
                from agent_monitor import get_monitor_status

                status = get_monitor_status()
                self._send_jsonrpc(msg_id, {
                    "content": [{"type": "text", "text": json.dumps(status, ensure_ascii=False, indent=2)}],
                    "structuredContent": status,
                })
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error getting monitor status: {str(e)}")
        elif tool_name == "agente_compliance_resumen":
            try:
                estado = arguments.get("estado")
                limite = arguments.get("limite", 20)

                params = {}
                if estado:
                    params["estado"] = estado
                params["limite"] = limite

                response = client.get(
                    "/v1/compliance/workflow",
                    params=params,
                )

                if response.status_code == 200:
                    data = response.json()
                    output = self._format_compliance_resumen(data)
                    self._send_jsonrpc(msg_id, {
                        "content": [{"type": "text", "text": output}],
                        "structuredContent": data,
                    })
                else:
                    self._send_error(msg_id, -32603, f"API error: {response.status_code}")
            except Exception as e:
                self._send_error(msg_id, -32603, f"Error executing agente_compliance_resumen: {str(e)}")
        else:
            self._send_error(msg_id, -32601, f"Unknown tool: {tool_name}")

    def _format_response(self, data: dict) -> str:
        """Format API response as readable text for LLM consumption."""
        lines = []
        lines.append(f"Consulta: {data['consulta']}")
        lines.append(f"Total resultados: {data['total_resultados']}")

        relevancia = data.get("relevancia")
        if relevancia:
            lines.append(f"Relevancia: {relevancia.get('nivel', 'N/A')} (score: {relevancia.get('score', 0):.2f})")
            terminos = relevancia.get('terminos_encontrados', [])
            if terminos:
                lines.append(f"  Terminos encontrados: {', '.join(terminos)}")

        confianza = data.get("confianza")
        if confianza:
            lines.append(f"Confianza: {confianza.get('nivel_texto', 'N/A')} (nivel: {confianza.get('nivel', 0)})")
            aviso = confianza.get('aviso')
            if aviso:
                lines.append(f"  Aviso: {aviso}")
            modelos_cubiertos = confianza.get('modelos_cubiertos', [])
            if modelos_cubiertos:
                lines.append(f"  Modelos identificados: {', '.join(modelos_cubiertos)}")
            clasificados = confianza.get('resultados_clasificados', {})
            if clasificados:
                lines.append(f"  Resultados por tipo: {', '.join(f'{k}: {v}' for k, v in clasificados.items())}")

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
                lines.append(f"    {inst['contenido'][:500]}")
            lines.append("")

        for resultado in data.get("resultados", []):
            relevancia_r = resultado.get('_relevancia', {})
            relevancia_str = ""
            if relevancia_r:
                relevancia_str = f" [relevancia: {relevancia_r.get('nivel', 'N/A')} (score: {relevancia_r.get('score', 0):.2f})]"

            if resultado["tipo"] == "normativa":
                lines.append(f"  Normativa: {resultado['norma']} art. {resultado['articulo']}{relevancia_str}")
                lines.append(f"    {resultado.get('texto', '')[:300]}")
                evidencia = resultado.get('evidencia')
                if evidencia and evidencia.get('motivo_ranking'):
                    lines.append(f"    Motivo: {evidencia['motivo_ranking']}")
            elif resultado["tipo"] == "doctrina":
                lines.append(f"  Doctrina: {resultado.get('referencia', '')} — {resultado.get('titulo', '')}{relevancia_str}")
                lines.append(f"    {resultado.get('fragmento', '')[:300]}")
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

            if obs.get('frecuencia_presentacion'):
                lines.append(f"  Frecuencia: {obs['frecuencia_presentacion']}")
            if obs.get('plazo_dias'):
                lines.append(f"  Plazo: {obs['plazo_dias']} días")
            if obs.get('ventana_presentacion'):
                lines.append(f"  Ventana: {obs['ventana_presentacion']}")
            if obs.get('trigger_presentacion'):
                lines.append(f"  Trigger: {obs['trigger_presentacion']}")
            if obs.get('canal_presentacion'):
                lines.append(f"  Canal: {obs['canal_presentacion']}")
            if obs.get('sancion_min') is not None or obs.get('sancion_max') is not None:
                min_val = obs['sancion_min'] if obs.get('sancion_min') else "N/A"
                max_val = obs['sancion_max'] if obs.get('sancion_max') else "N/A"
                lines.append(f"  Sanción: {min_val}€ - {max_val}€")
            if obs.get('recargo_voluntario'):
                lines.append(f"  Recargo voluntario: {obs['recargo_voluntario']}")
            if obs.get('recargo_involuntario'):
                lines.append(f"  Recargo involuntario: {obs['recargo_involuntario']}")
            if obs.get('interes_demora'):
                lines.append(f"  Interés demora: {obs['interes_demora']}")
            if obs.get('prescripcion_anos'):
                lines.append(f"  Prescripción: {obs['prescripcion_anos']} años")
            if obs.get('deposito_previo'):
                lines.append(f"  Depósito previo: {obs['deposito_previo']}")
            if obs.get('estado_metadato') == 'borrador':
                lines.append(f"  ⚠️ Estado: borrador (no curado)")
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
            if obs.get('frecuencia_presentacion'):
                lines.append(f"  Frecuencia: {obs['frecuencia_presentacion']}")
            if obs.get('ventana_presentacion'):
                lines.append(f"  Ventana: {obs['ventana_presentacion']}")
            if obs.get('plazo_dias'):
                lines.append(f"  Plazo: {obs['plazo_dias']} días")
            if obs.get('trigger_presentacion'):
                lines.append(f"  Trigger: {obs['trigger_presentacion']}")
            lines.append("")

        return "\n".join(lines)

    def _format_obligaciones_aplicables(self, data: dict) -> str:
        """Format applicable obligations for a regulated entity profile."""
        obligaciones = data.get("obligaciones", [])
        perfil = data.get("perfil", {})

        if not obligaciones:
            return "No se encontraron obligaciones aplicables para el perfil regulatorio indicado."

        lines = [
            f"Perfil: {perfil.get('tipo_entidad', 'desconocido')} | Supervisor: {perfil.get('supervision_principal', 'N/A')}",
            f"Obligaciones aplicables: {len(obligaciones)}",
            "",
        ]

        for obs in obligaciones:
            lines.append(f"=== {obs['codigo']} — {obs['nombre']} ===")
            lines.append(f"  Fuente: {obs['fuente']} | Organismo: {obs['organismo_emisor']}")
            lines.append(f"  Tipo: {obs['tipo_obligacion']} | Sujeto: {obs['sujeto_obligado']}")
            lines.append(f"  Ámbito: {obs['ambito']} | Vigencia: {obs['estado_vigencia']}")
            if obs.get('frecuencia_presentacion'):
                lines.append(f"  Frecuencia: {obs['frecuencia_presentacion']}")
            if obs.get('ventana_presentacion'):
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
        if data.get('plazo_dias'):
            lines.append(f"  Plazo: {data['plazo_dias']} días naturales")
        if data.get('frecuencia_presentacion'):
            lines.append(f"  Frecuencia: {data['frecuencia_presentacion']}")
        if data.get('ventana_presentacion'):
            lines.append(f"  Ventana: {data['ventana_presentacion']}")
        if data.get('trigger_presentacion'):
            lines.append(f"  Trigger: {data['trigger_presentacion']}")
        if data.get('canal_presentacion'):
            lines.append(f"  Canal: {data['canal_presentacion']}")
        if data.get('obligados_resumen'):
            lines.append(f"  Obligados: {data['obligados_resumen']}")
        if data.get('owner_rol_sugerido'):
            lines.append(f"  Owner sugerido: {data['owner_rol_sugerido']}")
        if data.get('criticidad'):
            lines.append(f"  Criticidad: {data['criticidad']}")
        if data.get('control_interno_sugerido'):
            lines.append(f"  Control interno: {data['control_interno_sugerido']}")
        if data.get('procedimiento_relacionado'):
            lines.append(f"  Procedimiento: {data['procedimiento_relacionado']}")
        lines.append("")

        evidencias = data.get('evidencia_requerida') or []
        if evidencias:
            lines.append("Evidencia requerida:")
            for item in evidencias:
                lines.append(f"  - {item}")
            lines.append("")

        lines.append("Sanciones:")
        if data.get('sancion_min') is not None or data.get('sancion_max') is not None:
            min_val = data['sancion_min'] if data.get('sancion_min') else "N/A"
            max_val = data['sancion_max'] if data.get('sancion_max') else "N/A"
            lines.append(f"  Rango: {min_val}€ - {max_val}€")
        if data.get('recargo_voluntario'):
            lines.append(f"  Recargo voluntario: {data['recargo_voluntario']}")
        if data.get('recargo_involuntario'):
            lines.append(f"  Recargo involuntario: {data['recargo_involuntario']}")
        if data.get('interes_demora'):
            lines.append(f"  Interés demora: {data['interes_demora']}")
        if data.get('prescripcion_anos'):
            lines.append(f"  Prescripción: {data['prescripcion_anos']} años")
        if data.get('deposito_previo'):
            lines.append(f"  Depósito previo: {data['deposito_previo']}")
        lines.append("")

        if data.get('documento_origen_ref'):
            lines.append(f"Documento origen: {data['documento_origen_tipo']} — {data['documento_origen_ref']}")
        if data.get('seccion_origen'):
            lines.append(f"  Sección: {data['seccion_origen']}")
        if data.get('nota'):
            lines.append(f"  Nota: {data['nota']}")
        lines.append("")

        if data.get('origen_metadato'):
            lines.append(f"Origen metadato: {data['origen_metadato']} | Estado: {data.get('estado_metadato', 'N/A')}")

        if data.get('documentos'):
            lines.append(f"Documentos relacionados: {len(data['documentos'])}")
            for doc in data['documentos']:
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
            if caso.get('fecha_objetivo'):
                lines.append(f"  Fecha objetivo: {caso['fecha_objetivo']}")
            if caso.get('notas'):
                lines.append(f"  Notas: {caso['notas'][:200]}")
            lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    server = MCPStdioServer()
    server.run()
