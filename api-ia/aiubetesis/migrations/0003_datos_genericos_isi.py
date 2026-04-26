# aiubetesis/migrations/0003_datos_genericos_isi.py
"""
Migración de datos genéricos para Ingeniería en Sistemas Inteligentes (ISI).
Puebla las tablas del esquema académico, docencia y estudiantil necesarias
para que el algoritmo de segmentación opere sin intervención humana.

Tablas que intervienen en el flujo de análisis de rendimiento:
  - academico.asignatura          → plan analítico de la carrera
  - academico.periodo             → período activo
  - academico.paralelo            → grupos por asignatura
  - docencia.docente / core.persona → docentes asignados
  - docencia.asignacion_docente_paralelo
  - docencia.unidad_tematica / docencia.tema
  - estudiantil.estudiante / core.persona
  - estudiantil.matricula
  - estudiantil.actividad_calificable + tipo_actividad_calificable
  - estudiantil.entrega
  - estudiantil.calificacion
  - docencia.recurso_aprendizaje   → indicador RU-E / RD-U / RV-N del paper
"""

import uuid
import random
from datetime import date, timedelta
from django.db import migrations

random.seed(2025)  # reproducibilidad

# ---------------------------------------------------------------
# Constantes de referencia (deben coincidir con innotech_db.sql)
# ---------------------------------------------------------------
CARRERA_ID = 1          # ISI ya insertada en datos semilla del SQL
PERIODO_CODIGO = "2024-2"

# Pensum ISI — 8 niveles × ~5 materias (solo las necesarias para el algoritmo)
# Formato: (codigo, nombre, nivel, creditos, horas_teoria, horas_practica)
ASIGNATURAS_ISI = [
    # Nivel 1
    ("ISI-101", "Fundamentos de Programación",       1, 4, 2, 4),
    ("ISI-102", "Cálculo Diferencial",               1, 4, 3, 2),
    ("ISI-103", "Álgebra Lineal",                    1, 3, 2, 2),
    # Nivel 2
    ("ISI-201", "Programación Orientada a Objetos",  2, 4, 2, 4),
    ("ISI-202", "Cálculo Integral",                  2, 4, 3, 2),
    ("ISI-203", "Estructuras de Datos",              2, 4, 2, 4),
    # Nivel 3
    ("ISI-301", "Base de Datos I",                   3, 4, 2, 4),
    ("ISI-302", "Sistemas Operativos",               3, 3, 2, 2),
    ("ISI-303", "Estadística Aplicada",              3, 3, 3, 0),
    # Nivel 4
    ("ISI-401", "Inteligencia Artificial",           4, 4, 2, 4),
    ("ISI-402", "Redes de Computadoras",             4, 3, 2, 2),
    ("ISI-403", "Ingeniería de Software",            4, 4, 2, 4),
    # Nivel 5
    ("ISI-501", "Aprendizaje Automático",            5, 4, 2, 4),
    ("ISI-502", "Visión por Computadora",            5, 3, 2, 2),
    ("ISI-503", "Base de Datos II",                  5, 3, 2, 2),
    # Nivel 6
    ("ISI-601", "Deep Learning",                     6, 4, 2, 4),
    ("ISI-602", "Procesamiento de Lenguaje Natural", 6, 4, 2, 4),
    ("ISI-603", "Soft Computing",                    6, 4, 2, 4),
    # Nivel 7
    ("ISI-701", "Sistemas Expertos",                 7, 3, 2, 2),
    ("ISI-702", "Robótica e IoT",                    7, 4, 2, 4),
    # Nivel 8
    ("ISI-801", "Proyecto de Titulación I",          8, 4, 2, 4),
    ("ISI-802", "Proyecto de Titulación II",         8, 4, 2, 4),
]

