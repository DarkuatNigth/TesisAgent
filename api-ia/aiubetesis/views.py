# api/views.py
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import EstudianteDataSerializer
from .services import GeminiService

# ==========================================
# LOGS
# ==========================================
logger = logging.getLogger(__name__)

class AnalisisRendimientoView(APIView):
    def post(self, request, *args, **kwargs):
        logger.info("POST /analisis-rendimiento/ recibido")

        serializer = EstudianteDataSerializer(data=request.data)

        if serializer.is_valid():
            datos = serializer.validated_data
            logger.info("Datos del estudiante validados correctamente")

            try:
                # Instanciamos el servicio (que ya tiene la lógica de BD y Gemini)
                servicio_ia = GeminiService()
                logger.info("Enviando datos al servicio de Gemini...")
                
                # Ejecutamos el servicio (puedes cambiar el prompt_name según lo que configures en la BD)
                diagnostico_json = servicio_ia.generar_plan_refuerzo(
                    estudiante_data=datos, 
                    prompt_name="prompt_evaluacion_softcomputing" 
                )
                
                logger.info("Análisis generado y guardado en PostgreSQL exitosamente.")
                
                return Response({
                    "code": 200,
                    "data": {"diagnostico_estructurado": diagnostico_json},
                    "message": "Plan de refuerzo generado exitosamente."
                }, status=status.HTTP_200_OK)

            except ValueError as ve:
                # Error cuando no se encuentra el prompt en PostgreSQL
                logger.error(f"Error de base de datos: {str(ve)}")
                return Response({
                    "code": 404,
                    "message": str(ve)
                }, status=status.HTTP_404_NOT_FOUND)
                
            except Exception as e:
                # Error en la llamada a Gemini
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