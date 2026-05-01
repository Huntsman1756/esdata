# Integraciones

## Estado

Matriz activa de integraciones de `esdata` con clientes LLM y herramientas externas.

| Integracion | Transporte | Auth | Estado | Doc |
|---|---|---|---|---|
| ChatGPT Custom GPT / Business Actions | OpenAPI HTTPS | API key dedicada | `[IMPLEMENTED]` | `chatgpt-business-actions.md` |
| OpenCode | MCP HTTP o stdio | `MCP_API_KEY` | `[IMPLEMENTED]` | `opencode-local-and-vps.md` |
| Open WebUI | OpenAPI HTTPS | `X-API-Key` | `[PARTIAL]` | `open-webui.md` |
| AnythingLLM | OpenAPI HTTPS | `X-API-Key` | `[PARTIAL]` | `anythingllm.md` |
| LangChain | REST/OpenAPI | `X-API-Key` | `[PARTIAL]` | `langchain.md` |

## Regla

- `MCP` es la superficie principal para clientes personales o locales.
- `OpenAPI + Actions` es la superficie principal para clientes cloud como ChatGPT.
- No documentar una integracion como `[IMPLEMENTED]` si el repo no contiene contrato, auth y pasos minimos verificables.
