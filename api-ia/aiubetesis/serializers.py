# api/serializers.py
from rest_framework import serializers
from pydantic import BaseModel, Field
from typing import List

# ==========================================
# 1. DTOs de ENTRADA (Validación con Django REST)
# ==========================================
class TareaCalificadaSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=True)
    calificacion = serializers.FloatField(required=True)
    objetivo = serializers.CharField(allow_blank=True, required=False)
    peso_porcentaje = serializers.FloatField(required=False, default=0.0) # Útil si le mandas el peso de la tarea

class EstudianteDataSerializer(serializers.Serializer):
    # Ahora calificaciones recibe un Array de Objetos JSON
    calificaciones = TareaCalificadaSerializer(many=True) 
    revision_recursos = serializers.CharField(required=True)
    desarrollo_actividades = serializers.CharField(required=True)
    conectividad = serializers.CharField(required=True)
    perfil_docente = serializers.CharField(required=True)
    
    def validate(self, data):
        for field, value in data.items():
            if isinstance(value, str) and not value.strip():
                raise serializers.ValidationError(
                    {field: "El campo no puede estar vacío o contener solo espacios."}
                )
        return data

# ==========================================
# 2. DTOs de SALIDA (Estructura para Gemini IA)
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
    materia_detectada: str = Field(description="Nombre inferido de la asignatura (ej: Inteligencia Artificial, Matemáticas)")
    tema_critico_detectado: str = Field(description="El tema o concepto específico de mayor peso donde el alumno falló (ej: Algoritmos Genéticos)")
    componente_principal: str = Field(description="El problema raíz (ej. Disonancia Pedagógica o Brecha Digital)")
    nivel_riesgo: str = Field(description="bajo | medio | alto | crítico")
    justificacion_pedagogica: List[str] = Field(description="Por qué reprobó, basado en los resultados de aprendizaje no alcanzados")
    plan_refuerzo_eva: List[TareaEVADTO] = Field(description="Lista de tareas estructuradas para subir al EVA")
    conclusion: str = Field(description="Conclusión final del experto")
    requiere_intervencion_docente: bool = Field(description="True si el problema requiere acción del docente")