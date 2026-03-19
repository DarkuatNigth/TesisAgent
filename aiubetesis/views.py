# api/views.py
import os
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Importamos las estructuras desde nuestro archivo serializers.py
from .serializers import EstudianteDataSerializer, DiagnosticoIADTO

from google import genai
from google.genai import types

from dotenv import load_dotenv
load_dotenv()

# Configuración del cliente de Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """Eres un experto en psicopedagogía y análisis de rendimiento académico 
universitario. Contexto institucional importante: los docentes son asignados por 
disponibilidad horaria y antigüedad, NO por afinidad disciplinar. Esto puede generar 
disonancia pedagógica cuando un docente dicta una asignatura alejada de su perfil 
de investigación, afectando directamente la calidad del proceso de enseñanza-aprendizaje.
Siempre considera este factor estructural al emitir tu diagnóstico."""


class AnalisisRendimientoView(APIView):
    def post(self, request, *args, **kwargs):
        if not client:
            return Response({
                "code": 500,
                "data": None,
                "message": "Falta la API Key de Gemini en las variables de entorno."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = EstudianteDataSerializer(data=request.data)

        if serializer.is_valid():
            datos = serializer.validated_data
        
        if serializer.is_valid():
            datos = serializer.validated_data
            
          
            prompt = f"""
            Analiza al estudiante con los siguientes datos:

            - Calificaciones: {datos['calificaciones']}
              (referencia: promedio institucional 7.2/10, umbral de bajo rendimiento < 6.0)
            - Revisión de recursos: {datos['revision_recursos']}
              (ej: cantidad de materiales consultados vs disponibles)
            - Desarrollo de actividades: {datos['desarrollo_actividades']}
              (ej: tareas entregadas, entregas tardías, tareas pendientes)
            - Conectividad: {datos['conectividad']}
              (ej: sesiones registradas en plataforma, duración promedio)
            - Perfil docente: {datos['perfil_docente']}
              (ej: especialidad del docente vs materia que dicta)

            Con base en estos datos, determina el componente principal del bajo rendimiento
            y genera exactamente 3 actividades accionables para resolverlo.
            """
            
            try:
                # 2. Llamada al modelo forzando la salida en JSON basada en nuestro DTO
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=DiagnosticoIADTO,
                    ),
                )
                
                # 3. Formateamos la respuesta de la IA a diccionario
                diagnostico_json = json.loads(response.text)
                
                return Response({
                    "code": 200,
                    "data": {"diagnostico_y_actividades": diagnostico_json},
                    "message": "Análisis generado exitosamente por Gemini IA"
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "code": 500,
                    "data": None,
                    "message": f"Error interno con la IA: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "code": 400,
            "data": serializer.errors,
            "message": "Los parámetros enviados en el JSON no son válidos"
        }, status=status.HTTP_400_BAD_REQUEST)