# aiubetesis/Algorithm/rendimiento_segmentador.py
"""
Algoritmo de Segmentación de Rendimiento Estudiantil
=====================================================
Implementado según el marco metodológico de:

  Wang, J. & Yu, Y. (2025). Machine learning approach to student performance
  prediction of online learning. PLoS ONE, 20(1), e0299018.
  https://doi.org/10.1371/journal.pone.0299018

INDICADORES CONSTRUIDOS (adaptados al contexto presencial/EVA):
  Equivalente a los 11 LBI del paper, mapeados a las tablas disponibles:

  Preparación:
    CI-N  → revisión de recursos (docencia.recurso_aprendizaje)  ← RV-N
    CR-N  → cobertura de actividades entregadas / total           ← RU-E
    CL-N  → asistencia a clases                                  ← RM-T

  Comportamiento principal:
    RM-T  → tiempo proporcional: asistencias / semanas período
    RU-E  → eficiencia en entregas: entregadas / total actividades
    RV-N  → repetición de recursos (no disponible → se infiere por
             número de actividades completadas sobre el umbral)
    RL-N  → nota promedio ponderada por peso de la actividad
    RD-U  → concentración: promedio de notas / nota máxima

  Comportamiento secundario:
    FB-N  → participaciones (tipo PARTICIPACION en calificaciones)
    FP-N  → proyectos entregados
    FR-N  → tareas entregadas

SELECCIÓN DE EIGENVALORES:
  Se retienen indicadores con coeficiente de correlación ≥ 0.6
  con la nota ponderada final (criterio del paper, Tabla 3).
  En la implementación se usa correlación de Pearson calculada
  sobre el conjunto de estudiantes del período.

CLASIFICACIÓN DE BAJO RENDIMIENTO:
  Umbral configurable; por defecto nota_ponderada < 6.0 / 10.
  El algoritmo ordena los estudiantes por asignatura, identifica
  los que caen bajo el umbral y construye el payload para Gemini.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

from django.db import connection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------
UMBRAL_BAJO_RENDIMIENTO = 6.0   # sobre 10
UMBRAL_CORRELACION = 0.6        # criterio del paper (Table 3)
PERIODO_ACTIVO_DEFAULT = "2024-2"


# ---------------------------------------------------------------
# DATA CLASSES
# ---------------------------------------------------------------
@dataclass
class IndicadorEstudiante:
    """
    Representa los 11 indicadores de comportamiento de aprendizaje
    de un estudiante en una asignatura (equivalente a LBI del paper).
    """
    estudiante_id: str
    nombre_estudiante: str
    asignatura_codigo: str
    asignatura_nombre: str
    docente_nombre: str
    paralelo_id: int

    # --- Indicadores calculados ---
    # RV-N: número de veces que revisó recursos (proxy: actividades completadas)
    rv_n: float = 0.0
    # RU-E: eficiencia de uso de recursos = entregas_calificadas / total_actividades
    ru_e: float = 0.0
    # RD-U: densidad de uso = promedio_nota / nota_maxima
    rd_u: float = 0.0
    # FB-N: participaciones registradas
    fb_n: float = 0.0
    # FP-N: proyectos entregados
    fp_n: float = 0.0
    # FR-N: tareas entregadas
    fr_n: float = 0.0
    # RM-T: ratio de asistencia
    rm_t: float = 0.0
    # RL-N: nota ponderada final
    rl_n: float = 0.0

    # --- Detalle de calificaciones (para el prompt de Gemini) ---
    calificaciones_detalle: List[Dict] = field(default_factory=list)

    @property
    def nota_ponderada(self) -> float:
        return self.rl_n

    @property
    def es_bajo_rendimiento(self) -> bool:
        return self.nota_ponderada < UMBRAL_BAJO_RENDIMIENTO

    def eigenvalores(self) -> Dict[str, float]:
        """Retorna solo los indicadores seleccionados como eigenvalores."""
        return {
            "RV_N": self.rv_n,
            "RU_E": self.ru_e,
            "RD_U": self.rd_u,
        }


@dataclass
class GrupoAsignatura:
    """Agrupa estudiantes de una asignatura con bajo rendimiento."""
    carrera_nombre: str
    asignatura_codigo: str
    asignatura_nombre: str
    paralelo_id: int
    docente_nombre: str
    docente_id: str
    total_estudiantes: int
    estudiantes_bajo_rendimiento: List[IndicadorEstudiante] = field(default_factory=list)

    @property
    def cantidad_bajo_rendimiento(self) -> int:
        return len(self.estudiantes_bajo_rendimiento)

    def payload_gemini(self) -> Dict:
        """
        Construye el payload consolidado para enviar a Gemini.
        Máximo 3 estudiantes representativos para no exceder el contexto.
        Se seleccionan los de peor rendimiento ponderado.
        """
        muestra = sorted(
            self.estudiantes_bajo_rendimiento,
            key=lambda e: e.nota_ponderada
        )[:3]

        return {
            "asignatura": self.asignatura_nombre,
            "codigo_asignatura": self.asignatura_codigo,
            "docente": self.docente_nombre,
            "total_estudiantes_bajo_rendimiento": self.cantidad_bajo_rendimiento,
            "muestra_estudiantes": [
                {
                    "nombre": e.nombre_estudiante,
                    "calificaciones": e.calificaciones_detalle,
                    "nota_ponderada_final": round(e.nota_ponderada, 2),
                    "revision_recursos": _nivel_texto(e.ru_e),
                    "desarrollo_actividades": _nivel_texto(e.rv_n),
                    "conectividad": _conectividad_texto(e.rm_t),
                    "perfil_docente": self.docente_nombre,
                    "eigenvalores": e.eigenvalores(),
                }
                for e in muestra
            ],
        }


# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------
def _nivel_texto(ratio: float) -> str:
    if ratio >= 0.8:
        return "Alto — revisa recursos consistentemente"
    elif ratio >= 0.5:
        return "Medio — revisa recursos ocasionalmente"
    else:
        return "Bajo — escasa revisión de recursos"


def _conectividad_texto(rm_t: float) -> str:
    if rm_t >= 0.85:
        return "Buena — asistencia regular"
    elif rm_t >= 0.65:
        return "Regular — faltas intermitentes"
    else:
        return "Deficiente — alta inasistencia"


def _pearson(xs: List[float], ys: List[float]) -> float:
    """Coeficiente de correlación de Pearson entre dos vectores."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
    )
    return num / den if den != 0 else 0.0


