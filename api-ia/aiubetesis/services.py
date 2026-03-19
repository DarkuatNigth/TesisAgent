import json
from google import genai
from google.genai import types
from django.conf import settings
from .models import PromptTemplate
from .serializers import DiagnosticoIADTO # Tu DTO de Pydantic

class GeminiService:
    def __init__(self):
        # El cliente se inicializa usando la variable de entorno cargada en Docker
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generar_plan_refuerzo(self, estudiante_data, prompt_name="prompt_evaluacion_softcomputing"):
        # 1. Traer el Prompt dinámico desde PostgreSQL
        try:
            template = PromptTemplate.objects.get(nombre_identificador=prompt_name, activo=True)
        except PromptTemplate.DoesNotExist:
            raise ValueError(f"El prompt '{prompt_name}' no existe en la base de datos.")

        # 2. Formatear el prompt con los datos del estudiante
        calificaciones_json = json.dumps(estudiante_data['calificaciones'], ensure_ascii=False)
        
        prompt_final = template.prompt_body.format(
            calificaciones=calificaciones_json,
            revision_recursos=estudiante_data['revision_recursos'],
            desarrollo_actividades=estudiante_data['desarrollo_actividades'],
            conectividad=estudiante_data['conectividad'],
            perfil_docente=estudiante_data['perfil_docente']
        )

        # 3. Llamada a la IA (usando los parámetros de la BD)
        response = self.client.models.generate_content(
            model=template.modelo_ia,
            contents=prompt_final,
            config=types.GenerateContentConfig(
                system_instruction=template.system_instruction,
                ##temperature=template.temperatura,
                response_mime_type="application/json",
                response_schema=DiagnosticoIADTO,
            ),
        )
        
        return json.loads(response.text)