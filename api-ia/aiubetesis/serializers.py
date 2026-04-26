# aiubetesis/serializers.py
from rest_framework import serializers
from pydantic import BaseModel, Field
from typing import List, Optional


# ==========================================
# 1. DTOs DE ENTRADA
# ==========================================

class AnalisisRendimientoInputSerializer(serializers.Serializer):
    """
    Entrada para POST /api/v1/analisis-rendimiento/
    Ya no requiere datos manuales: solo el período y la carrera.
    El algoritmo lee el resto desde la BD.
    """
    periodo_codigo = serializers.CharField(
        required=False,
        default="2024-2",
        help_text="Código del período académico. Ej: 2024-2",
    )
    carrera_id = serializers.IntegerField(
        required=False,
        default=1,
        help_text="ID de la carrera en academico.carrera. Por defecto ISI=1",
    )
    umbral_nota = serializers.FloatField(
        required=False,
        default=6.0,
        min_value=1.0,
        max_value=10.0,
        help_text="Nota mínima para no ser considerado bajo rendimiento (default 6.0/10)",
    )


class ExportarDocSerializer(serializers.Serializer):
    """Entrada para POST /api/v1/exportar-doc/"""
    id = serializers.IntegerField(help_text="ID de la SolucionGenerada")
    tipoDoc = serializers.ChoiceField(
        choices=["word", "pdf"],
        help_text="Formato de exportación: 'word' o 'pdf'",
    )


# ==========================================
# 2. DTOs DE SALIDA — Gemini IA (Pydantic)
# ==========================================

class CriterioRubricaDTO(BaseModel):
    criterio: str = Field(description="Ej: Funcionamiento según parámetros")
    descripcion: str = Field(description="Qué se espera que el alumno logre en este criterio")
    puntos_maximos: int = Field(description="Puntaje asignado a este criterio")


class TareaEVADTO(BaseModel):
    tipo: str = Field(description="Ej: Clase Práctica, Tarea, Foro de refuerzo")
    titulo: str = Field(description="Nombre de la actividad")
    objetivo: str = Field(description="Objetivo de la clase o tarea, ligado al resultado de aprendizaje fallido")
    actividades_pasos: List[str] = Field(description="Lista de pasos para el logro del objetivo")
    orientaciones_metodologicas: List[str] = Field(description="Consejos de cómo abordar la tarea")
    bibliografia: List[str] = Field(description="Recursos, enlaces o libros recomendados")
    rubrica_evaluacion: List[CriterioRubricaDTO] = Field(description="Rúbrica de calificación de la tarea")


class DiagnosticoIADTO(BaseModel):
    materia_detectada: str = Field(
        description="Nombre inferido de la asignatura (ej: Inteligencia Artificial)"
    )
    tema_critico_detectado: str = Field(
        description="El tema o concepto específico de mayor peso donde el alumno falló"
    )
    componente_principal: str = Field(
        description="El problema raíz (ej. Disonancia Pedagógica o Brecha Digital)"
    )
    nivel_riesgo: str = Field(description="bajo | medio | alto | crítico")
    justificacion_pedagogica: List[str] = Field(
        description="Por qué reprobó, basado en los resultados de aprendizaje no alcanzados"
    )
    plan_refuerzo_eva: List[TareaEVADTO] = Field(
        description="Lista de tareas estructuradas para subir al EVA (máximo 3)"
    )
    conclusion: str = Field(description="Conclusión final del experto")
    requiere_intervencion_docente: bool = Field(
        description="True si el problema requiere acción del docente"
    )


# ==========================================
# 3. DTOs DE RESPUESTA (para las vistas)
# ==========================================

class SolucionListadoSerializer(serializers.Serializer):
    """Serializer de respuesta para GET /api/v1/listar-soluciones/"""
    id = serializers.IntegerField()
    carrera_nombre = serializers.CharField()
    asignatura_nombre = serializers.CharField()
    asignatura_codigo = serializers.CharField()
    docente_nombre = serializers.CharField()
    total_estudiantes = serializers.IntegerField()
    cantidad_estudiantes_recuperacion = serializers.IntegerField()
    nivel_riesgo = serializers.SerializerMethodField()
    fecha_creacion = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    acciones = serializers.SerializerMethodField()

    def get_nivel_riesgo(self, obj):
        try:
            return obj.diagnostico_json.get("nivel_riesgo", "N/A")
        except Exception:
            return "N/A"

    def get_acciones(self, obj):
        return {
            "descargar_word": {"id": obj.id, "tipoDoc": "word"},
            "descargar_pdf":  {"id": obj.id, "tipoDoc": "pdf"},
        }