# aiubetesis/views.py
import json
import logging
from django.http import HttpResponse, StreamingHttpResponse
from django.conf import settings
from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from google import genai
from google.genai import types

from .serializers import (
    AnalisisRendimientoInputSerializer,
    ExportarDocSerializer,
    SolucionListadoSerializer,
)
from .Services.services import GeminiService
from .Algorithm.rendimiento_segmentador import SegmentadorRendimiento
from .models import SolucionGenerada
from .Aplicaciones.document_service import ExportDocumentService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------
# 1. POST /api/v1/analisis-rendimiento/
# ---------------------------------------------------------------
class AnalisisRendimientoView(APIView):
    """
    Ejecuta el pipeline completo:
      Segmentador → Gemini → SolucionGenerada

    Se puede llamar sin body (usa valores por defecto) o con:
      { "periodo_codigo": "2024-2", "carrera_id": 1, "umbral_nota": 6.0 }
    """

    def post(self, request, *args, **kwargs):
        logger.info("POST /api/v1/analisis-rendimiento/ iniciado")

        serializer = AnalisisRendimientoInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"code": 400, "data": serializer.errors, "message": "Parametros invalidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        periodo_codigo = serializer.validated_data["periodo_codigo"]
        carrera_id     = serializer.validated_data["carrera_id"]
        umbral_nota    = serializer.validated_data["umbral_nota"]

        try:
            segmentador = SegmentadorRendimiento(
                carrera_id=carrera_id,
                periodo_codigo=periodo_codigo,
                umbral=umbral_nota,
            )
            grupos = segmentador.segmentar()
        except Exception as e:
            logger.error("Error en segmentacion: %s", e, exc_info=True)
            return Response(
                {"code": 500, "message": f"Error al segmentar datos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not grupos:
            return Response(
                {
                    "code": 200,
                    "data": {"soluciones_generadas": 0},
                    "message": (
                        f"No se encontraron estudiantes con bajo rendimiento "
                        f"(umbral={umbral_nota}) en el periodo {periodo_codigo}."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        gemini_service     = GeminiService()
        soluciones_creadas = []
        errores            = []

        for grupo in grupos:
            try:
                solucion = gemini_service.analizar_grupo_asignatura(
                    grupo_payload=grupo.payload_gemini(),
                    carrera_nombre=grupo.carrera_nombre,
                    asignatura_nombre=grupo.asignatura_nombre,
                    asignatura_codigo=grupo.asignatura_codigo,
                    paralelo_id=grupo.paralelo_id,
                    docente_nombre=grupo.docente_nombre,
                    docente_id=grupo.docente_id,
                    total_estudiantes=grupo.total_estudiantes,
                    cantidad_bajo_rendimiento=grupo.cantidad_bajo_rendimiento,
                    periodo_codigo=periodo_codigo,
                )
                soluciones_creadas.append({
                    "id": solucion.id,
                    "asignatura": grupo.asignatura_nombre,
                    "estudiantes_recuperacion": grupo.cantidad_bajo_rendimiento,
                })
            except Exception as e:
                logger.error("Error Gemini para %s: %s", grupo.asignatura_codigo, e)
                errores.append({
                    "asignatura": grupo.asignatura_nombre,
                    "error": str(e),
                })

        return Response(
            {
                "code": 200,
                "data": {
                    "soluciones_generadas": len(soluciones_creadas),
                    "asignaturas_analizadas": len(grupos),
                    "soluciones": soluciones_creadas,
                    "errores": errores,
                },
                "message": (
                    f"Se generaron {len(soluciones_creadas)} planes de refuerzo "
                    f"para el periodo {periodo_codigo}."
                ),
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------
# 2. GET /api/v1/listar-soluciones/
# ---------------------------------------------------------------
class ListarSolucionesView(APIView):
    """
    Listado paginado de soluciones generadas.
    Query params opcionales:
      - periodo_codigo (ej: 2024-2)
      - asignatura_codigo
    """

    def get(self, request, *args, **kwargs):
        qs = SolucionGenerada.objects.filter(exitoso=True)

        periodo = request.query_params.get("periodo_codigo")
        asig    = request.query_params.get("asignatura_codigo")
        if periodo:
            qs = qs.filter(periodo_codigo=periodo)
        if asig:
            qs = qs.filter(asignatura_codigo=asig)

        serializer = SolucionListadoSerializer(qs, many=True)
        return Response(
            {
                "code": 200,
                "data": serializer.data,
                "total": qs.count(),
                "message": "Listado de soluciones generadas.",
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------
# 3. POST /api/v1/exportar-doc/
# ---------------------------------------------------------------
class ExportarDocView(APIView):
    """
    Exporta el plan de refuerzo como Word o PDF.
    Body: { "id": int, "tipoDoc": "word" | "pdf" }
    """

    def post(self, request, *args, **kwargs):
        serializer = ExportarDocSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"code": 400, "data": serializer.errors, "message": "Parametros invalidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solucion_id = serializer.validated_data["id"]
        tipo_doc    = serializer.validated_data["tipoDoc"]

        try:
            solucion = SolucionGenerada.objects.get(id=solucion_id, exitoso=True)
        except SolucionGenerada.DoesNotExist:
            return Response(
                {"code": 404, "message": f"Solucion con id={solucion_id} no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        export_service = ExportDocumentService(solucion)
        nombre_archivo = (
            f"plan_refuerzo_{solucion.asignatura_codigo}_{solucion.periodo_codigo}"
        )

        try:
            if tipo_doc == "word":
                buffer       = export_service.generar_word()
                content_type = (
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                )
                nombre_archivo += ".docx"
            else:
                buffer       = export_service.generar_pdf()
                content_type = "application/pdf"
                nombre_archivo += ".pdf"

            response = HttpResponse(buffer.read(), content_type=content_type)
            response["Content-Disposition"] = (
                f'attachment; filename="{nombre_archivo}"'
            )
            return response

        except Exception as e:
            logger.error("Error al generar documento: %s", e, exc_info=True)
            return Response(
                {"code": 500, "message": f"Error al generar el documento: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------
# 4. POST /api/v1/chat-agente/
# ---------------------------------------------------------------
 
def _clasificar_error_gemini(error: Exception) -> dict:
    """
    Detecta el tipo de error de Gemini y retorna un mensaje
    claro para mostrar al usuario en el front.
    """
    mensaje_error = str(error)
 
    if "429" in mensaje_error or "RESOURCE_EXHAUSTED" in mensaje_error:
        return {
            "tipo": "cuota_agotada",
            "mensaje": (
                "Se ha agotado la cuota disponible de la IA por hoy. "
                "Esto ocurre porque la API key utilizada es de nivel gratuito "
                "y tiene un limite diario de solicitudes. "
                "Por favor intenta nuevamente manana o contacta al administrador "
                "para actualizar el plan de la API."
            ),
        }
 
    if "401" in mensaje_error or "API_KEY_INVALID" in mensaje_error:
        return {
            "tipo": "api_key_invalida",
            "mensaje": (
                "La clave de acceso a la IA no es valida o ha expirado. "
                "Contacta al administrador del sistema."
            ),
        }
 
    if "503" in mensaje_error or "UNAVAILABLE" in mensaje_error:
        return {
            "tipo": "servicio_no_disponible",
            "mensaje": (
                "El servicio de IA no esta disponible en este momento. "
                "Por favor intenta en unos minutos."
            ),
        }
 
    if "deadline" in mensaje_error.lower() or "timeout" in mensaje_error.lower():
        return {
            "tipo": "timeout",
            "mensaje": (
                "La solicitud tardo demasiado en procesarse. "
                "Por favor intenta con una pregunta mas corta."
            ),
        }
 
    return {
        "tipo": "error_desconocido",
        "mensaje": "Ocurrio un error inesperado. Por favor intenta nuevamente.",
    }
 
class ChatAgenteView(APIView):
    """
    Recibe el mensaje del usuario, construye un contexto compacto
    agrupando asignaturas unicas desde la BD y llama a Gemini
    con streaming. Incluye manejo de errores clasificado.
    """
 
    def post(self, request, *args, **kwargs):
        mensaje = request.data.get("mensaje", "").strip()
        if not mensaje:
            return Response(
                {"error": "El campo 'mensaje' es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        # 1. Contexto compacto — agrupa por asignatura unica
        resumen = (
            SolucionGenerada.objects
            .filter(exitoso=True)
            .values(
                "asignatura_nombre",
                "asignatura_codigo",
                "docente_nombre",
                "carrera_nombre",
                "periodo_codigo",
            )
            .annotate(
                max_recuperacion=Max("cantidad_estudiantes_recuperacion"),
                max_total=Max("total_estudiantes"),
            )
            .order_by("-max_recuperacion")[:12]
        )
 
        if not resumen:
            contexto = "No hay soluciones generadas en el sistema todavia."
        else:
            lineas = [
                f"- {s['asignatura_nombre']} ({s['asignatura_codigo']}): "
                f"{s['max_recuperacion']} de {s['max_total']} estudiantes en recuperacion, "
                f"docente: {s['docente_nombre']}, "
                f"periodo: {s['periodo_codigo']}"
                for s in resumen
            ]
            total_recuperacion = sum(s['max_recuperacion'] for s in resumen)
            total_estudiantes  = sum(s['max_total'] for s in resumen)
            contexto = (
                f"Total general: {total_recuperacion} estudiantes en recuperacion "
                f"de {total_estudiantes} analizados.\n\n"
                "Detalle por asignatura:\n" + "\n".join(lineas)
            )
 
        # 2. Prompt compacto
        prompt = (
            "Eres el asistente academico del sistema InnoTech UBE. "
            "Interpreta los datos de rendimiento estudiantil.\n\n"
            f"DATOS DEL SISTEMA:\n{contexto}\n\n"
            f"PREGUNTA: {mensaje}\n\n"
            "Responde en espanol, conciso y basandote solo en los datos anteriores."
        )
 
        # 3. Streaming con Gemini + manejo de errores clasificado
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
 
        def stream_response():
            try:
                for chunk in client.models.generate_content_stream(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2),
                ):
                    if chunk.text:
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"
 
            except Exception as e:
                info_error = _clasificar_error_gemini(e)
                logger.error(
                    "Error Gemini [%s]: %s",
                    info_error["tipo"], e
                )
                yield f"data: {json.dumps({'error': info_error['mensaje'], 'tipo': info_error['tipo']})}\n\n"
 
            yield "data: [DONE]\n\n"
 
        response = StreamingHttpResponse(
            stream_response(),
            content_type="text/event-stream; charset=utf-8",
        )
        response["Cache-Control"]     = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response