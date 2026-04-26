# aiubetesis/Services/services.py
import json
import logging
from google import genai
from google.genai import types
from django.conf import settings

from ..models import PromptTemplate, RegistroAnalisisIA, SolucionGenerada
from ..serializers import DiagnosticoIADTO

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Servicio de integración con Gemini AI.

    Adaptado para recibir el payload generado por SegmentadorRendimiento
    en lugar de datos manuales del usuario.
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # ----------------------------------------------------------
    def analizar_grupo_asignatura(
        self,
        grupo_payload: dict,
        carrera_nombre: str,
        asignatura_nombre: str,
        asignatura_codigo: str,
        paralelo_id: int,
        docente_nombre: str,
        docente_id: str,
        total_estudiantes: int,
        cantidad_bajo_rendimiento: int,
        periodo_codigo: str,
        prompt_name: str = "prompt_evaluacion_softcomputing",
    ) -> SolucionGenerada:
        """
        Analiza un grupo de estudiantes con bajo rendimiento en una asignatura.
        Guarda el resultado en ia.solucion_generada y retorna el objeto.

        :param grupo_payload: dict devuelto por GrupoAsignatura.payload_gemini()
        :param ...: metadatos del contexto académico para guardar en la BD
        """

        # 1. Obtener template del prompt
        try:
            template = PromptTemplate.objects.get(
                nombre_identificador=prompt_name, activo=True
            )
        except PromptTemplate.DoesNotExist:
            raise ValueError(f"El prompt '{prompt_name}' no existe en la base de datos.")

        # 2. Construir prompt con datos del segmentador
        muestra = grupo_payload.get("muestra_estudiantes", [])
        if not muestra:
            raise ValueError("No hay estudiantes en la muestra para analizar.")

        # Tomamos el primer estudiante de la muestra como representativo
        # (el prompt está diseñado para un perfil, Gemini infiere el patrón grupal)
        est_rep = muestra[0]

        calificaciones_json = json.dumps(
            est_rep.get("calificaciones", []), ensure_ascii=False
        )

        prompt_final = template.prompt_body.format(
            calificaciones=calificaciones_json,
            revision_recursos=est_rep.get("revision_recursos", "No disponible"),
            desarrollo_actividades=est_rep.get("desarrollo_actividades", "No disponible"),
            conectividad=est_rep.get("conectividad", "No disponible"),
            perfil_docente=est_rep.get("perfil_docente", docente_nombre),
        )

        # Contexto adicional para que Gemini conozca la asignatura exacta
        contexto_adicional = (
            f"\n\nCONTEXTO ACADÉMICO:\n"
            f"  Carrera: {carrera_nombre}\n"
            f"  Asignatura: {asignatura_nombre} ({asignatura_codigo})\n"
            f"  Docente: {docente_nombre}\n"
            f"  Estudiantes bajo rendimiento: {cantidad_bajo_rendimiento} "
            f"de {total_estudiantes} matriculados.\n"
            f"  Se muestran {len(muestra)} estudiantes representativos.\n"
            f"  Genera EXACTAMENTE 3 tareas de recuperación diferenciadas.\n"
        )
        prompt_final += contexto_adicional

        # 3. Preparar registro en BD
        registro_bd = RegistroAnalisisIA(
            prompt_utilizado=template,
            datos_entrada_json=grupo_payload,
            exitoso=False,
        )

        try:
            # 4. Llamada a Gemini
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    system_instruction=template.system_instruction,
                    response_mime_type="application/json",
                    response_schema=DiagnosticoIADTO,
                    temperature=0.3,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )

            respuesta_json = json.loads(response.text)

            # 5. Guardar registro de análisis
            registro_bd.respuesta_ia_json = respuesta_json
            registro_bd.exitoso = True
            registro_bd.save()

            # 6. Guardar SolucionGenerada
            solucion = SolucionGenerada.objects.create(
                registro_analisis=registro_bd,
                carrera_nombre=carrera_nombre,
                asignatura_codigo=asignatura_codigo,
                asignatura_nombre=asignatura_nombre,
                paralelo_id=paralelo_id,
                docente_nombre=docente_nombre,
                docente_id=docente_id,
                total_estudiantes=total_estudiantes,
                cantidad_estudiantes_recuperacion=cantidad_bajo_rendimiento,
                diagnostico_json=respuesta_json,
                exitoso=True,
                periodo_codigo=periodo_codigo,
            )

            logger.info(
                "SolucionGenerada creada: id=%d, asignatura=%s",
                solucion.id, asignatura_codigo
            )
            return solucion

        except Exception as e:
            registro_bd.respuesta_ia_json = {"error": str(e)}
            registro_bd.save()
            logger.error("Error Gemini para asignatura %s: %s", asignatura_codigo, e)
            raise e