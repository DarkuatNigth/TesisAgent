# api/services.py
import json
from google import genai
from google.genai import types
from django.conf import settings
from .models import PromptTemplate, RegistroAnalisisIA
from .serializers import DiagnosticoIADTO

class GeminiService:
    def __init__(self):
        # El cliente se inicializa usando la variable de entorno cargada en settings
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

        # Preparamos el registro en la base de datos (aún no lo guardamos)
        registro_bd = RegistroAnalisisIA(
            prompt_utilizado=template,
            datos_entrada_json=estudiante_data,
            exitoso=False # Por defecto Falso, cambiará a True si Gemini responde bien
        )

        try:
            # 3. Llamada a la IA
            response = self.client.models.generate_content(
                model='gemini-2.5-flash', # Puedes parametrizar esto en el modelo si lo deseas
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    system_instruction=template.system_instruction,
                    response_mime_type="application/json",
                    response_schema=DiagnosticoIADTO,
                    temperature=0.3,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0  # desactiva el thinking para permitir response_schema
                    ),
                ),
            )
            
            # 4. Procesar la respuesta
            respuesta_json = json.loads(response.text)
            
            # 5. ¡GUARDAR EN LA BASE DE DATOS (ÉXITO)!
            registro_bd.respuesta_ia_json = respuesta_json
            registro_bd.exitoso = True
            registro_bd.save()
            
            return respuesta_json

        except Exception as e:
            # ¡GUARDAR EN LA BASE DE DATOS (ERROR)!
            registro_bd.respuesta_ia_json = {"error": str(e)}
            registro_bd.save()
            raise e # Relanzamos el error para que la vista lo maneje y devuelva un código 500