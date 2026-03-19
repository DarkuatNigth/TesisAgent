# api/serializers.py
from rest_framework import serializers
from pydantic import BaseModel, Field
from typing import List

# ==========================================
# 1. DTO de ENTRADA (Validación con Django REST)
# ==========================================
class EstudianteDataSerializer(serializers.Serializer):
    calificaciones = serializers.CharField(required=True)
    revision_recursos = serializers.CharField(required=True)
    desarrollo_actividades = serializers.CharField(required=True)
    conectividad = serializers.CharField(required=True)
    perfil_docente = serializers.CharField(required=True)
    
    def validate(self, data):
        # Evita prompts vacíos o solo espacios
        for field, value in data.items():
            if not value.strip():
                raise serializers.ValidationError(
                    {field: "El campo no puede estar vacío o contener solo espacios."}
                )
        return data

# ==========================================
# 2. DTOs de SALIDA (Estructura para Gemini IA)
# ==========================================
class ActividadDTO(BaseModel):
    nombre: str = Field(description="Título corto de la actividad")
    objetivo: str = Field(description="Objetivo principal de la actividad")
    descripcion: str = Field(description="Explicación detallada de qué se debe hacer")
    accion: str = Field(description="El paso a paso o acción concreta a tomar")

class DiagnosticoIADTO(BaseModel):
    componente_principal: str = Field(description="El problema raíz (ej. Disonancia Pedagógica)")
    justificacion: List[str] = Field(description="Lista de viñetas justificando el diagnóstico")
    actividades: List[ActividadDTO] = Field(description="Lista de 3 actividades propuestas")
    conclusion: str = Field(description="Conclusión final del experto")