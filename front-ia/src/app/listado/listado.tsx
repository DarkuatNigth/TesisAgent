"use client";
import { useEffect, useState } from "react";
import { listarSoluciones } from "@/lib/api";
import SolucionesTable from "@/components/SolucionesTable";
import { LayoutList, Loader2 } from "lucide-react";
import type { ListadoResponse, Solucion } from "@/types";

export default function ListadoPage() {
  const [soluciones, setSoluciones] = useState<Solucion[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);

  useEffect(() => {
    listarSoluciones()
      .then((data: ListadoResponse) => setSoluciones(data?.data ?? []))
      .catch(() => setError("No se pudo conectar con el servidor."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <div className="mb-8 flex items-center gap-3">
        <div className="rounded-xl bg-indigo-50 p-2.5">
          <LayoutList size={20} className="text-indigo-600" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Soluciones generadas</h1>
          <p className="text-sm text-gray-400">{soluciones.length} resultados</p>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <Loader2 size={24} className="animate-spin mr-2" />
          <span className="text-sm">Cargando soluciones…</span>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && <SolucionesTable soluciones={soluciones} />}
    </div>
  );
}