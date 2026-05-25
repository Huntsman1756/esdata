"use client";

import { useState } from "react";

export default function ConsultaClient() {
  const [query, setQuery] = useState("");
  const [sujeto, setSujeto] = useState("");
  const [pais, setPais] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function consultar() {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const params = new URLSearchParams({ q: query.trim() });
      if (sujeto.trim()) params.set("sujeto", sujeto.trim());
      if (pais.trim()) params.set("pais", pais.trim());
      const res = await fetch(`/api/consulta?${params.toString()}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Error consultando API");
    } finally {
      setLoading(false);
    }
  }

  function renderModelo(m: any) {
    return (
      <div key={m.codigo} style={{ border: "1px solid #ddd", borderRadius: 6, padding: 16, marginBottom: 12, background: "#fafafa" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <div>
            <span style={{ fontSize: 18, fontWeight: 700 }}>Modelo {m.codigo}</span>
            <span style={{ marginLeft: 8, fontSize: 13, color: "#666" }}>— {m.nombre}</span>
          </div>
          <span style={{ fontSize: 11, background: "#e0e0e0", padding: "2px 8px", borderRadius: 3 }}>
            {m.periodo || "N/A"}
          </span>
        </div>

        {m.categoria_obligado && (
          <div style={{ fontSize: 13, marginBottom: 4 }}>
            <strong>Categoría:</strong> {m.categoria_obligado}
          </div>
        )}
        {m.obligados_resumen && (
          <div style={{ fontSize: 13, marginBottom: 4 }}>
            <strong>Quién debe:</strong> {m.obligados_resumen}
          </div>
        )}
        {m.frecuencia && (
          <div style={{ fontSize: 13, marginBottom: 4 }}>
            <strong>Frecuencia:</strong> {m.frecuencia}
          </div>
        )}
        {m.ventana && (
          <div style={{ fontSize: 13, marginBottom: 4 }}>
            <strong>Plazo:</strong> {m.ventana}
          </div>
        )}
        {m.canal && (
          <div style={{ fontSize: 13, marginBottom: 4 }}>
            <strong>Canal:</strong> {m.canal}
          </div>
        )}

        {m.url_info && (
          <div style={{ fontSize: 13, marginBottom: 8 }}>
            <a href={m.url_info} target="_blank" rel="noopener" style={{ color: "#0066cc", textDecoration: "underline" }}>
              Info oficial AEAT →
            </a>
          </div>
        )}

        {m.campana && (
          <div style={{ fontSize: 13, marginBottom: 8 }}>
            <strong>Campana no verificada:</strong> dato interno {m.campana} {m.version_form && `| Versión: ${m.version_form}`}
          </div>
        )}

        {m.instrucciones && m.instrucciones.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {m.instrucciones.map((inst: any, j: number) => (
              <details key={j} style={{ border: "1px solid #e0e0e0", borderRadius: 4, marginBottom: 6, background: "#fff" }}>
                <summary style={{ padding: "6px 12px", cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
                  {inst.seccion ? `${inst.seccion.replace("-", " ").toUpperCase()}: ` : ""}{inst.titulo}
                </summary>
                <div style={{ padding: "8px 12px", fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                  {inst.contenido}
                </div>
              </details>
            ))}
          </div>
        )}
      </div>
    );
  }

  function renderResultado(r: any, i: number) {
    return (
      <div key={i} style={{ border: "1px solid #ddd", borderRadius: 6, padding: 12, marginBottom: 8, background: "#fafafa" }}>
        <span style={{
          fontSize: 10,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: 1,
          background: r.tipo === "modelo" ? "#1a1a1a" : r.tipo === "obligacion" ? "#0066cc" : r.tipo === "normativa" ? "#008844" : "#884400",
          color: "#fff",
          padding: "2px 8px",
          borderRadius: 3,
          marginRight: 8,
        }}>
          {r.tipo}
        </span>
        {r.codigo && <span style={{ fontWeight: 700 }}>Modelo {r.codigo}</span>}
        {r.nombre && <span style={{ marginLeft: 6 }}>— {r.nombre}</span>}
        {r.articulo && <span style={{ marginLeft: 6, color: "#666" }}>Art. {r.articulo} ({r.norma})</span>}
        {r.texto && (
          <div style={{ marginTop: 6, fontSize: 13, color: "#444", whiteSpace: "pre-wrap" }}>
            {r.texto}
          </div>
        )}
        {r.fragmento && (
          <div style={{ marginTop: 6, fontSize: 13, color: "#444", fontStyle: "italic" }}>
            {r.fragmento}
          </div>
        )}
        {r.fecha && <div style={{ marginTop: 4, fontSize: 12, color: "#888" }}>Fecha: {r.fecha}</div>}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
        <span style={{ fontSize: 20, fontWeight: 700 }}>esdata</span>
        <span style={{ fontSize: 12, color: "#888", background: "#f0f0f0", padding: "2px 8px", borderRadius: 4 }}>MCP Fiscal</span>
      </div>

      <div style={{ marginBottom: 16 }}>
        <textarea
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Pregunta fiscal: ej. 'cliente no residente en España con facturas intracomunitarias', 'irpf dividendos ue', 'iva entregas intracomunitarias'..."
          rows={3}
          style={{
            width: "100%",
            padding: 12,
            fontSize: 15,
            border: "1px solid #ccc",
            borderRadius: 6,
            resize: "vertical",
            fontFamily: "inherit",
            boxSizing: "border-box",
          }}
        />
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          placeholder="Sujeto (ej: no_residente, contribuyente)"
          value={sujeto}
          onChange={e => setSujeto(e.target.value)}
          style={{ flex: 1, minWidth: 180, padding: 8, fontSize: 13, border: "1px solid #ccc", borderRadius: 4 }}
        />
        <input
          placeholder="País/Ámbito (ej: ue, intracomunitario)"
          value={pais}
          onChange={e => setPais(e.target.value)}
          style={{ flex: 1, minWidth: 180, padding: 8, fontSize: 13, border: "1px solid #ccc", borderRadius: 4 }}
        />
        <button
          onClick={consultar}
          disabled={loading || !query.trim()}
          style={{
            padding: "8px 24px",
            fontSize: 14,
            fontWeight: 600,
            background: query.trim() ? "#1a1a1a" : "#ccc",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: query.trim() ? "pointer" : "default",
          }}
        >
          {loading ? "Consultando..." : "Consultar"}
        </button>
      </div>

      {error && (
        <div style={{ background: "#fee", border: "1px solid #fcc", borderRadius: 6, padding: 12, marginBottom: 16, color: "#900" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div>
          <div style={{ fontSize: 13, color: "#666", marginBottom: 16 }}>
            Consulta: <strong>"{result.consulta}"</strong> — {result.total_resultados} resultados
          </div>

          {result.modelos && result.modelos.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8, borderBottom: "2px solid #1a1a1a", paddingBottom: 4 }}>
                Modelos AEAT a presentar
              </h3>
              {result.modelos.map(renderModelo)}
            </div>
          )}

          {result.resultados && result.resultados.length > 0 && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8, borderBottom: "2px solid #1a1a1a", paddingBottom: 4 }}>
                Resultados complementarios
              </h3>
              {result.resultados.map(renderResultado)}
            </div>
          )}

          {!result.modelos || (result.modelos.length === 0 && result.resultados.length === 0) ? (
            <div style={{ padding: 24, textAlign: "center", color: "#888" }}>
              No se encontraron resultados para "{result.consulta}".
              <br />
              <span style={{ fontSize: 13 }}>Prueba con otros términos: facta, irnr, intracomunitario, retenciones, etc.</span>
            </div>
          ) : null}
        </div>
      )}

      {!result && !loading && (
        <div style={{ marginTop: 24 }}>
          <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, color: "#888", marginBottom: 8 }}>
            Preguntas de ejemplo
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {[
              "cliente no residente con facturas intracomunitarias",
              "irpf dividendos ue",
              "iva entregas intracomunitarias",
              "retenciones dividendos no residente",
              "obligaciones modelo 349",
              "irnr facta plazo presentación",
              "operaciones intracomunitarias empresas",
            ].map((ex, i) => (
              <button
                key={i}
                onClick={() => setQuery(ex)}
                style={{
                  padding: "6px 12px",
                  fontSize: 12,
                  border: "1px solid #ccc",
                  borderRadius: 4,
                  background: "#fff",
                  cursor: "pointer",
                }}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
