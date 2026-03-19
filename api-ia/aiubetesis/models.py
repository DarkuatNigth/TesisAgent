from django.db import models

class PromptTemplate(models.Model):
    nombre_identificador = models.CharField(max_length=100, unique=True, help_text="Ej: prompt_softcomputing_v1")
    system_instruction = models.TextField(help_text="Rol y contexto general para Gemini.")
    prompt_body = models.TextField(help_text="El esqueleto del prompt con variables. Ej: {calificaciones}")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_identificador

class RegistroAnalisisIA(models.Model):
    prompt_utilizado = models.ForeignKey(PromptTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    # JSONField es perfecto para PostgreSQL, permite hacer consultas directas dentro del JSON después
    datos_entrada_json = models.JSONField(help_text="JSON exacto que se recibió del Frontend")
    respuesta_ia_json = models.JSONField(help_text="JSON estructurado que devolvió Gemini")
    exitoso = models.BooleanField(default=True, help_text="Indica si la IA respondió sin errores")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Análisis {self.id} - {self.fecha_creacion.strftime('%Y-%m-%d %H:%M')}"