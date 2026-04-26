const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function ejecutarAnalisis(body = {}) {
  const res = await fetch(`${BASE}/analisis-rendimiento/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function listarSoluciones(params?: {
  periodo_codigo?: string;
  asignatura_codigo?: string;
}) {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  const res = await fetch(`${BASE}/listar-soluciones/${qs ? `?${qs}` : ""}`, {
    cache: "no-store",
  });
  return res.json();
}

export async function exportarDoc(id: number, tipoDoc: "word" | "pdf") {
  const res = await fetch(`${BASE}/exportar-doc/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, tipoDoc }),
  });
  if (!res.ok) throw new Error("Error al exportar");
  return res.blob();
}

// Tipo que puede retornar el generador:
// - string con texto parcial del streaming
// - objeto { error, tipo } si el backend detectó un error clasificado
export type ChatChunk = string | { error: string; tipo: string };

export async function* chatAgente(mensaje: string): AsyncGenerator<ChatChunk> {
  const res = await fetch(`${BASE}/chat-agente/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensaje }),
  });

  if (!res.ok || !res.body) throw new Error("Error al conectar con el agente");

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer    = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw || raw === "[DONE]") continue;
      try {
        const chunk = JSON.parse(raw);
        // Error clasificado desde el backend
        if (chunk.error && chunk.tipo) {
          yield { error: chunk.error, tipo: chunk.tipo };
          return;
        }
        // Texto normal
        if (chunk.text) yield chunk.text as string;
      } catch {}
    }
  }
}