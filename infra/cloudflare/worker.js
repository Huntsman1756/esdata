// Cloudflare Worker: gateway para api.esdata.org
// Ajuste 4: caché solo en paths realmente deterministas
// Ajuste 5: rotación de secretos MCP (activo + anterior con gracia de 24h)

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // --- Rate limiting por IP ---
    // Aplica a búsquedas (aunque no se cacheen, se protegen)
    if (path.startsWith("/v1/legislacion/buscar") ||
        path.startsWith("/v1/doctrina/buscar")) {
      const ip = request.headers.get("CF-Connecting-IP");
      const { success } = await env.RATE_LIMITER.limit({ key: `rate:${ip}` });
      if (!success) {
        return new Response(
          JSON.stringify({ error: "Too many requests", retry_after: 60 }),
          { status: 429, headers: { "Content-Type": "application/json" } }
        );
      }
    }

    // --- Protección /mcp con rotación de secretos ---
    // Acepta el secreto activo y el anterior durante el periodo de gracia.
    // Para rotar: actualiza MCP_SECRET_ACTIVE con el nuevo, MCP_SECRET_PREVIOUS
    // con el anterior. Tras 24h, vacía MCP_SECRET_PREVIOUS.
    if (path.startsWith("/mcp")) {
      const authHeader = request.headers.get("Authorization") || "";
      const token = authHeader.replace("Bearer ", "").trim();
      const validTokens = [env.MCP_SECRET_ACTIVE, env.MCP_SECRET_PREVIOUS]
        .filter(Boolean); // ignora vacíos

      if (!validTokens.includes(token)) {
        return new Response(
          JSON.stringify({ error: "Unauthorized" }),
          { status: 401, headers: { "Content-Type": "application/json" } }
        );
      }
    }

    // --- Caché solo en GETs deterministas ---
    // SÍ cachea: /v1/legislacion/{codigo}/articulos/{numero}
    //             /v1/legislacion/{codigo}/articulos/{numero}/historial
    //             /v1/materias y /v1/materias/{slug}
    //             /v1/legislacion (lista de normas)
    //
    // NO cachea: /v1/legislacion/buscar (vigente_en, filtros, confianza dinámica)
    //             /v1/doctrina/buscar
    //             /status, /health (siempre frescos)
    //             /mcp (ya manejado arriba)

    const CACHEABLE = [
      /^\/v1\/legislacion\/[^/]+\/articulos\/[^/]+(\/historial)?$/,
      /^\/v1\/materias(\/[^/]+)?$/,
      /^\/v1\/legislacion$/,
      /^\/v1\/legislacion\/[^/]+$/,
    ];

    const isCacheable = request.method === "GET" &&
      CACHEABLE.some(re => re.test(path)) &&
      !url.searchParams.has("vigente_en"); // con fecha explícita, no cachear

    if (isCacheable) {
      const cache = caches.default;
      let response = await cache.match(request);

      if (!response) {
        response = await fetch(request);
        if (response.status === 200) {
          const headers = new Headers(response.headers);
          headers.set("Cache-Control", "public, max-age=3600");
          headers.set("X-Cache", "MISS");
          response = new Response(response.body, { ...response, headers });
          ctx.waitUntil(cache.put(request, response.clone()));
        }
      } else {
        const headers = new Headers(response.headers);
        headers.set("X-Cache", "HIT");
        response = new Response(response.body, { ...response, headers });
      }
      return response;
    }

    return fetch(request);
  }
};
