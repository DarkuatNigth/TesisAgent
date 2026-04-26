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