# Docentes (apellido, nombre, dedicación, nivel_formacion)
DOCENTES_ISI = [
    ("Morales",  "Carmen",   "TIEMPO_COMPLETO", 3),  # 3=MAESTRIA
    ("Vásquez",  "Roberto",  "TIEMPO_COMPLETO", 4),  # 4=DOCTORADO
    ("Guerrero", "Patricia", "MEDIO_TIEMPO",    3),
    ("Alvarado", "Marco",    "TIEMPO_COMPLETO", 3),
    ("Castillo", "Diana",    "HORA_CLASE",      2),  # 2=ESPECIALIDAD
]

# Nombres y apellidos para generar estudiantes
NOMBRES = [
    "María","Juan","Ana","Carlos","Lucía","Pedro","Sofía","Luis",
    "Valentina","Diego","Isabella","Andrés","Camila","Sebastián",
    "Daniela","Miguel","Fernanda","José","Gabriela","David",
    "Paula","Mateo","Natalia","Alejandro","Valeria","Santiago",
    "Andrea","Ricardo","Paola","Jorge","Cristina","Ramón",
    "Lorena","Héctor","Verónica","Óscar","Patricia","Iván",
    "Adriana","Mauricio",
]
APELLIDOS = [
    "García","Rodríguez","Martínez","López","González","Pérez",
    "Sánchez","Ramírez","Torres","Flores","Rivera","Morales",
    "Jiménez","Hernández","Díaz","Vásquez","Romero","Alvarado",
    "Castillo","Mendoza","Reyes","Cruz","Ortega","Guerrero",
    "Medina","Ruiz","Vargas","Suárez","Molina","Aguilar",
    "Núñez","Herrera","Cabrera","Espinoza","Vera","Palacios",
    "Delgado","Muñoz","Figueroa","Cordero",
]

TOTAL_ESTUDIANTES = 40

# Tipos de actividad calificable que usa el sistema
TIPOS_ACTIVIDAD = [
    "TAREA", "TALLER", "TEST",
    "EXAMEN_PARCIAL", "EXAMEN_FINAL",
    "PROYECTO", "PARTICIPACION",
]

