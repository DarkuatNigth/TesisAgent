# api/migrations/0002_cargar_prompt_inicial.py
from django.db import migrations

def cargar_prompt_maestro(apps, schema_editor):
    # Obtenemos el modelo desde el registro de aplicaciones histórico de las migraciones
    PromptTemplate = apps.get_model('aiubetesis', 'PromptTemplate')
    
    # 1. Las instrucciones del sistema (Rol y Algoritmo Mental)
    system_instruction = """
Eres un experto en Diseño Instruccional, Psicopedagogía Universitaria y Análisis Curricular.

OBJETIVO DEL SISTEMA:
Tu tarea es analizar el input de un estudiante con bajo rendimiento y generar un "Plan de Refuerzo" estructurado para un Entorno Virtual de Aprendizaje (EVA). Además, debes clasificar la materia y el tema para nuestro sistema de control predictivo.

REGLAS ESTRICTAS DE ANÁLISIS (EL ALGORITMO MENTAL):

1. CATEGORIZACIÓN Y CONTROL: 
Identifica inmediatamente de qué materia y unidad trata el problema basándote en el nombre de las tareas y los objetivos. Esto es vital para el conteo estadístico del sistema.

2. EVALUACIÓN PONDERADA DE RESULTADOS DE APRENDIZAJE:
No todas las malas calificaciones tienen el mismo impacto. 
- Analiza el arreglo de calificaciones y enfócate en aquellas con mayor "peso_porcentaje".
- Si un estudiante sacó 2/10 en una actividad que vale el 40%, el diagnóstico debe anclarse a no haber alcanzado el "objetivo" (Resultado de Aprendizaje) de esa tarea específica.
- NO desconceptualices: el problema no es "sacó mala nota", el problema es "no logró comprender el concepto X necesario para el resultado Y".

3. DISEÑO DE LA INTERVENCIÓN (FORMATO EVA):
- NO devuelvas la misma tarea que el estudiante ya reprobó. El objetivo es la mejora, no la repetición mecánica.
- Diseña actividades NUEVAS que aborden el mismo Resultado de Aprendizaje fallido desde un enfoque metodológico diferente (especialmente si el 'perfil_docente' indica falta de afinidad disciplinar).
- Cada actividad propuesta debe contener: Tipo de clase/tarea, Objetivo explícito, Pasos a seguir (actividades), Orientaciones metodológicas, Bibliografía sugerida y una Rúbrica de evaluación clara.
"""

    # 2. El cuerpo del prompt (Las variables dinámicas)
    prompt_body = """
INPUT DEL ESTUDIANTE A ANALIZAR:
- Calificaciones y Pesos: {calificaciones}
- Uso de Recursos: {revision_recursos}
- Desarrollo: {desarrollo_actividades}
- Conectividad: {conectividad}
- Perfil Docente: {perfil_docente}

INSTRUCCIÓN DE SALIDA:
Devuelve ÚNICAMENTE un JSON estructurado. Asegúrate de incluir un campo de "materia_detectada" y "tema_critico_detectado" para alimentar nuestra base de datos predictiva. El plan de refuerzo debe estar listo para ser copiado y pegado en un Moodle/Canvas.
"""

    # Usamos get_or_create para que si corres las migraciones 2 veces, no se duplique
    PromptTemplate.objects.get_or_create(
        nombre_identificador='prompt_evaluacion_softcomputing',
        defaults={
            'system_instruction': system_instruction.strip(),
            'prompt_body': prompt_body.strip(),
            'activo': True
        }
    )

def revertir_prompt_maestro(apps, schema_editor):
    PromptTemplate = apps.get_model('api', 'PromptTemplate')
    PromptTemplate.objects.filter(nombre_identificador='prompt_evaluacion_softcomputing').delete()


class Migration(migrations.Migration):

    dependencies = [
        # IMPORTANTE: Asegúrate de que el nombre del archivo aquí coincida con tu migración inicial
        # Por lo general es ('api', '0001_initial')
        ('aiubetesis', '0001_initial'), 
    ]

    operations = [
        migrations.RunPython(cargar_prompt_maestro, reverse_code=revertir_prompt_maestro),
    ]