import os
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import EstudianteDataSerializer, DiagnosticoIADTO
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

# ==========================================
# LOGS
# ==========================================
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """
Eres un experto en diseño instruccional y psicopedagogía universitaria.
Tu objetivo es analizar el rendimiento de un estudiante basado en sus calificaciones y el peso de las actividades respecto a los Resultados de Aprendizaje de la materia.
Debes crear un "Plan de Refuerzo" que devuelva tareas estructuradas exactamente como se configuran en un Entorno Virtual de Aprendizaje (EVA).
NO des consejos genéricos. Crea Clases Prácticas o Tareas completas con objetivos, pasos, rúbricas y bibliografía, enfocadas en los temas de mayor peso que el alumno reprobó.
"""

class AnalisisRendimientoView(APIView):
    def post(self, request, *args, **kwargs):
        logger.info("POST /analisis-rendimiento/ recibido")

        if not client:
            logger.error("GEMINI_API_KEY no configurada en variables de entorno")
            return Response({"code": 500, "message": "Falta la API Key."}, status=500)

        serializer = EstudianteDataSerializer(data=request.data)

        if serializer.is_valid():
            datos = serializer.validated_data
            logger.info("Datos del estudiante validados correctamente")

            calificaciones_json_str = json.dumps(datos['calificaciones'], ensure_ascii=False, indent=2)

            prompt = f"""
            Analiza el perfil de este estudiante:

            1. CALIFICACIONES Y RESULTADOS DE APRENDIZAJE:
            {calificaciones_json_str}
            (Evalúa cuáles de estas actividades reprobadas tienen mayor impacto en el aprendizaje general).

            2. VARIABLES DEL ENTORNO:
            - Revisión de recursos: {datos['revision_recursos']}
            - Desarrollo de actividades: {datos['desarrollo_actividades']}
            - Conectividad: {datos['conectividad']}
            - Perfil docente: {datos['perfil_docente']}

            INSTRUCCIONES:
            1. Determina el componente principal del bajo rendimiento ponderando el peso de las tareas fallidas.
            2. Genera las actividades de refuerzo en formato 'TareaEVADTO'. Deben ser actividades nuevas y específicas para subsanar los conceptos no aprendidos, no repetir las tareas originales.
            """

            try:
                logger.info("Enviando prompt a Gemini...")

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=DiagnosticoIADTO,
                        temperature=0.3,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=0  # desactiva el thinking para permitir response_schema
                        ),
                    ),
                )

                logger.info("Respuesta recibida de Gemini correctamente")
                diagnostico_json = json.loads(response.text)

                return Response({
                    "code": 200,
                    "data": {"diagnostico_estructurado": diagnostico_json},
                    "message": "Plan de refuerzo generado exitosamente."
                }, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Error al llamar a Gemini: {str(e)}", exc_info=True)
                return Response({
                    "code": 500,
                    "message": f"Error interno con la IA: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.warning(f"Datos inválidos recibidos: {serializer.errors}")
        return Response({
            "code": 400,
            "data": serializer.errors,
            "message": "Parámetros inválidos."
        }, status=status.HTTP_400_BAD_REQUEST)