"use client";
import { useState } from "react";
import { FileText, FileDown, Loader2, AlertTriangle, CheckCircle } from "lucide-react";
import { exportarDoc } from "@/lib/api";
import type { Solucion } from "@/types";

const RIESGO_STYLE: Record<string, string> = {
  bajo:     "bg-green-50  text-green-700  border-green-200",
  medio:    "bg-yellow-50 text-yellow-700 border-yellow-200",
  alto:     "bg-orange-50 text-orange-700 border-orange-200",
  crítico:  "bg-red-50    text-red-700    border-red-200",
};

export default function SolucionesTable({ soluciones }: { soluciones: Solucion[] }) {
  const [descargando, setDescargando] = useState<string | null>(null);

  async function descargar(id: number, tipo: "word" | "pdf", asig: string) {
    const key = `${id}-${tipo}`;
    setDescargando(key);
    try {
      const blob = await exportarDoc(id, tipo);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `plan_refuerzo_${asig}.${tipo === "word" ? "docx" : "pdf"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Error al descargar el documento.");
    } finally {
      setDescargando(null);
    }
  }

  if (!soluciones.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400">
        <AlertTriangle size={36} className="mb-3 text-gray-300" />
        <p className="text-sm">No hay soluciones generadas todavía.</p>
        <p className="text-xs mt-1">Ejecuta el análisis desde la página de Presentación.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50">
            {["Carrera", "Asignatura", "Docente", "Estudiantes en recuperación",
              "Nivel de riesgo", "Acciones"].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {soluciones.map((s) => (
            <tr key={s.id} className="hover:bg-gray-50/60 transition-colors">
              <td className="px-4 py-3 text-gray-600 text-xs">{s.carrera_nombre}</td>
              <td className="px-4 py-3">
                <p className="font-medium text-gray-900">{s.asignatura_nombre}</p>
                <p className="text-xs text-gray-400">{s.asignatura_codigo}</p>
              </td>
              <td className="px-4 py-3 text-gray-600">{s.docente_nombre}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <CheckCircle size={14} className="text-indigo-400" />
                  <span className="font-medium text-gray-900">
                    {s.cantidad_estudiantes_recuperacion}
                  </span>
                  <span className="text-xs text-gray-400">/ {s.total_estudiantes}</span>
                </div>
              </td>
              <td className="px-4 py-3">
                <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize
                  ${RIESGO_STYLE[s.nivel_riesgo] ?? RIESGO_STYLE["medio"]}`}>
                  {s.nivel_riesgo}
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  {(["word", "pdf"] as const).map((tipo) => {
                    const key  = `${s.id}-${tipo}`;
                    const busy = descargando === key;
                    return (
                      <button
                        key={tipo}
                        onClick={() => descargar(s.id, tipo, s.asignatura_codigo)}
                        disabled={!!descargando}
                        title={`Descargar ${tipo.toUpperCase()}`}
                        className="flex items-center gap-1 rounded-lg border border-gray-200
                                   px-2.5 py-1.5 text-xs text-gray-600 transition
                                   hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700
                                   disabled:opacity-50"
                      >
                        {busy
                          ? <Loader2 size={12} className="animate-spin" />
                          : tipo === "word" ? <FileText size={12} /> : <FileDown size={12} />}
                        {tipo.toUpperCase()}
                      </button>
                    );
                  })}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}