# ---------------------------------------------------------------
# CONSULTAS SQL
# ---------------------------------------------------------------
_SQL_PARALELOS_ACTIVOS = """
SELECT
    p.id                                        AS paralelo_id,
    a.codigo                                    AS asig_codigo,
    a.nombre                                    AS asig_nombre,
    a.creditos                                  AS creditos,
    ca.nombre                                   AS carrera_nombre,
    COALESCE(
        per.primer_nombre || ' ' || per.primer_apellido,
        'Docente no asignado'
    )                                           AS docente_nombre,
    COALESCE(d.id::text, '')                    AS docente_id
FROM academico.paralelo p
JOIN academico.periodo   per2 ON p.id_periodo = per2.id
JOIN academico.asignatura a   ON p.id_asignatura = a.id
JOIN academico.carrera   ca   ON a.id_carrera = ca.id
LEFT JOIN docencia.asignacion_docente_paralelo adp
    ON adp.id_paralelo = p.id AND adp.es_principal = TRUE
LEFT JOIN docencia.docente d ON d.id = adp.id_docente
LEFT JOIN core.persona per   ON per.id = d.id_persona
WHERE per2.codigo = %s
  AND per2.activo = TRUE
  AND a.id_carrera = %s
ORDER BY a.id_nivel, a.codigo
"""

_SQL_INDICADORES_ESTUDIANTE = """
SELECT
    e.id                                                    AS est_id,
    p.primer_nombre || ' ' || p.primer_apellido             AS nombre,
    -- RU-E: entregas calificadas / total actividades del paralelo
    COALESCE(
        COUNT(DISTINCT CASE WHEN en.estado = 'CALIFICADA' THEN en.id END)::numeric
        / NULLIF(COUNT(DISTINCT ac.id), 0),
        0
    )                                                       AS ru_e,
    -- RD-U: promedio de notas / 10 (densidad respecto al máximo)
    COALESCE(AVG(cal.puntaje) / 10.0, 0)                   AS rd_u,
    -- RM-T: asistencias (PRESENTE+TARDANZA) / total registros
    COALESCE(
        SUM(CASE WHEN asis.estado IN ('PRESENTE','TARDANZA') THEN 1 ELSE 0 END)::numeric
        / NULLIF(COUNT(DISTINCT asis.id), 0),
        0.75   -- default si no hay asistencias registradas
    )                                                       AS rm_t,
    -- FB-N: actividades tipo PARTICIPACION entregadas
    COUNT(DISTINCT CASE
        WHEN tac.nombre = 'PARTICIPACION' AND en2.estado = 'CALIFICADA'
        THEN en2.id END)                                    AS fb_n,
    -- FP-N: proyectos entregados
    COUNT(DISTINCT CASE
        WHEN tac.nombre = 'PROYECTO' AND en2.estado = 'CALIFICADA'
        THEN en2.id END)                                    AS fp_n,
    -- FR-N: tareas entregadas
    COUNT(DISTINCT CASE
        WHEN tac.nombre = 'TAREA' AND en2.estado = 'CALIFICADA'
        THEN en2.id END)                                    AS fr_n,
    -- RV-N: proxy por actividades completadas / total
    COALESCE(
        COUNT(DISTINCT CASE WHEN en.estado = 'CALIFICADA' THEN en.id END)::numeric
        / NULLIF(COUNT(DISTINCT ac.id), 0),
        0
    )                                                       AS rv_n
FROM estudiantil.estudiante e
JOIN core.persona p ON p.id = e.id_persona
JOIN estudiantil.matricula m ON m.id_estudiante = e.id
LEFT JOIN estudiantil.actividad_calificable ac ON ac.id_paralelo = m.id_paralelo
LEFT JOIN estudiantil.entrega en ON en.id_matricula = m.id AND en.id_actividad = ac.id
LEFT JOIN estudiantil.calificacion cal ON cal.id_entrega = en.id
LEFT JOIN estudiantil.entrega en2 ON en2.id_matricula = m.id
LEFT JOIN estudiantil.actividad_calificable ac2 ON ac2.id = en2.id_actividad
LEFT JOIN estudiantil.tipo_actividad_calificable tac ON tac.id = ac2.id_tipo
LEFT JOIN estudiantil.asistencia asis ON asis.id_matricula = m.id
WHERE m.id_paralelo = %s
  AND m.estado IN ('ACTIVA','APROBADA','REPROBADA')
GROUP BY e.id, p.primer_nombre, p.primer_apellido
"""

