from django.db import models

class PromptTemplate(models.Model):
    nombre_identificador = models.CharField(
        max_length=100, unique=True,
        help_text="Ej: prompt_softcomputing_v1"
    )
    system_instruction = models.TextField(
        help_text="Rol y contexto general para Gemini."
    )
    prompt_body = models.TextField(
        help_text="El esqueleto del prompt con variables. Ej: {calificaciones}"
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"ia"."prompt_template"'
    def __str__(self):
        return self.nombre_identificador

class RegistroAnalisisIA(models.Model):
    prompt_utilizado = models.ForeignKey(
        PromptTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    datos_entrada_json = models.JSONField(
        help_text="JSON exacto que se recibió del Frontend"
    )
    respuesta_ia_json = models.JSONField(
        help_text="JSON estructurado que devolvió Gemini",
        null=True, blank=True
    )
    exitoso = models.BooleanField(
        default=True, help_text="Indica si la IA respondió sin errores"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"ia"."registro_analisis_ia"'

    def __str__(self):
        return f"Análisis {self.id} - {self.fecha_creacion.strftime('%Y-%m-%d %H:%M')}"


class SolucionGenerada(models.Model):
    """
    Almacena el resultado estructurado del agente IA por cada asignatura
    analizada. Sirve como fuente para los endpoints de listado y exportación.

    Campos para el listado (endpoint listar-soluciones/):
      - carrera_nombre
      - asignatura_nombre
      - docente_nombre
      - cantidad_estudiantes_recuperacion
      - diagnostico_json (estructura completa de Gemini)

    El campo diagnostico_json sigue el esquema DiagnosticoIADTO,
    extendido con los campos de contexto académico.
    """

    registro_analisis = models.ForeignKey(
        RegistroAnalisisIA,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="soluciones",
    )
    # Contexto académico (desnormalizado para acceso rápido en el listado)
    carrera_nombre = models.CharField(max_length=150)
    asignatura_codigo = models.CharField(max_length=20)
    asignatura_nombre = models.CharField(max_length=150)
    paralelo_id = models.IntegerField(null=True, blank=True)
    docente_nombre = models.CharField(max_length=150)
    docente_id = models.CharField(max_length=50, blank=True)

    # Métricas de rendimiento
    total_estudiantes = models.IntegerField(default=0)
    cantidad_estudiantes_recuperacion = models.IntegerField(default=0)

    # Resultado completo de Gemini
    diagnostico_json = models.JSONField(
        help_text="JSON estructurado DiagnosticoIADTO devuelto por Gemini"
    )

    # Estado y trazabilidad
    exitoso = models.BooleanField(default=True)
    periodo_codigo = models.CharField(max_length=20, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"ia"."solucion_generada"'
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["periodo_codigo", "asignatura_codigo"]),
            models.Index(fields=["exitoso", "fecha_creacion"]),
        ]

    def __str__(self):
        return (
            f"Solución [{self.asignatura_codigo}] "
            f"{self.asignatura_nombre} — {self.fecha_creacion.strftime('%Y-%m-%d')}"
        )