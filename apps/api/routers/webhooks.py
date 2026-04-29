"""Generic webhook router with HMAC-SHA256 signature verification + idempotency.

Regla 5 de AGENTS.md: "Verificacion criptografica de firma + idempotencia por event.id"

Usage:
    from routers.webhooks import webhook_router, WebhookPayload, webhook_secret

    # Register your handler:
    @webhook_router.on_post("/stripe")
    async def handle_stripe(payload: WebhookPayload, db: Session = Depends(get_db)):
        # payload is already verified and idempotent-checked
        ...

    # Or use the decorator on existing endpoints:
    @app.post("/webhooks/github")
    @verify_webhook_endpoint("x-hub-signature-256")
    async def handle_github(request: Request, payload: dict = Body(...)):
        ...
"""

import logging
from collections.abc import Callable
from typing import Any

from db import get_db
from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from services.webhook_verification import (
    WebhookEvent,
    check_idempotency,
    record_webhook_event,
    verify_webhook_signature,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Router generico reutilizable por proveedor de webhooks
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookPayload(BaseModel):
    """Esquema basico para eventos webhook con idempotencia."""

    event_id: str = Field(..., description="Identificador unico del evento para idempotencia")
    event_type: str = Field(..., description="Tipo de evento (ej: payment.completed)")
    payload: dict = Field(..., description="Datos del evento")
    timestamp: str | None = Field(None, description="ISO 8601 timestamp del evento")


def verify_webhook_endpoint(
    signature_header: str = "x-webhook-signature",
) -> Callable:
    """Decorador para verificar firma HMAC en endpoints de webhook.

    Usage:
        @app.post("/webhooks/provider")
        @verify_webhook_endpoint("x-provider-signature")
        async def handle_webhook(request: Request):
            payload = await request.body()
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            body = await request.body()
            verify_webhook_signature(request, body, signature_header)
            kwargs["request"] = request
            kwargs["_raw_body"] = body
            return await func(*args, **kwargs)
        return wrapper
    return decorator


@webhook_router.post(
    "/generic",
    status_code=status.HTTP_200_OK,
    summary="Webhook generico con verificacion + idempotencia",
    description=(
        "Endpoint generico que verifica firma HMAC-SHA256 y rechaza eventos duplicados "
        "por event_id."
    ),
)
async def handle_generic_webhook(
    request: Request,
    payload: WebhookPayload = Body(...),
    db: Session = Depends(get_db),
) -> dict:
    """Endpoint generico de webhook con:
    1. Verificacion de firma HMAC-SHA256
    2. Idempotencia por event_id
    3. Registro de evento procesado
    """
    # 1. Verificar firma
    body = await request.body()
    verify_webhook_signature(request, body)

    # 2. Verificar idempotencia
    is_duplicate = await check_idempotency(db, payload.event_id)
    if is_duplicate:
        logger.info("Duplicate webhook event: event_id=%s", payload.event_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "duplicate", "event_id": payload.event_id},
        )

    # 3. Registrar evento para idempotencia
    webhook_event = WebhookEvent(
        event_id=payload.event_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    await record_webhook_event(db, webhook_event)

    # 4. Procesar evento (aqui va la logica de negocio del webhook)
    logger.info(
        "Processing webhook: event_id=%s type=%s",
        payload.event_id,
        payload.event_type,
    )

    # TODO: Envelope the actual business logic here
    # e.g., update database, trigger notifications, etc.

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "processed", "event_id": payload.event_id},
    )


@webhook_router.post(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check para webhook endpoints",
)
async def webhook_health():
    """Verifica que el servicio de webhooks esta operativo."""
    return {"status": "ok", "service": "webhook-verification"}