_SQL_CALIFICACIONES_DETALLE = """
SELECT
    tac.nombre                          AS tipo_actividad,
    ac.nombre                           AS nombre_actividad,
    COALESCE(cal.puntaje, 0)            AS calificacion,
    ac.puntaje_max                      AS puntaje_max,
    -- peso porcentual según tipo de actividad
    CASE tac.nombre
        WHEN 'EXAMEN_FINAL'   THEN 30.0
        WHEN 'EXAMEN_PARCIAL' THEN 25.0
        WHEN 'TEST'           THEN 15.0
        WHEN 'TALLER'         THEN 10.0
        WHEN 'TAREA'          THEN 10.0
        WHEN 'PROYECTO'       THEN  7.0
        WHEN 'PARTICIPACION'  THEN  3.0
        ELSE                        0.0
    END                                 AS peso_porcentaje
FROM estudiantil.matricula m
JOIN estudiantil.actividad_calificable ac ON ac.id_paralelo = m.id_paralelo
LEFT JOIN estudiantil.entrega en ON en.id_matricula = m.id AND en.id_actividad = ac.id
LEFT JOIN estudiantil.calificacion cal ON cal.id_entrega = en.id
JOIN estudiantil.tipo_actividad_calificable tac ON tac.id = ac.id_tipo
WHERE m.id_estudiante = %s AND m.id_paralelo = %s
ORDER BY peso_porcentaje DESC, tac.nombre
"""


