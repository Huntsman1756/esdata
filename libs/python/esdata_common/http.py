"""Cliente HTTP reutilizable con retries para API y workers."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def create_client(
    base_url: str = "",
    timeout: float = 30.0,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """Crear cliente HTTP con retries automaticos.

    Args:
        base_url: URL base para todas las peticiones.
        timeout: Timeout en segundos por peticion.
        max_retries: Numero maximo de reintentos.
        backoff_factor: Factor de backoff exponencial entre reintentos.
        **kwargs: Argumentos adicionales para httpx.AsyncClient.
    """
    transport = httpx.AsyncHTTPTransport(retries=max_retries)
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
        transport=transport,
        **kwargs,
    )


async def fetch_with_retry(
    url: str,
    method: str = "GET",
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    timeout: float = 30.0,
    **kwargs: Any,
) -> httpx.Response:
    """Hacer peticion HTTP con reintentos y backoff exponencial.

    Args:
        url: URL completa de la peticion.
        method: Metodo HTTP (GET, POST, etc.).
        max_retries: Numero maximo de reintentos.
        backoff_factor: Factor de backoff exponencial.
        timeout: Timeout en segundos.
        **kwargs: Argumentos adicionales para httpx.request.

    Returns:
        Response del httpx.

    Raises:
        httpx.HTTPError: Si se agotan los reintentos.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await httpx.AsyncClient(timeout=timeout).request(
                method, url, **kwargs
            )
            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            last_exception = e
            logger.warning(
                "Intento %d/%d fallido para %s %s: %s",
                attempt + 1,
                max_retries + 1,
                method,
                url,
                str(e),
            )
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                logger.info("Reintento en %.1f segundos...", delay)
                await httpx.AsyncClient().aclose()  # Espera minimal
                import asyncio
                await asyncio.sleep(delay)

    raise last_exception or httpx.HTTPError("Sin respuestas exitosas")
