"use client";
import { useState } from "react";
import { BrainCircuit, Users, BookOpen, FileText, Loader2 } from "lucide-react";
import { ejecutarAnalisis } from "@/lib/api";
import type { AnalisisResponse } from "@/types";

export default function PresentacionPage() {
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<AnalisisResponse | null>(null);
  const [error, setError]       = useState<string | null>(null);

  async function handleAnalizar() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await ejecutarAnalisis();
      setResult(data);
    } catch {
      setError("No se pudo conectar con el servidor Django.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-16">
      {/* Hero */}
      <div className="mb-16 text-center">
        <div className="mb-6 inline-flex items-center justify-center rounded-2xl bg-indigo-50 p-5">
          <BrainCircuit size={48} className="text-indigo-600" />
        </div>
        <h1 className="mb-4 text-4xl font-semibold tracking-tight text-gray-900">
          Sistema de análisis de rendimiento estudiantil
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-gray-500 leading-relaxed">
          Detecta automáticamente estudiantes con bajo rendimiento, genera planes de
          recuperación personalizados con IA y exporta documentos listos para el EVA.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <button
            onClick={handleAnalizar}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3
                       text-sm font-medium text-white transition hover:bg-indigo-700
                       active:scale-95 disabled:opacity-60"
          >
            {loading
              ? <><Loader2 size={16} className="animate-spin" /> Analizando…</>
              : <><BrainCircuit size={16} /> Ejecutar análisis</>}
          </button>
        </div>
      </div>

      {/* Tarjetas de características */}
      <div className="mb-16 grid gap-4 sm:grid-cols-3">
        {[
          { icon: Users,    title: "Segmentación automática",
            desc: "El algoritmo lee directamente desde la base de datos y clasifica estudiantes según indicadores de comportamiento académico." },
          { icon: BrainCircuit, title: "Planes con IA Gemini",
            desc: "Por cada asignatura detectada genera hasta 3 tareas de recuperación diferenciadas con objetivos, pasos y rúbricas." },
          { icon: FileText, title: "Exportación Word y PDF",
            desc: "Descarga el plan de refuerzo listo para subir al EVA con un solo clic en Word o PDF." },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title}
               className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-3 inline-flex rounded-xl bg-indigo-50 p-2.5">
              <Icon size={20} className="text-indigo-600" />
            </div>
            <h3 className="mb-2 text-sm font-medium text-gray-900">{title}</h3>
            <p className="text-sm leading-relaxed text-gray-500">{desc}</p>
          </div>
        ))}
      </div>

      {/* Resultado del análisis */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}
      {result && (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-6">
          <p className="mb-4 text-sm font-medium text-green-800">{result.message}</p>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              { label: "Asignaturas analizadas", value: result.data.asignaturas_analizadas },
              { label: "Soluciones generadas",   value: result.data.soluciones_generadas },
              { label: "Con errores",            value: result.data.errores.length },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl bg-white/70 p-3 text-center">
                <p className="text-2xl font-semibold text-green-700">{value}</p>
                <p className="text-xs text-green-600">{label}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}