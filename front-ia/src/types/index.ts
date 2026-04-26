export interface Solucion {
  id: number;
  carrera_nombre: string;
  asignatura_nombre: string;
  asignatura_codigo: string;
  docente_nombre: string;
  total_estudiantes: number;
  cantidad_estudiantes_recuperacion: number;
  nivel_riesgo: string;
  fecha_creacion: string;
  acciones: {
    descargar_word: { id: number; tipoDoc: string };
    descargar_pdf:  { id: number; tipoDoc: string };
  };
}

export interface ListadoResponse {
  code: number;
  data: Solucion[];
  total: number;
  message: string;
}

export interface AnalisisResponse {
  code: number;
  data: {
    soluciones_generadas: number;
    asignaturas_analizadas: number;
    soluciones: { id: number; asignatura: string; estudiantes_recuperacion: number }[];
    errores: { asignatura: string; error: string }[];
  };
  message: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}