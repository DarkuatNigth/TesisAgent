# aiubetesis/views.py
"""
Endpoints del sistema de análisis de rendimiento estudiantil.

POST /api/v1/analisis-rendimiento/
    Lee datos de la BD, aplica el algoritmo de segmentación,
    llama a Gemini por cada asignatura con bajo rendimiento y
    persiste los resultados en ia.solucion_generada.

GET  /api/v1/listar-soluciones/
    Devuelve el listado de soluciones generadas con:
      - nombre de carrera, asignatura, docente
      - cantidad de estudiantes en recuperación
      - acciones disponibles (descargar word / pdf)

POST /api/v1/exportar-doc/
    Recibe { id: int, tipoDoc: "word" | "pdf" } y devuelve el archivo.
"""

import logging
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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
                {"code": 400, "data": serializer.errors, "message": "Parámetros inválidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        periodo_codigo = serializer.validated_data["periodo_codigo"]
        carrera_id     = serializer.validated_data["carrera_id"]
        umbral_nota    = serializer.validated_data["umbral_nota"]

        # 1. Segmentar desde la BD
        try:
            segmentador = SegmentadorRendimiento(
                carrera_id=carrera_id,
                periodo_codigo=periodo_codigo,
                umbral=umbral_nota,
            )
            grupos = segmentador.segmentar()
        except Exception as e:
            logger.error("Error en segmentación: %s", e, exc_info=True)
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
                        f"(umbral={umbral_nota}) en el período {periodo_codigo}."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        # 2. Llamar a Gemini por cada grupo
        gemini_service = GeminiService()
        soluciones_creadas = []
        errores = []

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
                logger.error(
                    "Error Gemini para %s: %s", grupo.asignatura_codigo, e
                )
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
                    f"para el período {periodo_codigo}."
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
                {"code": 400, "data": serializer.errors, "message": "Parámetros inválidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solucion_id = serializer.validated_data["id"]
        tipo_doc    = serializer.validated_data["tipoDoc"]

        try:
            solucion = SolucionGenerada.objects.get(id=solucion_id, exitoso=True)
        except SolucionGenerada.DoesNotExist:
            return Response(
                {"code": 404, "message": f"Solución con id={solucion_id} no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        export_service = ExportDocumentService(solucion)
        nombre_archivo = (
            f"plan_refuerzo_{solucion.asignatura_codigo}_{solucion.periodo_codigo}"
        )

        try:
            if tipo_doc == "word":
                buffer = export_service.generar_word()
                content_type = (
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                )
                nombre_archivo += ".docx"
            else:  # pdf
                buffer = export_service.generar_pdf()
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