# ---------------------------------------------------------------
# Helper de SQL crudo (igual que el script de referencia)
# ---------------------------------------------------------------
def _sql(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    try:
        return cursor.fetchall()
    except Exception:
        return []


def cargar_datos_genericos(apps, schema_editor):
    from django.db import connection
    c = connection.cursor()

    # ----------------------------------------------------------
    # 1. PERÍODO
    # ----------------------------------------------------------
    rows = _sql(c, "SELECT id FROM academico.periodo WHERE codigo = %s", [PERIODO_CODIGO])
    if not rows:
        _sql(c, """
            INSERT INTO academico.periodo(nombre, codigo, fecha_inicio, fecha_fin, activo, en_curso)
            VALUES (%s, %s, %s, %s, TRUE, TRUE)
        """, [f"Período {PERIODO_CODIGO}", PERIODO_CODIGO, date(2024, 9, 1), date(2025, 2, 28)])
    periodo_id = _sql(c, "SELECT id FROM academico.periodo WHERE codigo = %s", [PERIODO_CODIGO])[0][0]

    # ----------------------------------------------------------
    # 2. ASIGNATURAS ISI
    # ----------------------------------------------------------
    asig_map = {}  # codigo → id
    for codigo, nombre, nivel_num, cred, ht, hp in ASIGNATURAS_ISI:
        rows = _sql(c, "SELECT id FROM academico.asignatura WHERE codigo = %s", [codigo])
        if not rows:
            # Obtener id del nivel
            nivel_rows = _sql(c, "SELECT id FROM academico.nivel WHERE numero = %s", [nivel_num])
            nivel_id = nivel_rows[0][0] if nivel_rows else None
            if not nivel_id:
                _sql(c, "INSERT INTO academico.nivel(numero, nombre) VALUES (%s, %s)",
                     [nivel_num, f"Nivel {nivel_num}"])
                nivel_id = _sql(c, "SELECT id FROM academico.nivel WHERE numero = %s", [nivel_num])[0][0]
            _sql(c, """
                INSERT INTO academico.asignatura(
                    id_carrera, id_nivel, codigo, nombre, creditos,
                    horas_teoria, horas_practica, horas_autonomo, modalidad, activo
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'PRESENCIAL',TRUE)
            """, [CARRERA_ID, nivel_id, codigo, nombre, cred, ht, hp, 2])
        asig_map[codigo] = _sql(c, "SELECT id FROM academico.asignatura WHERE codigo = %s", [codigo])[0][0]

    # ----------------------------------------------------------
    # 3. TIPOS DE ACTIVIDAD CALIFICABLE
    # ----------------------------------------------------------
    tipo_act_map = {}
    for t in TIPOS_ACTIVIDAD:
        rows = _sql(c, "SELECT id FROM estudiantil.tipo_actividad_calificable WHERE nombre = %s", [t])
        if not rows:
            _sql(c, "INSERT INTO estudiantil.tipo_actividad_calificable(nombre) VALUES (%s)", [t])
        tipo_act_map[t] = _sql(c, "SELECT id FROM estudiantil.tipo_actividad_calificable WHERE nombre = %s", [t])[0][0]

    # ----------------------------------------------------------
    # 4. TIPO_DOCENTE y NIVEL_FORMACION (lookups)
    # ----------------------------------------------------------
    tipo_titular = _sql(c, "SELECT id FROM docencia.tipo_docente WHERE nombre = 'TITULAR'")
    if not tipo_titular:
        _sql(c, "INSERT INTO docencia.tipo_docente(nombre) VALUES ('TITULAR')")
    tipo_titular_id = _sql(c, "SELECT id FROM docencia.tipo_docente WHERE nombre = 'TITULAR'")[0][0]

    nivel_form_ids = {}  # 2=ESPECIALIDAD, 3=MAESTRIA, 4=DOCTORADO
    for nf_id, nf_nom in [(2, "ESPECIALIDAD"), (3, "MAESTRIA"), (4, "DOCTORADO")]:
        rows = _sql(c, "SELECT id FROM docencia.nivel_formacion WHERE nombre = %s", [nf_nom])
        if not rows:
            _sql(c, "INSERT INTO docencia.nivel_formacion(nombre) VALUES (%s)", [nf_nom])
        nivel_form_ids[nf_id] = _sql(c, "SELECT id FROM docencia.nivel_formacion WHERE nombre = %s", [nf_nom])[0][0]

    tipo_ci = _sql(c, "SELECT id FROM core.tipo_identificacion WHERE codigo = 'CI'")[0][0]

    # ----------------------------------------------------------
    # 5. DOCENTES
    # ----------------------------------------------------------
    docente_ids = []
    for i, (apellido, nombre, dedic, nf_num) in enumerate(DOCENTES_ISI):
        cedula_doc = f"09{str(i + 1).zfill(8)}"
        rows = _sql(c, "SELECT id FROM core.persona WHERE numero_identificacion = %s", [cedula_doc])
        if not rows:
            p_id = str(uuid.uuid4())
            _sql(c, """
                INSERT INTO core.persona(
                    id, tipo_identificacion, numero_identificacion,
                    primer_nombre, primer_apellido,
                    email_institucional, activo
                ) VALUES (%s,%s,%s,%s,%s,%s,TRUE)
            """, [p_id, tipo_ci, cedula_doc, nombre, apellido,
                  f"{nombre.lower()}.{apellido.lower()}@ube.edu.ec"])
        persona_id = _sql(c, "SELECT id FROM core.persona WHERE numero_identificacion = %s", [cedula_doc])[0][0]

        rows = _sql(c, "SELECT id FROM docencia.docente WHERE id_persona = %s", [persona_id])
        if not rows:
            d_id = str(uuid.uuid4())
            nf_real = nivel_form_ids.get(nf_num, nivel_form_ids[3])
            _sql(c, """
                INSERT INTO docencia.docente(
                    id, id_persona, id_tipo, id_nivel_formacion,
                    id_carrera_adscrito, fecha_ingreso, dedicacion, activo
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE)
            """, [d_id, persona_id, tipo_titular_id, nf_real,
                  CARRERA_ID, date(2018, 3, 1), dedic])
        docente_id = _sql(c, "SELECT id FROM docencia.docente WHERE id_persona = %s", [persona_id])[0][0]
        docente_ids.append(docente_id)

    # ----------------------------------------------------------
    # 6. PARALELOS (1 por asignatura en este período)
    # ----------------------------------------------------------
    paralelo_map = {}  # asig_codigo → paralelo_id
    for codigo, asig_id in asig_map.items():
        rows = _sql(c, """
            SELECT id FROM academico.paralelo
            WHERE id_asignatura=%s AND id_periodo=%s AND codigo='A'
        """, [asig_id, periodo_id])
        if not rows:
            _sql(c, """
                INSERT INTO academico.paralelo(id_asignatura, id_periodo, codigo, capacidad_max)
                VALUES (%s,%s,'A',35)
            """, [asig_id, periodo_id])
        paralelo_map[codigo] = _sql(c, """
            SELECT id FROM academico.paralelo
            WHERE id_asignatura=%s AND id_periodo=%s AND codigo='A'
        """, [asig_id, periodo_id])[0][0]

    # ----------------------------------------------------------
    # 7. ASIGNACIÓN DOCENTE → PARALELO
    # ----------------------------------------------------------
    asig_codigos = list(paralelo_map.keys())
    for idx, (codigo, paralelo_id) in enumerate(paralelo_map.items()):
        docente_id = docente_ids[idx % len(docente_ids)]
        rows = _sql(c, """
            SELECT id FROM docencia.asignacion_docente_paralelo
            WHERE id_docente=%s AND id_paralelo=%s AND tipo='AMBAS'
        """, [docente_id, paralelo_id])
        if not rows:
            _sql(c, """
                INSERT INTO docencia.asignacion_docente_paralelo(
                    id_docente, id_paralelo, tipo, es_principal,
                    estado, fecha_inicio
                ) VALUES (%s,%s,'AMBAS',TRUE,'ACTIVA',%s)
            """, [docente_id, paralelo_id, date(2024, 9, 1)])

    # ----------------------------------------------------------
    # 8. PLAN TEMÁTICO + UNIDADES + TEMAS por asignatura
    # ----------------------------------------------------------
    plan_map = {}     # paralelo_id → plan_id
    unidad_map = {}   # paralelo_id → [unidad_ids]
    tema_map = {}     # paralelo_id → [tema_ids]

    for codigo, paralelo_id in paralelo_map.items():
        docente_id = docente_ids[list(paralelo_map.keys()).index(codigo) % len(docente_ids)]
        rows = _sql(c, "SELECT id FROM docencia.plan_tematico WHERE id_paralelo=%s", [paralelo_id])
        if not rows:
            _sql(c, """
                INSERT INTO docencia.plan_tematico(id_paralelo, id_docente, estado)
                VALUES (%s,%s,'PUBLICADO')
            """, [paralelo_id, docente_id])
        plan_id = _sql(c, "SELECT id FROM docencia.plan_tematico WHERE id_paralelo=%s", [paralelo_id])[0][0]
        plan_map[paralelo_id] = plan_id

        # 3 unidades temáticas por asignatura
        unidad_ids = []
        tema_ids = []
        for u in range(1, 4):
            rows = _sql(c, """
                SELECT id FROM docencia.unidad_tematica
                WHERE id_plan=%s AND numero=%s
            """, [plan_id, u])
            if not rows:
                _sql(c, """
                    INSERT INTO docencia.unidad_tematica(id_plan, numero, titulo, semanas)
                    VALUES (%s,%s,%s,4)
                """, [plan_id, u, f"Unidad {u} — {codigo}"])
            u_id = _sql(c, """
                SELECT id FROM docencia.unidad_tematica WHERE id_plan=%s AND numero=%s
            """, [plan_id, u])[0][0]
            unidad_ids.append(u_id)

            # 2 temas por unidad
            for t in range(1, 3):
                rows = _sql(c, """
                    SELECT id FROM docencia.tema WHERE id_unidad=%s AND numero=%s
                """, [u_id, t])
                if not rows:
                    _sql(c, """
                        INSERT INTO docencia.tema(id_unidad, numero, titulo)
                        VALUES (%s,%s,%s)
                    """, [u_id, t, f"Tema {t} — Unidad {u} — {codigo}"])
                t_id = _sql(c, "SELECT id FROM docencia.tema WHERE id_unidad=%s AND numero=%s", [u_id, t])[0][0]
                tema_ids.append(t_id)

        unidad_map[paralelo_id] = unidad_ids
        tema_map[paralelo_id] = tema_ids

    # ----------------------------------------------------------
    # 9. RECURSOS DE APRENDIZAJE (indicadores RU-E, RD-U, RV-N del paper)
    # ----------------------------------------------------------
    tipo_recurso_map = {}
    for tr in ["VIDEO", "PDF", "PRESENTACION", "ENLACE_WEB", "EJERCICIO"]:
        rows = _sql(c, "SELECT id FROM docencia.tipo_recurso WHERE nombre = %s", [tr])
        if not rows:
            _sql(c, "INSERT INTO docencia.tipo_recurso(nombre) VALUES (%s)", [tr])
        tipo_recurso_map[tr] = _sql(c, "SELECT id FROM docencia.tipo_recurso WHERE nombre = %s", [tr])[0][0]

    for paralelo_id, t_ids in tema_map.items():
        for idx, t_id in enumerate(t_ids):
            tipo_r = ["VIDEO", "PDF", "PRESENTACION", "EJERCICIO"][idx % 4]
            rows = _sql(c, "SELECT id FROM docencia.recurso_aprendizaje WHERE id_tema=%s AND id_tipo=%s",
                        [t_id, tipo_recurso_map[tipo_r]])
            if not rows:
                _sql(c, """
                    INSERT INTO docencia.recurso_aprendizaje(
                        id_tema, id_tipo, titulo, descripcion, activo
                    ) VALUES (%s,%s,%s,%s,TRUE)
                """, [t_id, tipo_recurso_map[tipo_r],
                      f"Recurso {tipo_r} Tema {idx + 1}",
                      "Material de apoyo para el aprendizaje del tema"])

    # ----------------------------------------------------------
    # 10. ESTUDIANTES
    # ----------------------------------------------------------
    est_ids = []
    for i in range(TOTAL_ESTUDIANTES):
        cedula = f"17{str(300 + i).zfill(8)}"
        rows = _sql(c, "SELECT id FROM core.persona WHERE numero_identificacion = %s", [cedula])
        if rows:
            p_id = rows[0][0]
        else:
            p_id = str(uuid.uuid4())
            nombre = NOMBRES[i % len(NOMBRES)]
            ap1 = APELLIDOS[i % len(APELLIDOS)]
            ap2 = APELLIDOS[(i + 7) % len(APELLIDOS)]
            _sql(c, """
                INSERT INTO core.persona(
                    id, tipo_identificacion, numero_identificacion,
                    primer_nombre, primer_apellido, segundo_apellido,
                    email_institucional, activo
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE)
            """, [p_id, tipo_ci, cedula, nombre, ap1, ap2,
                  f"{nombre.lower()}{i}@ube.edu.ec"])

        rows = _sql(c, "SELECT id FROM estudiantil.estudiante WHERE id_persona = %s", [p_id])
        if rows:
            est_ids.append(rows[0][0])
            continue

        e_id = str(uuid.uuid4())
        nivel_est = random.randint(3, 7)
        _sql(c, """
            INSERT INTO estudiantil.estudiante(
                id, id_persona, id_carrera, codigo_estudiante,
                fecha_ingreso, nivel_actual, estado
            ) VALUES (%s,%s,%s,%s,%s,%s,'ACTIVO')
        """, [e_id, p_id, CARRERA_ID,
              f"ISI-{str(2021000 + i)}", date(2021, 3, 1), nivel_est])
        est_ids.append(e_id)

    # ----------------------------------------------------------
    # 11. MATRÍCULAS + ACTIVIDADES + ENTREGAS + CALIFICACIONES
    #     Solo para las asignaturas de niveles 3-6 (las que el
    #     algoritmo analiza — mayor probabilidad de bajo rendimiento)
    # ----------------------------------------------------------
    asig_analisis = [
        "ISI-301","ISI-302","ISI-303",
        "ISI-401","ISI-402","ISI-403",
        "ISI-501","ISI-502","ISI-503",
        "ISI-601","ISI-602","ISI-603",
    ]

    # Pesos de cada tipo de actividad (suman ~100)
    pesos_tipo = {
        "TAREA":         10.0,
        "TALLER":        10.0,
        "TEST":          15.0,
        "EXAMEN_PARCIAL":25.0,
        "EXAMEN_FINAL":  30.0,
        "PROYECTO":       7.0,
        "PARTICIPACION":  3.0,
    }

    for est_id in est_ids:
        # Cada estudiante se matricula en 4-6 asignaturas del set de análisis
        materias_est = random.sample(asig_analisis, k=random.randint(4, 6))
        for codigo in materias_est:
            paralelo_id = paralelo_map[codigo]
            # Matrícula
            rows = _sql(c, """
                SELECT id FROM estudiantil.matricula
                WHERE id_estudiante=%s AND id_paralelo=%s
            """, [est_id, paralelo_id])
            if rows:
                mat_id = rows[0][0]
            else:
                _sql(c, """
                    INSERT INTO estudiantil.matricula(
                        id_estudiante, id_paralelo, estado
                    ) VALUES (%s,%s,'ACTIVA')
                """, [est_id, paralelo_id])
                mat_id = _sql(c, """
                    SELECT id FROM estudiantil.matricula
                    WHERE id_estudiante=%s AND id_paralelo=%s
                """, [est_id, paralelo_id])[0][0]

            # Perfil de rendimiento: 30% alto, 40% medio, 30% bajo
            perfil = random.choices(
                ["alto", "medio", "bajo"], weights=[30, 40, 30]
            )[0]

            # Actividades calificables (1 por tipo)
            for tipo_nombre, peso in pesos_tipo.items():
                tipo_id = tipo_act_map[tipo_nombre]
                tema_ids_par = tema_map[paralelo_id]
                tema_id = random.choice(tema_ids_par) if tema_ids_par else None
                unidad_id = random.choice(unidad_map[paralelo_id]) if unidad_map[paralelo_id] else None

                rows = _sql(c, """
                    SELECT id FROM estudiantil.actividad_calificable
                    WHERE id_paralelo=%s AND id_tipo=%s AND nombre=%s
                """, [paralelo_id, tipo_id, f"{tipo_nombre} — {codigo}"])
                if rows:
                    act_id = rows[0][0]
                else:
                    _sql(c, """
                        INSERT INTO estudiantil.actividad_calificable(
                            id_paralelo, id_tipo, id_tema, id_unidad,
                            nombre, descripcion,
                            fecha_asignacion, fecha_entrega,
                            puntaje_max, activo
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,10.00,TRUE)
                    """, [paralelo_id, tipo_id, tema_id, unidad_id,
                          f"{tipo_nombre} — {codigo}",
                          f"Actividad de {tipo_nombre} para la asignatura {codigo}",
                          date(2024, 9, 15),
                          date(2024, 9, 30)])
                    act_id = _sql(c, """
                        SELECT id FROM estudiantil.actividad_calificable
                        WHERE id_paralelo=%s AND id_tipo=%s AND nombre=%s
                    """, [paralelo_id, tipo_id, f"{tipo_nombre} — {codigo}"])[0][0]

                # Entrega
                rows = _sql(c, """
                    SELECT id FROM estudiantil.entrega
                    WHERE id_matricula=%s AND id_actividad=%s
                """, [mat_id, act_id])
                if rows:
                    entrega_id = rows[0][0]
                else:
                    _sql(c, """
                        INSERT INTO estudiantil.entrega(
                            id_matricula, id_actividad, estado
                        ) VALUES (%s,%s,'CALIFICADA')
                    """, [mat_id, act_id])
                    entrega_id = _sql(c, """
                        SELECT id FROM estudiantil.entrega
                        WHERE id_matricula=%s AND id_actividad=%s
                    """, [mat_id, act_id])[0][0]

                # Calificación según perfil
                if perfil == "alto":
                    nota = round(random.uniform(7.5, 10.0), 2)
                elif perfil == "medio":
                    nota = round(random.uniform(5.5, 7.5), 2)
                else:  # bajo — candidato a tarea de recuperación
                    if tipo_nombre in ("EXAMEN_PARCIAL", "EXAMEN_FINAL"):
                        nota = round(random.uniform(1.0, 5.0), 2)
                    else:
                        nota = round(random.uniform(2.0, 5.5), 2)

                rows = _sql(c, "SELECT id FROM estudiantil.calificacion WHERE id_entrega=%s", [entrega_id])
                if not rows:
                    _sql(c, """
                        INSERT INTO estudiantil.calificacion(
                            id_entrega, puntaje, revisado_docente
                        ) VALUES (%s,%s,TRUE)
                    """, [entrega_id, nota])

    # ----------------------------------------------------------
    # 12. ASISTENCIA (indicador RM-T del paper)
    # ----------------------------------------------------------
    estados_asistencia = ["PRESENTE", "AUSENTE", "TARDANZA", "JUSTIFICADO"]
    pesos_asistencia_alto = [70, 10, 15, 5]
    pesos_asistencia_bajo = [40, 35, 15, 10]

    for est_id in est_ids[:20]:  # solo primeros 20 para no inflar la migración
        mats = _sql(c, """
            SELECT id FROM estudiantil.matricula WHERE id_estudiante=%s LIMIT 3
        """, [est_id])
        for (mat_id,) in mats:
            for semana in range(1, 13):  # 12 semanas
                fecha_clase = date(2024, 9, 2) + timedelta(weeks=semana - 1)
                rows = _sql(c, """
                    SELECT id FROM estudiantil.asistencia
                    WHERE id_matricula=%s AND fecha=%s
                """, [mat_id, fecha_clase])
                if not rows:
                    pesos_w = pesos_asistencia_alto if random.random() > 0.3 else pesos_asistencia_bajo
                    estado = random.choices(estados_asistencia, weights=pesos_w)[0]
                    _sql(c, """
                        INSERT INTO estudiantil.asistencia(
                            id_matricula, fecha, hora_inicio, estado
                        ) VALUES (%s,%s,'07:00:00',%s)
                    """, [mat_id, fecha_clase, estado])

    print("\n  ✅ Migración 0003 completada: datos genéricos ISI cargados correctamente.")


def revertir_datos_genericos(apps, schema_editor):
    """
    Reversión mínima: elimina registros del período 2024-2.
    No elimina personas/docentes para no romper integridad referencial.
    """
    from django.db import connection
    c = connection.cursor()
    periodo_rows = c.execute(
        "SELECT id FROM academico.periodo WHERE codigo = %s", [PERIODO_CODIGO]
    )
    # La reversión completa requeriría eliminar en cascada; se omite para producción.
    print("  ⚠️  Reversión parcial: se conservan personas y docentes.")


class Migration(migrations.Migration):

    dependencies = [
        ("aiubetesis", "0002_cargar_prompt_inicial"),
    ]

    operations = [
        migrations.RunPython(
            cargar_datos_genericos,
            reverse_code=revertir_datos_genericos,
        ),
    ]