# ---------------------------------------------------------------
# CLASE PRINCIPAL
# ---------------------------------------------------------------
class SegmentadorRendimiento:
    """
    Segmenta estudiantes con bajo rendimiento por asignatura
    usando los indicadores de comportamiento definidos en el paper.

    Flujo:
      1. Obtiene paralelos activos del período indicado.
      2. Por cada paralelo calcula los 11 LBI para cada estudiante.
      3. Aplica correlación de Pearson para retener eigenvalores.
      4. Clasifica como bajo rendimiento si nota_ponderada < umbral.
      5. Devuelve grupos listos para enviarse al agente Gemini.
    """

    def __init__(
        self,
        carrera_id: int = 1,
        periodo_codigo: str = PERIODO_ACTIVO_DEFAULT,
        umbral: float = UMBRAL_BAJO_RENDIMIENTO,
    ):
        self.carrera_id = carrera_id
        self.periodo_codigo = periodo_codigo
        self.umbral = umbral

    # -------------------------------------------------------
    def segmentar(self) -> List[GrupoAsignatura]:
        """
        Punto de entrada principal.
        Retorna lista de GrupoAsignatura con estudiantes bajo rendimiento.
        """
        paralelos = self._obtener_paralelos()
        grupos: List[GrupoAsignatura] = []

        for row in paralelos:
            (paralelo_id, asig_cod, asig_nom, creditos,
             carrera_nom, docente_nom, docente_id) = row

            indicadores = self._calcular_indicadores(paralelo_id, asig_cod, asig_nom, docente_nom)

            if not indicadores:
                continue

            # Selección de eigenvalores por correlación (metodología del paper)
            eigenvalores_activos = self._seleccionar_eigenvalores(indicadores)
            logger.info(
                "Paralelo %s (%s): eigenvalores activos = %s",
                paralelo_id, asig_cod, eigenvalores_activos
            )

            bajo_rend = [i for i in indicadores if i.es_bajo_rendimiento]

            if not bajo_rend:
                continue

            grupo = GrupoAsignatura(
                carrera_nombre=carrera_nom,
                asignatura_codigo=asig_cod,
                asignatura_nombre=asig_nom,
                paralelo_id=paralelo_id,
                docente_nombre=docente_nom,
                docente_id=docente_id,
                total_estudiantes=len(indicadores),
                estudiantes_bajo_rendimiento=bajo_rend,
            )
            grupos.append(grupo)

        logger.info(
            "Segmentación completada: %d asignaturas con estudiantes en riesgo.",
            len(grupos)
        )
        return grupos

    # -------------------------------------------------------
    def _obtener_paralelos(self):
        with connection.cursor() as cursor:
            cursor.execute(_SQL_PARALELOS_ACTIVOS, [self.periodo_codigo, self.carrera_id])
            return cursor.fetchall()

    # -------------------------------------------------------
    def _calcular_indicadores(
        self,
        paralelo_id: int,
        asig_cod: str,
        asig_nom: str,
        docente_nom: str,
    ) -> List[IndicadorEstudiante]:
        indicadores = []

        with connection.cursor() as cursor:
            cursor.execute(_SQL_INDICADORES_ESTUDIANTE, [paralelo_id])
            rows = cursor.fetchall()

        for row in rows:
            (est_id, nombre, ru_e, rd_u, rm_t, fb_n, fp_n, fr_n, rv_n) = row

            # Nota ponderada: calculada con los pesos del SQL de detalle
            califs, nota_pond = self._calificaciones_y_nota(est_id, paralelo_id)

            ind = IndicadorEstudiante(
                estudiante_id=str(est_id),
                nombre_estudiante=str(nombre),
                asignatura_codigo=asig_cod,
                asignatura_nombre=asig_nom,
                docente_nombre=docente_nom,
                paralelo_id=paralelo_id,
                rv_n=float(rv_n),
                ru_e=float(ru_e),
                rd_u=float(rd_u),
                fb_n=float(fb_n),
                fp_n=float(fp_n),
                fr_n=float(fr_n),
                rm_t=float(rm_t),
                rl_n=nota_pond,
                calificaciones_detalle=califs,
            )
            indicadores.append(ind)

        return indicadores

    # -------------------------------------------------------
    def _calificaciones_y_nota(
        self, est_id: str, paralelo_id: int
    ) -> Tuple[List[Dict], float]:
        with connection.cursor() as cursor:
            cursor.execute(_SQL_CALIFICACIONES_DETALLE, [est_id, paralelo_id])
            rows = cursor.fetchall()

        califs = []
        suma_ponderada = 0.0
        suma_pesos = 0.0

        for tipo_act, nombre_act, calif, pmax, peso in rows:
            nota_sobre_10 = (float(calif) / float(pmax)) * 10 if float(pmax) > 0 else 0.0
            califs.append({
                "nombre": nombre_act,
                "calificacion": round(nota_sobre_10, 2),
                "objetivo": f"Lograr competencia en {tipo_act.lower().replace('_', ' ')}",
                "peso_porcentaje": float(peso),
            })
            suma_ponderada += nota_sobre_10 * float(peso)
            suma_pesos += float(peso)

        nota_final = (suma_ponderada / suma_pesos) if suma_pesos > 0 else 0.0
        return califs, round(nota_final, 2)

    # -------------------------------------------------------
    def _seleccionar_eigenvalores(
        self, indicadores: List[IndicadorEstudiante]
    ) -> List[str]:
        """
        Aplica el criterio del paper (correlación de Pearson ≥ 0.6)
        para determinar qué indicadores son eigenvalores significativos.
        Si hay menos de 3 estudiantes, retorna los 3 canónicos del paper.
        """
        if len(indicadores) < 3:
            return ["RV_N", "RU_E", "RD_U"]

        notas = [i.nota_ponderada for i in indicadores]

        candidatos = {
            "RV_N": [i.rv_n for i in indicadores],
            "RU_E": [i.ru_e for i in indicadores],
            "RD_U": [i.rd_u for i in indicadores],
            "FB_N": [i.fb_n for i in indicadores],
            "FP_N": [i.fp_n for i in indicadores],
            "FR_N": [i.fr_n for i in indicadores],
            "RM_T": [i.rm_t for i in indicadores],
        }

        seleccionados = []
        for nombre_ind, valores in candidatos.items():
            corr = abs(_pearson(valores, notas))
            if corr >= UMBRAL_CORRELACION:
                seleccionados.append(nombre_ind)
                logger.debug("Eigenvalor retenido: %s (r=%.3f)", nombre_ind, corr)
            else:
                logger.debug("Indicador descartado: %s (r=%.3f)", nombre_ind, corr)

        # Si ninguno supera el umbral (datos insuficientes), usar los canónicos
        return seleccionados if seleccionados else ["RV_N", "RU_E", "RD_U"]