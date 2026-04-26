-- =============================================================================
-- INNOTECH - BASE DE DATOS COMPLETA NORMALIZADA
-- Universidad Bolivariana del Ecuador
-- PostgreSQL 16
-- Diseño orientado a los 17 sistemas de titulación de Ingeniería en Sistemas Inteligentes
-- =============================================================================

-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- búsqueda de similitud de texto (plagio)
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- =============================================================================
-- ESQUEMAS
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS core;           -- Entidades base compartidas
CREATE SCHEMA IF NOT EXISTS academico;      -- Planificación académica
CREATE SCHEMA IF NOT EXISTS docencia;       -- Gestión docente y evaluación
CREATE SCHEMA IF NOT EXISTS estudiantil;    -- Seguimiento estudiantil
CREATE SCHEMA IF NOT EXISTS admision;       -- Admisión y orientación vocacional
CREATE SCHEMA IF NOT EXISTS talento;        -- Talento humano y concursos
CREATE SCHEMA IF NOT EXISTS practicas;      -- Prácticas preprofesionales / internado
CREATE SCHEMA IF NOT EXISTS ia;             -- Resultados y logs de modelos IA

SET search_path = core, academico, docencia, estudiantil, admision, talento, practicas, ia, public;

-- =============================================================================
-- ESQUEMA CORE - Entidades base
-- =============================================================================

-- Catálogos generales
CREATE TABLE core.tipo_identificacion (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    codigo          VARCHAR(10) NOT NULL UNIQUE,
    descripcion     VARCHAR(60) NOT NULL
);
INSERT INTO core.tipo_identificacion(codigo, descripcion) VALUES
    ('CI','Cédula de Identidad'),('PASAPORTE','Pasaporte'),('RUC','RUC');

CREATE TABLE core.genero (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    codigo          VARCHAR(10) NOT NULL UNIQUE,
    descripcion     VARCHAR(40) NOT NULL
);
INSERT INTO core.genero(codigo, descripcion) VALUES
    ('M','Masculino'),('F','Femenino'),('NB','No binario'),('ND','No declara');

CREATE TABLE core.estado_civil (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    codigo          VARCHAR(15) NOT NULL UNIQUE,
    descripcion     VARCHAR(40) NOT NULL
);
INSERT INTO core.estado_civil(codigo, descripcion) VALUES
    ('SOLTERO','Soltero/a'),('CASADO','Casado/a'),('DIVORCIADO','Divorciado/a'),
    ('VIUDO','Viudo/a'),('UNION_LIBRE','Unión libre');

CREATE TABLE core.provincia (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(60) NOT NULL,
    codigo          VARCHAR(5) NOT NULL UNIQUE
);

CREATE TABLE core.canton (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(80) NOT NULL,
    id_provincia    SMALLINT NOT NULL REFERENCES core.provincia(id),
    codigo          VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE core.parroquia (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(80) NOT NULL,
    id_canton       SMALLINT NOT NULL REFERENCES core.canton(id),
    tipo            VARCHAR(10) CHECK (tipo IN ('URBANA','RURAL')),
    latitud         NUMERIC(9,6),
    longitud        NUMERIC(9,6)
);

-- Persona: tabla raíz de estudiantes, docentes, aspirantes, postulantes
CREATE TABLE core.persona (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo_identificacion SMALLINT NOT NULL REFERENCES core.tipo_identificacion(id),
    numero_identificacion VARCHAR(20) NOT NULL,
    primer_nombre       VARCHAR(60) NOT NULL,
    segundo_nombre      VARCHAR(60),
    primer_apellido     VARCHAR(60) NOT NULL,
    segundo_apellido    VARCHAR(60),
    fecha_nacimiento    DATE,
    id_genero           SMALLINT REFERENCES core.genero(id),
    id_estado_civil     SMALLINT REFERENCES core.estado_civil(id),
    email_personal      VARCHAR(120),
    email_institucional VARCHAR(120),
    telefono_movil      VARCHAR(15),
    telefono_fijo       VARCHAR(15),
    id_parroquia        SMALLINT REFERENCES core.parroquia(id),
    direccion_detalle   VARCHAR(200),
    foto_url            VARCHAR(255),
    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tipo_identificacion, numero_identificacion)
);
CREATE INDEX idx_persona_identificacion ON core.persona(numero_identificacion);
CREATE INDEX idx_persona_nombre ON core.persona USING gin(to_tsvector('spanish', primer_apellido || ' ' || primer_nombre));

-- Usuarios del sistema
CREATE TABLE core.usuario (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_persona      UUID NOT NULL REFERENCES core.persona(id),
    username        VARCHAR(60) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_acceso   TIMESTAMPTZ,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE core.rol (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(60) NOT NULL UNIQUE,
    descripcion     VARCHAR(200)
);
INSERT INTO core.rol(nombre) VALUES
    ('ADMIN'),('DOCENTE'),('ESTUDIANTE'),('COORDINADOR'),('BIENESTAR'),
    ('TALENTO_HUMANO'),('ADMISION'),('PRACTICAS');

CREATE TABLE core.usuario_rol (
    id_usuario  UUID NOT NULL REFERENCES core.usuario(id),
    id_rol      SMALLINT NOT NULL REFERENCES core.rol(id),
    desde       DATE NOT NULL DEFAULT CURRENT_DATE,
    hasta       DATE,
    PRIMARY KEY (id_usuario, id_rol)
);

-- =============================================================================
-- ESQUEMA ACADEMICO
-- =============================================================================

CREATE TABLE academico.facultad (
    id          SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre      VARCHAR(120) NOT NULL,
    codigo      VARCHAR(10) NOT NULL UNIQUE,
    activo      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE academico.carrera (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_facultad     SMALLINT NOT NULL REFERENCES academico.facultad(id),
    nombre          VARCHAR(120) NOT NULL,
    codigo          VARCHAR(20) NOT NULL UNIQUE,
    modalidad       VARCHAR(20) CHECK (modalidad IN ('PRESENCIAL','HIBRIDA','ONLINE')),
    duracion_ciclos SMALLINT NOT NULL DEFAULT 8,
    titulo_otorga   VARCHAR(120),
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE academico.periodo (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(40) NOT NULL,
    codigo          VARCHAR(10) NOT NULL UNIQUE,   -- Ej: 2024-1
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    en_curso        BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_periodo_fechas CHECK (fecha_fin > fecha_inicio)
);

-- Malla curricular
CREATE TABLE academico.nivel (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    numero  SMALLINT NOT NULL,   -- 1..n semestre/ciclo
    nombre  VARCHAR(20)          -- Primer Nivel, etc.
);

CREATE TABLE academico.asignatura (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_carrera      SMALLINT NOT NULL REFERENCES academico.carrera(id),
    id_nivel        SMALLINT NOT NULL REFERENCES academico.nivel(id),
    codigo          VARCHAR(20) NOT NULL UNIQUE,
    nombre          VARCHAR(120) NOT NULL,
    creditos        SMALLINT NOT NULL DEFAULT 3,
    horas_teoria    SMALLINT NOT NULL DEFAULT 2,
    horas_practica  SMALLINT NOT NULL DEFAULT 2,
    horas_autonomo  SMALLINT NOT NULL DEFAULT 2,
    modalidad       VARCHAR(20) CHECK (modalidad IN ('PRESENCIAL','VIRTUAL','HIBRIDA')),
    requiere_lab    BOOLEAN NOT NULL DEFAULT FALSE,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE academico.prerequisito (
    id_asignatura   SMALLINT NOT NULL REFERENCES academico.asignatura(id),
    id_prerequisito SMALLINT NOT NULL REFERENCES academico.asignatura(id),
    PRIMARY KEY (id_asignatura, id_prerequisito),
    CONSTRAINT chk_no_autoreferencia CHECK (id_asignatura <> id_prerequisito)
);

-- Espacios físicos (Sistema 4)
CREATE TABLE academico.tipo_espacio (
    id          SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre      VARCHAR(60) NOT NULL UNIQUE   -- AULA, LABORATORIO, AUDITORIO, etc.
);
INSERT INTO academico.tipo_espacio(nombre) VALUES
    ('AULA'),('LABORATORIO'),('AUDITORIO'),('SALA_REUNIONES'),('SALA_VIDEOCONFERENCIA');

CREATE TABLE academico.edificio (
    id          SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre      VARCHAR(60) NOT NULL,
    codigo      VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE academico.espacio_fisico (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_edificio     SMALLINT NOT NULL REFERENCES academico.edificio(id),
    id_tipo_espacio SMALLINT NOT NULL REFERENCES academico.tipo_espacio(id),
    codigo          VARCHAR(20) NOT NULL UNIQUE,
    nombre          VARCHAR(80) NOT NULL,
    capacidad       SMALLINT NOT NULL,
    tiene_proyector BOOLEAN NOT NULL DEFAULT FALSE,
    tiene_internet  BOOLEAN NOT NULL DEFAULT FALSE,
    tiene_ac        BOOLEAN NOT NULL DEFAULT FALSE,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

-- Paralelos (Sistema 3 y 4)
CREATE TABLE academico.paralelo (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_asignatura   SMALLINT NOT NULL REFERENCES academico.asignatura(id),
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    codigo          VARCHAR(5) NOT NULL,   -- A, B, C
    capacidad_max   SMALLINT NOT NULL DEFAULT 35,
    UNIQUE (id_asignatura, id_periodo, codigo)
);

-- Horario de paralelos (Sistema 3 y 4)
CREATE TABLE academico.dia_semana (
    id      SMALLINT PRIMARY KEY,
    nombre  VARCHAR(12) NOT NULL
);
INSERT INTO academico.dia_semana VALUES (1,'Lunes'),(2,'Martes'),(3,'Miércoles'),(4,'Jueves'),(5,'Viernes'),(6,'Sábado');

CREATE TABLE academico.franja_horaria (
    id              SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    hora_inicio     TIME NOT NULL,
    hora_fin        TIME NOT NULL,
    CONSTRAINT chk_franja CHECK (hora_fin > hora_inicio)
);

CREATE TABLE academico.horario_paralelo (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_dia          SMALLINT NOT NULL REFERENCES academico.dia_semana(id),
    id_franja       SMALLINT NOT NULL REFERENCES academico.franja_horaria(id),
    id_espacio      SMALLINT REFERENCES academico.espacio_fisico(id),
    tipo            VARCHAR(15) CHECK (tipo IN ('TEORIA','PRACTICA','LABORATORIO')),
    UNIQUE (id_dia, id_franja, id_espacio)   -- sin colisión de espacio
);

-- Reserva de espacio (Sistema 4)
CREATE TABLE academico.reserva_espacio (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_espacio      SMALLINT NOT NULL REFERENCES academico.espacio_fisico(id),
    id_solicitante  UUID NOT NULL REFERENCES core.persona(id),
    fecha           DATE NOT NULL,
    hora_inicio     TIME NOT NULL,
    hora_fin        TIME NOT NULL,
    motivo          VARCHAR(200),
    estado          VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE','APROBADA','RECHAZADA','CANCELADA')),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reserva_horas CHECK (hora_fin > hora_inicio)
);

-- =============================================================================
-- ESQUEMA DOCENCIA - Docentes
-- =============================================================================

CREATE TABLE docencia.nivel_formacion (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre  VARCHAR(60) NOT NULL UNIQUE   -- TERCER_NIVEL, MAESTRIA, DOCTORADO, etc.
);
INSERT INTO docencia.nivel_formacion(nombre) VALUES
    ('TERCER_NIVEL'),('ESPECIALIDAD'),('MAESTRIA'),('DOCTORADO'),('POSTDOCTORADO');

CREATE TABLE docencia.tipo_docente (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre  VARCHAR(60) NOT NULL UNIQUE   -- TITULAR, OCASIONAL, INVITADO, etc.
);
INSERT INTO docencia.tipo_docente(nombre) VALUES
    ('TITULAR'),('OCASIONAL'),('INVITADO'),('HONORARIO');

CREATE TABLE docencia.docente (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_persona          UUID NOT NULL UNIQUE REFERENCES core.persona(id),
    id_tipo             SMALLINT NOT NULL REFERENCES docencia.tipo_docente(id),
    id_nivel_formacion  SMALLINT REFERENCES docencia.nivel_formacion(id),
    id_carrera_adscrito SMALLINT REFERENCES academico.carrera(id),
    fecha_ingreso       DATE,
    dedicacion          VARCHAR(20) CHECK (dedicacion IN ('TIEMPO_COMPLETO','MEDIO_TIEMPO','HORA_CLASE')),
    horas_max_semana    SMALLINT DEFAULT 40,
    activo              BOOLEAN NOT NULL DEFAULT TRUE
);

-- Títulos académicos del docente (Sistema 16)
CREATE TABLE docencia.titulo_docente (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente          UUID NOT NULL REFERENCES docencia.docente(id),
    id_nivel_formacion  SMALLINT NOT NULL REFERENCES docencia.nivel_formacion(id),
    titulo              VARCHAR(150) NOT NULL,
    institucion         VARCHAR(150) NOT NULL,
    pais                VARCHAR(60),
    anio_obtencion      SMALLINT,
    es_principal        BOOLEAN NOT NULL DEFAULT FALSE,
    registro_senescyt   VARCHAR(30),
    documento_url       VARCHAR(255)
);

-- Experiencia profesional docente (Sistema 16)
CREATE TABLE docencia.experiencia_profesional (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    empresa         VARCHAR(150) NOT NULL,
    cargo           VARCHAR(120) NOT NULL,
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE,
    descripcion     TEXT,
    tipo            VARCHAR(20) CHECK (tipo IN ('DOCENCIA','PROFESIONAL'))
);

-- Capacitaciones docente (Sistema 15 y 16)
CREATE TABLE docencia.capacitacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    nombre          VARCHAR(200) NOT NULL,
    institucion     VARCHAR(150),
    horas           SMALLINT NOT NULL,
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE,
    tipo            VARCHAR(30) CHECK (tipo IN ('CURSO','TALLER','SEMINARIO','CONGRESO','OTRO')),
    area_tematica   VARCHAR(120),
    certificado_url VARCHAR(255)
);

-- Publicaciones científicas (Sistema 16)
CREATE TABLE docencia.publicacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    titulo          VARCHAR(300) NOT NULL,
    revista         VARCHAR(200),
    doi             VARCHAR(100),
    anio            SMALLINT NOT NULL,
    tipo            VARCHAR(30) CHECK (tipo IN ('ARTICULO','LIBRO','CAPITULO','CONFERENCE')),
    cuartil         VARCHAR(5),   -- Q1, Q2, Q3, Q4
    indexacion      VARCHAR(30),  -- SCOPUS, WOS, LATINDEX, etc.
    url             VARCHAR(255)
);

-- Ponencias (Sistema 16)
CREATE TABLE docencia.ponencia (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    titulo          VARCHAR(300) NOT NULL,
    evento          VARCHAR(200) NOT NULL,
    ciudad          VARCHAR(80),
    pais            VARCHAR(60),
    fecha           DATE NOT NULL,
    tipo            VARCHAR(20) CHECK (tipo IN ('NACIONAL','INTERNACIONAL')),
    url_memoria     VARCHAR(255)
);

-- Proyectos de investigación (Sistema 16)
CREATE TABLE docencia.proyecto_investigacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(200) NOT NULL,
    codigo          VARCHAR(30),
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE,
    estado          VARCHAR(20) CHECK (estado IN ('EN_CURSO','FINALIZADO','SUSPENDIDO')),
    financiamiento  VARCHAR(100),
    descripcion     TEXT
);

CREATE TABLE docencia.docente_proyecto (
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    id_proyecto     INTEGER NOT NULL REFERENCES docencia.proyecto_investigacion(id),
    rol             VARCHAR(40),   -- DIRECTOR, CO-INVESTIGADOR, etc.
    PRIMARY KEY (id_docente, id_proyecto)
);

-- Proyectos de vinculación (Sistema 16)
CREATE TABLE docencia.proyecto_vinculacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(200) NOT NULL,
    comunidad       VARCHAR(150),
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE,
    estado          VARCHAR(20) CHECK (estado IN ('EN_CURSO','FINALIZADO','SUSPENDIDO'))
);

CREATE TABLE docencia.docente_vinculacion (
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    id_proyecto     INTEGER NOT NULL REFERENCES docencia.proyecto_vinculacion(id),
    rol             VARCHAR(40),
    PRIMARY KEY (id_docente, id_proyecto)
);

-- Disponibilidad docente para asignación (Sistema 3)
CREATE TABLE docencia.disponibilidad_docente (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    id_dia          SMALLINT NOT NULL REFERENCES academico.dia_semana(id),
    id_franja       SMALLINT NOT NULL REFERENCES academico.franja_horaria(id),
    disponible      BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (id_docente, id_periodo, id_dia, id_franja)
);

-- Asignación de docente a paralelo (Sistema 3)
CREATE TABLE docencia.asignacion_docente_paralelo (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    tipo            VARCHAR(15) CHECK (tipo IN ('TEORIA','PRACTICA','AMBAS')),
    es_principal    BOOLEAN NOT NULL DEFAULT TRUE,  -- para asignaturas con >1 docente en serie
    estado          VARCHAR(20) NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA','REEMPLAZO_VACACION','REEMPLAZO_EVENTUAL','FINALIZADA')),
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE,
    UNIQUE (id_docente, id_paralelo, tipo)
);

-- Plan temático de la asignatura en el paralelo (Sistemas 5,6,7,9,10,11,12,13)
CREATE TABLE docencia.plan_tematico (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    estado          VARCHAR(20) NOT NULL DEFAULT 'BORRADOR'
                    CHECK (estado IN ('BORRADOR','PUBLICADO','CERRADO')),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE docencia.unidad_tematica (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_plan         INTEGER NOT NULL REFERENCES docencia.plan_tematico(id),
    numero          SMALLINT NOT NULL,
    titulo          VARCHAR(200) NOT NULL,
    descripcion     TEXT,
    semanas         SMALLINT NOT NULL DEFAULT 2,
    UNIQUE (id_plan, numero)
);

CREATE TABLE docencia.tema (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_unidad       INTEGER NOT NULL REFERENCES docencia.unidad_tematica(id),
    numero          SMALLINT NOT NULL,
    titulo          VARCHAR(200) NOT NULL,
    descripcion     TEXT,
    UNIQUE (id_unidad, numero)
);

CREATE TABLE docencia.objetivo_especifico (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_unidad       INTEGER NOT NULL REFERENCES docencia.unidad_tematica(id),
    descripcion     TEXT NOT NULL,
    resultado_esperado TEXT
);

CREATE TABLE docencia.resultado_aprendizaje (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_objetivo     INTEGER NOT NULL REFERENCES docencia.objetivo_especifico(id),
    descripcion     TEXT NOT NULL,
    nivel_bloom     VARCHAR(20) CHECK (nivel_bloom IN ('RECORDAR','COMPRENDER','APLICAR','ANALIZAR','EVALUAR','CREAR'))
);

-- Recursos didácticos (Sistemas 5 y 6)
CREATE TABLE docencia.tipo_recurso (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre  VARCHAR(60) NOT NULL UNIQUE  -- VIDEO, PDF, PRESENTACION, ENLACE, EJERCICIO
);
INSERT INTO docencia.tipo_recurso(nombre) VALUES
    ('VIDEO'),('PDF'),('PRESENTACION'),('ENLACE_WEB'),('EJERCICIO'),('IMAGEN'),('AUDIO');

CREATE TABLE docencia.recurso_aprendizaje (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_tema         INTEGER REFERENCES docencia.tema(id),
    id_unidad       INTEGER REFERENCES docencia.unidad_tematica(id),
    id_tipo         SMALLINT NOT NULL REFERENCES docencia.tipo_recurso(id),
    titulo          VARCHAR(200) NOT NULL,
    descripcion     TEXT,
    url             VARCHAR(500),
    contenido       TEXT,           -- si es recurso generado por IA
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    prompt_usado    TEXT,
    id_docente      UUID REFERENCES docencia.docente(id),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Instrumento de evaluación (Sistema 7)
CREATE TABLE docencia.instrumento_evaluacion (
    id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo INTEGER NOT NULL REFERENCES academico.paralelo(id),
    nombre      VARCHAR(200) NOT NULL,
    tipo        VARCHAR(20) CHECK (tipo IN ('RUBRICA','LISTA_COTEJO','ESCALA','OTRO')),
    descripcion TEXT,
    puntaje_max NUMERIC(5,2) NOT NULL DEFAULT 10.00,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE docencia.item_evaluacion (
    id                      INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_instrumento          INTEGER NOT NULL REFERENCES docencia.instrumento_evaluacion(id),
    descripcion             VARCHAR(300) NOT NULL,
    puntaje_maximo          NUMERIC(5,2) NOT NULL,
    criterio_cumplimiento   TEXT,
    orden                   SMALLINT NOT NULL DEFAULT 1
);

-- Evaluación docente (Sistema 14 y 15)
CREATE TABLE docencia.criterio_evaluacion_docente (
    id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre      VARCHAR(120) NOT NULL,
    descripcion TEXT,
    peso        NUMERIC(5,2) NOT NULL,  -- % de peso en la evaluación final
    activo      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE docencia.evaluacion_docente (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    id_paralelo     INTEGER REFERENCES academico.paralelo(id),
    tipo_evaluacion VARCHAR(20) CHECK (tipo_evaluacion IN ('HETERO','AUTO','PARES','DIRECTIVOS')),
    puntaje_total   NUMERIC(5,2),
    observaciones   TEXT,
    fecha_evaluacion DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (id_docente, id_periodo, id_paralelo, tipo_evaluacion)
);

CREATE TABLE docencia.detalle_evaluacion_docente (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_evaluacion       INTEGER NOT NULL REFERENCES docencia.evaluacion_docente(id),
    id_criterio         INTEGER NOT NULL REFERENCES docencia.criterio_evaluacion_docente(id),
    puntaje             NUMERIC(5,2) NOT NULL,
    comentario          TEXT
);

-- Plan de capacitación (Sistema 15)
CREATE TABLE docencia.plan_capacitacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente      UUID NOT NULL REFERENCES docencia.docente(id),
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    estado          VARCHAR(20) DEFAULT 'GENERADO'
                    CHECK (estado IN ('GENERADO','APROBADO','EN_EJECUCION','COMPLETADO')),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE docencia.item_plan_capacitacion (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_plan             INTEGER NOT NULL REFERENCES docencia.plan_capacitacion(id),
    id_criterio         INTEGER NOT NULL REFERENCES docencia.criterio_evaluacion_docente(id),
    descripcion         VARCHAR(300) NOT NULL,
    tipo_actividad      VARCHAR(60),
    horas_estimadas     SMALLINT,
    prioridad           SMALLINT CHECK (prioridad BETWEEN 1 AND 5),
    peso_necesidad      NUMERIC(5,2)   -- calculado por IA
);

-- =============================================================================
-- ESQUEMA ESTUDIANTIL - Estudiantes y seguimiento
-- =============================================================================

CREATE TABLE estudiantil.estudiante (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_persona          UUID NOT NULL UNIQUE REFERENCES core.persona(id),
    id_carrera          SMALLINT NOT NULL REFERENCES academico.carrera(id),
    codigo_estudiante   VARCHAR(20) NOT NULL UNIQUE,
    fecha_ingreso       DATE NOT NULL,
    nivel_actual        SMALLINT,
    modalidad           VARCHAR(20) CHECK (modalidad IN ('PRESENCIAL','VIRTUAL','HIBRIDA')),
    estado              VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'
                        CHECK (estado IN ('ACTIVO','SUSPENDIDO','RETIRADO','GRADUADO','BECA')),
    beca                BOOLEAN NOT NULL DEFAULT FALSE,
    tipo_beca           VARCHAR(60)
);
CREATE INDEX idx_estudiante_codigo ON estudiantil.estudiante(codigo_estudiante);

-- Matrícula
CREATE TABLE estudiantil.matricula (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante   UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    fecha_matricula DATE NOT NULL DEFAULT CURRENT_DATE,
    estado          VARCHAR(20) NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA','RETIRADA','APROBADA','REPROBADA')),
    UNIQUE (id_estudiante, id_paralelo)
);
CREATE INDEX idx_matricula_estudiante ON estudiantil.matricula(id_estudiante);

-- Asistencia (Sistema 1)
CREATE TABLE estudiantil.asistencia (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_matricula    INTEGER NOT NULL REFERENCES estudiantil.matricula(id),
    fecha           DATE NOT NULL,
    hora_inicio     TIME NOT NULL,
    estado          VARCHAR(15) NOT NULL CHECK (estado IN ('PRESENTE','AUSENTE','TARDANZA','JUSTIFICADO')),
    justificacion   VARCHAR(300),
    registrado_por  UUID REFERENCES core.persona(id)
);
CREATE INDEX idx_asistencia_matricula ON estudiantil.asistencia(id_matricula, fecha);

-- Calificaciones (Sistemas 1, 5, 13, 14)
CREATE TABLE estudiantil.tipo_actividad_calificable (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre  VARCHAR(60) NOT NULL UNIQUE  -- TAREA, TALLER, TEST, EXAMEN, PROYECTO, PARTICIPACION
);
INSERT INTO estudiantil.tipo_actividad_calificable(nombre) VALUES
    ('TAREA'),('TALLER'),('TEST'),('EXAMEN_PARCIAL'),('EXAMEN_FINAL'),
    ('PROYECTO'),('PARTICIPACION'),('LECTION_INTERACTIVA');

CREATE TABLE estudiantil.actividad_calificable (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_tipo         SMALLINT NOT NULL REFERENCES estudiantil.tipo_actividad_calificable(id),
    id_tema         INTEGER REFERENCES docencia.tema(id),
    id_unidad       INTEGER REFERENCES docencia.unidad_tematica(id),
    nombre          VARCHAR(200) NOT NULL,
    descripcion     TEXT,
    fecha_asignacion DATE,
    fecha_entrega   DATE,
    puntaje_max     NUMERIC(5,2) NOT NULL DEFAULT 10.00,
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    id_instrumento  INTEGER REFERENCES docencia.instrumento_evaluacion(id),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE estudiantil.entrega (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_matricula        INTEGER NOT NULL REFERENCES estudiantil.matricula(id),
    id_actividad        INTEGER NOT NULL REFERENCES estudiantil.actividad_calificable(id),
    fecha_entrega       TIMESTAMPTZ,
    contenido_texto     TEXT,
    archivo_url         VARCHAR(500),
    estado              VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                        CHECK (estado IN ('PENDIENTE','ENTREGADA','CALIFICADA','TARDE')),
    UNIQUE (id_matricula, id_actividad)
);

CREATE TABLE estudiantil.calificacion (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_entrega          INTEGER NOT NULL UNIQUE REFERENCES estudiantil.entrega(id),
    puntaje             NUMERIC(5,2) NOT NULL,
    puntaje_ia          NUMERIC(5,2),       -- puntaje sugerido por IA (Sistema 7)
    calificado_por_ia   BOOLEAN NOT NULL DEFAULT FALSE,
    revisado_docente    BOOLEAN NOT NULL DEFAULT FALSE,
    observacion         TEXT,
    fecha_calificacion  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Detalle de calificación por ítem (Sistema 7)
CREATE TABLE estudiantil.calificacion_item (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_calificacion INTEGER NOT NULL REFERENCES estudiantil.calificacion(id),
    id_item         INTEGER NOT NULL REFERENCES docencia.item_evaluacion(id),
    puntaje         NUMERIC(5,2) NOT NULL,
    comentario      TEXT
);

-- Situación económica del estudiante (Sistema 1 y 17)
CREATE TABLE estudiantil.situacion_economica (
    id                      INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante           UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_periodo              SMALLINT NOT NULL REFERENCES academico.periodo(id),
    ingreso_familiar        NUMERIC(10,2),
    numero_miembros_hogar   SMALLINT,
    nivel_pobreza           VARCHAR(20) CHECK (nivel_pobreza IN ('EXTREMA','BAJA','MEDIA','ALTA')),
    tiene_bono_desarrollo   BOOLEAN NOT NULL DEFAULT FALSE,
    tiene_discapacidad      BOOLEAN NOT NULL DEFAULT FALSE,
    porcentaje_discapacidad SMALLINT CHECK (porcentaje_discapacidad BETWEEN 0 AND 100),
    trabaja                 BOOLEAN NOT NULL DEFAULT FALSE,
    horas_trabajo_semana    SMALLINT,
    actualizado_en          DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (id_estudiante, id_periodo)
);

-- Cargas familiares (Sistemas 1 y 17)
CREATE TABLE estudiantil.carga_familiar (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante   UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    parentesco      VARCHAR(30) NOT NULL,  -- HIJO, PADRE, MADRE, CONYUGUE, etc.
    edad            SMALLINT,
    es_dependiente  BOOLEAN NOT NULL DEFAULT TRUE
);

-- Pagos / cuotas (Sistema 1)
CREATE TABLE estudiantil.cuota_pago (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante   UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    numero_cuota    SMALLINT NOT NULL,
    valor           NUMERIC(10,2) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_pago      DATE,
    estado          VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE','PAGADA','VENCIDA','EXONERADA'))
);

-- =============================================================================
-- SISTEMA 1 - Predicción de deserción estudiantil
-- =============================================================================

CREATE TABLE estudiantil.modelo_riesgo_desercion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(100) NOT NULL,
    version         VARCHAR(20) NOT NULL,
    descripcion     TEXT,
    fecha_entrenamiento DATE,
    metricas        JSONB,   -- accuracy, recall, etc.
    activo          BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE estudiantil.alerta_desercion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante   UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    id_modelo       INTEGER REFERENCES estudiantil.modelo_riesgo_desercion(id),
    nivel_riesgo    VARCHAR(15) NOT NULL CHECK (nivel_riesgo IN ('BAJO','MEDIO','ALTO','CRITICO')),
    puntaje_riesgo  NUMERIC(5,4),     -- 0.0 a 1.0
    causas          JSONB,            -- factores más relevantes identificados
    recomendacion   TEXT,
    estado          VARCHAR(20) NOT NULL DEFAULT 'GENERADA'
                    CHECK (estado IN ('GENERADA','NOTIFICADA','ATENDIDA','CERRADA','FALSO_POSITIVO')),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atendido_por    UUID REFERENCES core.persona(id),
    atendido_en     TIMESTAMPTZ
);
CREATE INDEX idx_alerta_riesgo ON estudiantil.alerta_desercion(id_estudiante, id_periodo, nivel_riesgo);

CREATE TABLE estudiantil.semaforo_riesgo (
    id_alerta       INTEGER NOT NULL REFERENCES estudiantil.alerta_desercion(id),
    color           VARCHAR(10) NOT NULL CHECK (color IN ('VERDE','AMARILLO','NARANJA','ROJO')),
    factor          VARCHAR(60) NOT NULL,  -- CUOTAS, CALIFICACIONES, ASISTENCIA, SOCIOECONOMICO
    valor_actual    NUMERIC(10,4),
    umbral_alerta   NUMERIC(10,4),
    PRIMARY KEY (id_alerta, factor)
);

-- =============================================================================
-- SISTEMA 2 - Orientación vocacional
-- =============================================================================

CREATE TABLE admision.aspirante (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_persona      UUID NOT NULL UNIQUE REFERENCES core.persona(id),
    anio_graduacion SMALLINT,
    tipo_colegio    VARCHAR(30) CHECK (tipo_colegio IN ('FISCAL','PARTICULAR','FISCOMISIONAL','MUNICIPAL')),
    bachillerato    VARCHAR(80),   -- tipo de bachillerato
    promedio_bachillerato NUMERIC(4,2),
    fecha_registro  DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE admision.campo_interes (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre  VARCHAR(80) NOT NULL UNIQUE,   -- INGENIERIA, SALUD, ARTE, CIENCIAS_SOCIALES, etc.
    descripcion TEXT
);
INSERT INTO admision.campo_interes(nombre) VALUES
    ('INGENIERIA_Y_TECNOLOGIA'),('SALUD_Y_BIENESTAR'),('ARTES_Y_CULTURA'),
    ('CIENCIAS_SOCIALES'),('CIENCIAS_NATURALES'),('NEGOCIOS_Y_ADMINISTRACION'),
    ('EDUCACION'),('DERECHO');

CREATE TABLE admision.demanda_laboral_carrera (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_carrera      SMALLINT NOT NULL REFERENCES academico.carrera(id),
    anio            SMALLINT NOT NULL,
    indice_demanda  NUMERIC(4,2),   -- índice de empleabilidad 0-10
    salario_promedio NUMERIC(10,2),
    fuente          VARCHAR(120),
    UNIQUE (id_carrera, anio)
);

CREATE TABLE admision.test_vocacional (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_aspirante    UUID NOT NULL REFERENCES admision.aspirante(id),
    fecha           DATE NOT NULL DEFAULT CURRENT_DATE,
    estado          VARCHAR(20) NOT NULL DEFAULT 'INICIADO'
                    CHECK (estado IN ('INICIADO','COMPLETADO','EXPIRADO'))
);

CREATE TABLE admision.respuesta_test_vocacional (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_test         INTEGER NOT NULL REFERENCES admision.test_vocacional(id),
    id_campo        SMALLINT NOT NULL REFERENCES admision.campo_interes(id),
    puntaje         NUMERIC(4,2) NOT NULL,  -- afinidad 0-10
    UNIQUE (id_test, id_campo)
);

CREATE TABLE admision.resultado_orientacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_test         INTEGER NOT NULL UNIQUE REFERENCES admision.test_vocacional(id),
    id_carrera_rec  SMALLINT NOT NULL REFERENCES academico.carrera(id),
    id_campo_ppal   SMALLINT NOT NULL REFERENCES admision.campo_interes(id),
    puntaje_afinidad NUMERIC(5,2),
    razonamiento_ia TEXT,
    alternativas    JSONB,   -- lista de carreras alternativas con puntaje
    generado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SISTEMA 8 - Detección de plagio
-- =============================================================================

CREATE TABLE estudiantil.analisis_plagio (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_actividad    INTEGER NOT NULL REFERENCES estudiantil.actividad_calificable(id),
    fecha_analisis  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estado          VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE','EN_PROCESO','COMPLETADO','ERROR')),
    parametros      JSONB   -- umbral de similitud usado, algoritmo, etc.
);

CREATE TABLE estudiantil.resultado_plagio (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_analisis     INTEGER NOT NULL REFERENCES estudiantil.analisis_plagio(id),
    id_entrega_a    INTEGER NOT NULL REFERENCES estudiantil.entrega(id),
    id_entrega_b    INTEGER NOT NULL REFERENCES estudiantil.entrega(id),
    porcentaje_similitud NUMERIC(5,2) NOT NULL,
    nivel           VARCHAR(15) CHECK (nivel IN ('BAJO','MEDIO','ALTO','MUY_ALTO')),
    fragmentos      JSONB,   -- secciones similares identificadas
    CONSTRAINT chk_diferente_entrega CHECK (id_entrega_a <> id_entrega_b)
);

-- =============================================================================
-- SISTEMA 9, 10, 11, 12 - Generación IA de tutorías, tareas, test, lecciones
-- =============================================================================

-- Solicitudes de tutoría automática
CREATE TABLE docencia.solicitud_tutoria (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_matricula    INTEGER NOT NULL REFERENCES estudiantil.matricula(id),
    id_tema         INTEGER REFERENCES docencia.tema(id),
    descripcion     VARCHAR(300) NOT NULL,
    fecha           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estado          VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE','PROCESANDO','COMPLETADA','ERROR'))
);

CREATE TABLE docencia.tutoria_generada (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_solicitud        INTEGER NOT NULL UNIQUE REFERENCES docencia.solicitud_tutoria(id),
    tipo                VARCHAR(15) CHECK (tipo IN ('VIDEO','PDF','TEXTO')),
    contenido           TEXT,
    url_recurso         VARCHAR(500),
    prompt_usado        TEXT,
    modelo_ia           VARCHAR(60),
    generado_en         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valoracion          SMALLINT CHECK (valoracion BETWEEN 1 AND 5)
);

-- Banco de preguntas para test (Sistema 11)
CREATE TABLE docencia.banco_pregunta (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_tema         INTEGER NOT NULL REFERENCES docencia.tema(id),
    enunciado       TEXT NOT NULL,
    tipo            VARCHAR(20) CHECK (tipo IN ('OPCION_MULTIPLE','VERDADERO_FALSO','ABIERTA','EMPAREJAMIENTO')),
    dificultad      VARCHAR(10) CHECK (dificultad IN ('BAJA','MEDIA','ALTA')),
    nivel_bloom     VARCHAR(20) CHECK (nivel_bloom IN ('RECORDAR','COMPRENDER','APLICAR','ANALIZAR','EVALUAR','CREAR')),
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE docencia.opcion_pregunta (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_pregunta     INTEGER NOT NULL REFERENCES docencia.banco_pregunta(id),
    texto           TEXT NOT NULL,
    es_correcta     BOOLEAN NOT NULL DEFAULT FALSE,
    retroalimentacion TEXT
);

-- Test generados (Sistema 11)
CREATE TABLE docencia.test_generado (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_unidad       INTEGER REFERENCES docencia.unidad_tematica(id),
    nombre          VARCHAR(200) NOT NULL,
    duracion_min    SMALLINT,
    puntaje_total   NUMERIC(5,2),
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_apertura  TIMESTAMPTZ,
    fecha_cierre    TIMESTAMPTZ,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE docencia.pregunta_test (
    id_test         INTEGER NOT NULL REFERENCES docencia.test_generado(id),
    id_pregunta     INTEGER NOT NULL REFERENCES docencia.banco_pregunta(id),
    orden           SMALLINT NOT NULL,
    puntaje         NUMERIC(4,2),
    PRIMARY KEY (id_test, id_pregunta)
);

-- Lecciones interactivas en video (Sistema 12)
CREATE TABLE docencia.video_clase (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_tema         INTEGER REFERENCES docencia.tema(id),
    titulo          VARCHAR(200) NOT NULL,
    url_video       VARCHAR(500) NOT NULL,
    duracion_seg    INTEGER,
    plataforma      VARCHAR(30) CHECK (plataforma IN ('YOUTUBE','VIMEO','MOODLE','PANOPTO','OTRO')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE docencia.leccion_interactiva (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_video        INTEGER NOT NULL REFERENCES docencia.video_clase(id),
    segundo_inicio  INTEGER NOT NULL,  -- momento en segundos donde aparece la pregunta
    id_pregunta     INTEGER NOT NULL REFERENCES docencia.banco_pregunta(id),
    es_obligatoria  BOOLEAN NOT NULL DEFAULT TRUE,
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE docencia.respuesta_leccion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_leccion      INTEGER NOT NULL REFERENCES docencia.leccion_interactiva(id),
    id_matricula    INTEGER NOT NULL REFERENCES estudiantil.matricula(id),
    id_opcion       INTEGER REFERENCES docencia.opcion_pregunta(id),
    respuesta_abierta TEXT,
    es_correcta     BOOLEAN,
    fecha_respuesta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_leccion, id_matricula)
);

-- Informe de resultados de aprendizaje (Sistema 13)
CREATE TABLE docencia.informe_resultados_aprendizaje (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_plan         INTEGER NOT NULL REFERENCES docencia.plan_tematico(id),
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    contenido_json  JSONB,      -- análisis detallado por objetivo/resultado
    pdf_url         VARCHAR(500),
    estado          VARCHAR(20) DEFAULT 'BORRADOR'
                    CHECK (estado IN ('BORRADOR','PUBLICADO','ENTREGADO')),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SISTEMA 14 - Verificación de heteroevaluación
-- =============================================================================

CREATE TABLE docencia.encuesta_heteroevaluacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_paralelo     INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    fecha_apertura  TIMESTAMPTZ NOT NULL,
    fecha_cierre    TIMESTAMPTZ NOT NULL,
    activa          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE docencia.respuesta_heteroevaluacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_encuesta     INTEGER NOT NULL REFERENCES docencia.encuesta_heteroevaluacion(id),
    id_matricula    INTEGER NOT NULL REFERENCES estudiantil.matricula(id),
    id_criterio     INTEGER NOT NULL REFERENCES docencia.criterio_evaluacion_docente(id),
    puntaje         NUMERIC(4,2) NOT NULL,
    comentario      TEXT,
    fecha_respuesta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_encuesta, id_matricula, id_criterio)
);

CREATE TABLE docencia.verificacion_heteroevaluacion (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_encuesta         INTEGER NOT NULL REFERENCES docencia.encuesta_heteroevaluacion(id),
    id_matricula        INTEGER NOT NULL REFERENCES estudiantil.matricula(id),
    score_veracidad     NUMERIC(5,4),   -- 0-1 calculado por IA
    es_objetiva         BOOLEAN,
    factores_analisis   JSONB,          -- asistencia, calificaciones, cumplimiento vs. respuesta
    observacion_ia      TEXT,
    revisado_por        UUID REFERENCES core.persona(id),
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_encuesta, id_matricula)
);

-- =============================================================================
-- ESQUEMA TALENTO - Sistema 16: Concurso de méritos docentes
-- =============================================================================

CREATE TABLE talento.perfil_puesto (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_carrera      SMALLINT NOT NULL REFERENCES academico.carrera(id),
    nombre          VARCHAR(200) NOT NULL,
    codigo          VARCHAR(20) NOT NULL UNIQUE,
    descripcion     TEXT,
    asignaturas_afinidad TEXT[],   -- array de áreas temáticas
    nivel_formacion_requerido SMALLINT REFERENCES docencia.nivel_formacion(id),
    experiencia_min_anios SMALLINT DEFAULT 0,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE talento.criterio_merito (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(120) NOT NULL,
    descripcion     TEXT,
    peso            NUMERIC(5,2) NOT NULL,  -- % sobre puntaje total
    puntaje_max     NUMERIC(6,2) NOT NULL,
    formula_calculo TEXT,                   -- descripción de cómo se pondera
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);
-- Valores típicos según reglamento LOES Ecuador:
INSERT INTO talento.criterio_merito(nombre, peso, puntaje_max) VALUES
    ('Titulo_Cuarto_Nivel', 30.00, 30.00),
    ('Experiencia_Docente', 20.00, 20.00),
    ('Experiencia_Profesional', 10.00, 10.00),
    ('Publicaciones_Cientificas', 15.00, 15.00),
    ('Capacitaciones', 10.00, 10.00),
    ('Ponencias', 5.00, 5.00),
    ('Proyectos_Investigacion', 5.00, 5.00),
    ('Proyectos_Vinculacion', 3.00, 3.00),
    ('Tutorias_Titulacion', 2.00, 2.00);

CREATE TABLE talento.concurso_meritos (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_perfil       INTEGER NOT NULL REFERENCES talento.perfil_puesto(id),
    nombre          VARCHAR(200) NOT NULL,
    convocatoria    VARCHAR(50) NOT NULL UNIQUE,
    fecha_apertura  DATE NOT NULL,
    fecha_cierre    DATE NOT NULL,
    fecha_resultados DATE,
    estado          VARCHAR(20) NOT NULL DEFAULT 'CONVOCADO'
                    CHECK (estado IN ('CONVOCADO','EN_RECEPCION','EN_EVALUACION','CERRADO','DESIERTO')),
    plazas          SMALLINT NOT NULL DEFAULT 1
);

CREATE TABLE talento.postulante (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_persona      UUID NOT NULL REFERENCES core.persona(id),
    id_concurso     INTEGER NOT NULL REFERENCES talento.concurso_meritos(id),
    fecha_postulacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estado          VARCHAR(20) NOT NULL DEFAULT 'POSTULADO'
                    CHECK (estado IN ('POSTULADO','EN_REVISION','CALIFICADO','IMPUGNADO','DESCALIFICADO')),
    UNIQUE (id_persona, id_concurso)
);

-- Documentos del postulante referenciando sus entidades
CREATE TABLE talento.documento_postulante (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_postulante   UUID NOT NULL REFERENCES talento.postulante(id),
    id_criterio     INTEGER NOT NULL REFERENCES talento.criterio_merito(id),
    tipo_documento  VARCHAR(80) NOT NULL,
    descripcion     VARCHAR(300),
    archivo_url     VARCHAR(500) NOT NULL,
    verificado      BOOLEAN NOT NULL DEFAULT FALSE,
    verificado_por  UUID REFERENCES core.persona(id)
);

CREATE TABLE talento.calificacion_merito (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_postulante       UUID NOT NULL REFERENCES talento.postulante(id),
    id_criterio         INTEGER NOT NULL REFERENCES talento.criterio_merito(id),
    puntaje_obtenido    NUMERIC(6,2) NOT NULL,
    puntaje_ia          NUMERIC(6,2),    -- sugerencia del sistema IA
    calculado_por_ia    BOOLEAN NOT NULL DEFAULT FALSE,
    observacion         TEXT,
    calificado_por      UUID REFERENCES core.persona(id),
    calificado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_postulante, id_criterio)
);

CREATE TABLE talento.resultado_concurso (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_postulante   UUID NOT NULL UNIQUE REFERENCES talento.postulante(id),
    id_concurso     INTEGER NOT NULL REFERENCES talento.concurso_meritos(id),
    puntaje_total   NUMERIC(6,2) NOT NULL,
    posicion        SMALLINT,
    ganador         BOOLEAN NOT NULL DEFAULT FALSE,
    publicado_en    TIMESTAMPTZ
);

-- =============================================================================
-- ESQUEMA PRACTICAS - Sistema 17: Asignación prioritaria de internado
-- =============================================================================

CREATE TABLE practicas.requisito_habilitante (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_carrera      SMALLINT NOT NULL REFERENCES academico.carrera(id),
    nombre          VARCHAR(150) NOT NULL,
    descripcion     TEXT,
    tipo            VARCHAR(30) CHECK (tipo IN ('MODULO_APROBADO','CALIFICACIONES','INGLES','OTRO')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE practicas.modalidad_practica (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre  VARCHAR(80) NOT NULL UNIQUE   -- INTERNADO, PASANTIA, VINCULACION, etc.
);
INSERT INTO practicas.modalidad_practica(nombre) VALUES
    ('INTERNADO'),('PASANTIA'),('VINCULACION_COMUNITARIA');

CREATE TABLE practicas.tipo_institucion_receptora (
    id      SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre  VARCHAR(60) NOT NULL UNIQUE
);
INSERT INTO practicas.tipo_institucion_receptora(nombre) VALUES
    ('PUBLICA'),('PRIVADA'),('ONG'),('EMPRESA_PUBLICA'),('EMPRESA_PRIVADA');

CREATE TABLE practicas.institucion_receptora (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_tipo         SMALLINT NOT NULL REFERENCES practicas.tipo_institucion_receptora(id),
    nombre          VARCHAR(200) NOT NULL,
    ruc             VARCHAR(13),
    id_parroquia    SMALLINT REFERENCES core.parroquia(id),
    direccion       VARCHAR(200),
    contacto_nombre VARCHAR(120),
    contacto_email  VARCHAR(120),
    contacto_tel    VARCHAR(15),
    latitud         NUMERIC(9,6),
    longitud        NUMERIC(9,6),
    activa          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE practicas.plaza_practica (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_institucion      INTEGER NOT NULL REFERENCES practicas.institucion_receptora(id),
    id_carrera          SMALLINT NOT NULL REFERENCES academico.carrera(id),
    id_modalidad        SMALLINT NOT NULL REFERENCES practicas.modalidad_practica(id),
    id_periodo          SMALLINT NOT NULL REFERENCES academico.periodo(id),
    nombre_plaza        VARCHAR(200) NOT NULL,
    cupo_total          SMALLINT NOT NULL DEFAULT 1,
    cupo_disponible     SMALLINT NOT NULL DEFAULT 1,
    fecha_inicio        DATE,
    fecha_fin           DATE,
    descripcion         TEXT,
    requisitos_especificos TEXT,
    activa              BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_cupo CHECK (cupo_disponible >= 0 AND cupo_disponible <= cupo_total)
);

-- Criterios de ponderación para ranking (Sistema 17)
CREATE TABLE practicas.criterio_asignacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_carrera      SMALLINT NOT NULL REFERENCES academico.carrera(id),
    nombre          VARCHAR(120) NOT NULL,
    peso            NUMERIC(5,2) NOT NULL,
    descripcion     TEXT,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);
-- Ejemplo de criterios:
-- Promedio académico (30%), Estado civil c/hijos (25%), Situación económica (20%),
-- Ubicación geográfica cercanía (15%), Nivel académico completado (10%)

-- Verificación de requisitos habilitantes del estudiante
CREATE TABLE practicas.verificacion_requisito (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante       UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_requisito        INTEGER NOT NULL REFERENCES practicas.requisito_habilitante(id),
    id_periodo          SMALLINT NOT NULL REFERENCES academico.periodo(id),
    cumple              BOOLEAN NOT NULL,
    evidencia_url       VARCHAR(500),
    verificado_por      UUID REFERENCES core.persona(id),
    verificado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_estudiante, id_requisito, id_periodo)
);

-- Ranking y asignación (Sistema 17)
CREATE TABLE practicas.ranking_internado (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante       UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_periodo          SMALLINT NOT NULL REFERENCES academico.periodo(id),
    id_carrera          SMALLINT NOT NULL REFERENCES academico.carrera(id),
    puntaje_total       NUMERIC(6,4) NOT NULL,
    detalle_puntaje     JSONB,   -- desglose por criterio
    posicion            INTEGER,
    habilitado          BOOLEAN NOT NULL DEFAULT FALSE,   -- cumple todos los requisitos
    generado_por_ia     BOOLEAN NOT NULL DEFAULT FALSE,
    observaciones       TEXT,
    generado_en         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_estudiante, id_periodo)
);
CREATE INDEX idx_ranking_periodo_posicion ON practicas.ranking_internado(id_periodo, posicion);

CREATE TABLE practicas.asignacion_internado (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_ranking          INTEGER NOT NULL UNIQUE REFERENCES practicas.ranking_internado(id),
    id_plaza            INTEGER NOT NULL REFERENCES practicas.plaza_practica(id),
    fecha_asignacion    DATE NOT NULL DEFAULT CURRENT_DATE,
    estado              VARCHAR(20) NOT NULL DEFAULT 'ASIGNADA'
                        CHECK (estado IN ('ASIGNADA','CONFIRMADA','RECHAZADA','REASIGNADA','CANCELADA')),
    motivo_rechazo      VARCHAR(300),
    asignado_por        UUID REFERENCES core.persona(id),
    es_automatica       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE practicas.apelacion_internado (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_estudiante       UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_periodo          SMALLINT NOT NULL REFERENCES academico.periodo(id),
    motivo              TEXT NOT NULL,
    documentos_url      TEXT[],
    estado              VARCHAR(20) NOT NULL DEFAULT 'PRESENTADA'
                        CHECK (estado IN ('PRESENTADA','EN_REVISION','RESUELTA','DENEGADA')),
    resolucion          TEXT,
    resuelto_por        UUID REFERENCES core.persona(id),
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seguimiento de la práctica/internado
CREATE TABLE practicas.seguimiento_practica (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_asignacion       INTEGER NOT NULL REFERENCES practicas.asignacion_internado(id),
    id_docente_tutor    UUID REFERENCES docencia.docente(id),
    fecha_inicio_real   DATE,
    fecha_fin_real      DATE,
    horas_completadas   NUMERIC(6,2) DEFAULT 0,
    calificacion_final  NUMERIC(5,2),
    observaciones       TEXT
);

-- Tutorías de titulación (dato para concurso méritos, Sistema 16)
CREATE TABLE practicas.tutoria_titulacion (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_docente          UUID NOT NULL REFERENCES docencia.docente(id),
    id_estudiante       UUID NOT NULL REFERENCES estudiantil.estudiante(id),
    id_periodo          SMALLINT NOT NULL REFERENCES academico.periodo(id),
    tema_trabajo        VARCHAR(300) NOT NULL,
    tipo                VARCHAR(20) CHECK (tipo IN ('TITULACION','INTERNADO')),
    resultado           VARCHAR(20) CHECK (resultado IN ('APROBADO','EN_PROCESO','SUSPENDIDO')),
    fecha_inicio        DATE,
    fecha_fin           DATE
);

-- =============================================================================
-- ESQUEMA IA - Logs y control de modelos de IA
-- =============================================================================

CREATE TABLE ia.modelo_ia (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(100) NOT NULL,
    tipo            VARCHAR(30) CHECK (tipo IN ('CLASIFICACION','REGRESION','NLP','GENERATIVO','RECOMENDACION')),
    version         VARCHAR(20) NOT NULL,
    descripcion     TEXT,
    sistema_origen  VARCHAR(100),   -- 'SISTEMA_1_DESERCION', etc.
    fecha_despliegue DATE,
    metricas        JSONB,
    activo          BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (nombre, version)
);

CREATE TABLE ia.log_prediccion (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_modelo       INTEGER NOT NULL REFERENCES ia.modelo_ia(id),
    entidad_tipo    VARCHAR(60) NOT NULL,   -- 'estudiante', 'postulante', etc.
    entidad_id      UUID NOT NULL,
    input_data      JSONB,
    output_data     JSONB,
    confianza       NUMERIC(5,4),
    tiempo_ms       INTEGER,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_log_prediccion_entidad ON ia.log_prediccion(entidad_tipo, entidad_id, creado_en DESC);

CREATE TABLE ia.feedback_prediccion (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_log          BIGINT NOT NULL REFERENCES ia.log_prediccion(id),
    correcto        BOOLEAN,
    comentario      TEXT,
    revisado_por    UUID REFERENCES core.persona(id),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SISTEMA 3 - Distribución automática de docentes (tabla de resultado)
-- =============================================================================

CREATE TABLE academico.propuesta_horario (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_periodo      SMALLINT NOT NULL REFERENCES academico.periodo(id),
    id_carrera      SMALLINT NOT NULL REFERENCES academico.carrera(id),
    nombre          VARCHAR(100) NOT NULL,
    estado          VARCHAR(20) NOT NULL DEFAULT 'PROPUESTA'
                    CHECK (estado IN ('PROPUESTA','EN_REVISION','APROBADA','RECHAZADA')),
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    conflictos      JSONB,   -- lista de conflictos detectados
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    aprobado_por    UUID REFERENCES core.persona(id),
    aprobado_en     TIMESTAMPTZ
);

CREATE TABLE academico.item_propuesta_horario (
    id                  INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_propuesta        INTEGER NOT NULL REFERENCES academico.propuesta_horario(id),
    id_paralelo         INTEGER NOT NULL REFERENCES academico.paralelo(id),
    id_docente          UUID NOT NULL REFERENCES docencia.docente(id),
    id_espacio          SMALLINT NOT NULL REFERENCES academico.espacio_fisico(id),
    id_dia              SMALLINT NOT NULL REFERENCES academico.dia_semana(id),
    id_franja           SMALLINT NOT NULL REFERENCES academico.franja_horaria(id),
    tipo                VARCHAR(15) CHECK (tipo IN ('TEORIA','PRACTICA','LABORATORIO')),
    tiene_conflicto     BOOLEAN NOT NULL DEFAULT FALSE,
    detalle_conflicto   TEXT
);

-- =============================================================================
-- SISTEMA 5 - Generación de actividades para bajo rendimiento
-- =============================================================================

CREATE TABLE estudiantil.actividad_recuperacion (
    id              INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_matricula    INTEGER NOT NULL REFERENCES estudiantil.matricula(id),
    id_tema         INTEGER NOT NULL REFERENCES docencia.tema(id),
    descripcion     TEXT NOT NULL,
    tipo            VARCHAR(40),   -- EJERCICIOS_ADICIONALES, VIDEO_COMPLEMENTARIO, etc.
    generado_por_ia BOOLEAN NOT NULL DEFAULT FALSE,
    estado          VARCHAR(20) DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE','EN_PROGRESO','COMPLETADA','IGNORADA')),
    fecha_limite    DATE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- VISTAS ÚTILES
-- =============================================================================

-- Vista: promedio académico del estudiante por periodo
CREATE VIEW estudiantil.v_promedio_estudiante_periodo AS
SELECT
    m.id_estudiante,
    p.id AS id_periodo,
    p.nombre AS periodo,
    ROUND(AVG(c.puntaje), 2) AS promedio,
    COUNT(DISTINCT m.id) AS materias_matriculadas,
    COUNT(DISTINCT CASE WHEN m.estado = 'APROBADA' THEN m.id END) AS materias_aprobadas
FROM estudiantil.matricula m
JOIN academico.paralelo pa ON m.id_paralelo = pa.id
JOIN academico.periodo p ON pa.id_periodo = p.id
LEFT JOIN estudiantil.entrega e ON e.id_matricula = m.id
LEFT JOIN estudiantil.calificacion c ON c.id_entrega = e.id
GROUP BY m.id_estudiante, p.id, p.nombre;

-- Vista: porcentaje de asistencia del estudiante por paralelo
CREATE VIEW estudiantil.v_asistencia_paralelo AS
SELECT
    a.id_matricula,
    COUNT(*) AS total_clases,
    COUNT(CASE WHEN a.estado IN ('PRESENTE','TARDANZA') THEN 1 END) AS clases_asistidas,
    ROUND(COUNT(CASE WHEN a.estado IN ('PRESENTE','TARDANZA') THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS porcentaje_asistencia
FROM estudiantil.asistencia a
GROUP BY a.id_matricula;

-- Vista: ranking internado con datos completos
CREATE VIEW practicas.v_ranking_detalle AS
SELECT
    r.id_periodo,
    r.posicion,
    e.codigo_estudiante,
    p.primer_nombre || ' ' || p.primer_apellido AS nombre_estudiante,
    r.puntaje_total,
    r.habilitado,
    r.detalle_puntaje,
    ai.id_plaza AS plaza_asignada
FROM practicas.ranking_internado r
JOIN estudiantil.estudiante e ON r.id_estudiante = e.id
JOIN core.persona p ON e.id_persona = p.id
LEFT JOIN practicas.asignacion_internado ai ON ai.id_ranking = r.id;

-- Vista: puntaje total por postulante en concurso
CREATE VIEW talento.v_puntaje_concurso AS
SELECT
    po.id AS id_postulante,
    po.id_concurso,
    p.primer_nombre || ' ' || p.primer_apellido AS nombre,
    p.numero_identificacion,
    SUM(cm.puntaje_obtenido) AS puntaje_total,
    COUNT(cm.id) AS criterios_evaluados
FROM talento.postulante po
JOIN core.persona p ON po.id_persona = p.id
LEFT JOIN talento.calificacion_merito cm ON cm.id_postulante = po.id
GROUP BY po.id, po.id_concurso, p.primer_nombre, p.primer_apellido, p.numero_identificacion;

-- =============================================================================
-- ÍNDICES ADICIONALES DE RENDIMIENTO
-- =============================================================================

CREATE INDEX idx_matricula_paralelo ON estudiantil.matricula(id_paralelo);
CREATE INDEX idx_entrega_actividad ON estudiantil.entrega(id_actividad);
CREATE INDEX idx_calificacion_entrega ON estudiantil.calificacion(id_entrega);
CREATE INDEX idx_alerta_estado ON estudiantil.alerta_desercion(estado, nivel_riesgo);
CREATE INDEX idx_asignacion_docente ON docencia.asignacion_docente_paralelo(id_docente, id_paralelo);
CREATE INDEX idx_disponibilidad_docente ON docencia.disponibilidad_docente(id_docente, id_periodo);
CREATE INDEX idx_horario_dia_franja ON academico.horario_paralelo(id_dia, id_franja);
CREATE INDEX idx_plaza_periodo ON practicas.plaza_practica(id_periodo, id_carrera, activa);
CREATE INDEX idx_postulante_concurso ON talento.postulante(id_concurso, estado);
CREATE INDEX idx_log_ia_modelo ON ia.log_prediccion(id_modelo, creado_en DESC);
CREATE INDEX idx_resultado_plagio_actividad ON estudiantil.resultado_plagio(id_analisis);

-- Índice GIN para búsqueda de texto en contenido generado por IA
CREATE INDEX idx_recurso_contenido ON docencia.recurso_aprendizaje USING gin(to_tsvector('spanish', COALESCE(titulo,'') || ' ' || COALESCE(descripcion,'')));
CREATE INDEX idx_pregunta_enunciado ON docencia.banco_pregunta USING gin(to_tsvector('spanish', enunciado));

-- Índice de similitud de texto para detección de plagio
CREATE INDEX idx_entrega_contenido_trgm ON estudiantil.entrega USING gin(contenido_texto gin_trgm_ops);

-- =============================================================================
-- TRIGGERS - Integridad y automatización
-- =============================================================================

-- Actualiza timestamp automáticamente
CREATE OR REPLACE FUNCTION core.fn_actualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_persona_timestamp
    BEFORE UPDATE ON core.persona
    FOR EACH ROW EXECUTE FUNCTION core.fn_actualizar_timestamp();

-- Trigger: reducir cupo disponible al asignar plaza de internado
CREATE OR REPLACE FUNCTION practicas.fn_reducir_cupo()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'CONFIRMADA' THEN
        UPDATE practicas.plaza_practica
        SET cupo_disponible = cupo_disponible - 1
        WHERE id = NEW.id_plaza
          AND cupo_disponible > 0;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No hay cupo disponible en la plaza %', NEW.id_plaza;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_asignacion_cupo
    AFTER INSERT OR UPDATE OF estado ON practicas.asignacion_internado
    FOR EACH ROW EXECUTE FUNCTION practicas.fn_reducir_cupo();

-- Trigger: verificar colisión de docente en horario
CREATE OR REPLACE FUNCTION academico.fn_verificar_colision_docente()
RETURNS TRIGGER AS $$
DECLARE
    v_conflicto INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_conflicto
    FROM academico.item_propuesta_horario iph
    WHERE iph.id_propuesta = NEW.id_propuesta
      AND iph.id_docente = NEW.id_docente
      AND iph.id_dia = NEW.id_dia
      AND iph.id_franja = NEW.id_franja
      AND iph.id <> COALESCE(NEW.id, 0);

    IF v_conflicto > 0 THEN
        NEW.tiene_conflicto := TRUE;
        NEW.detalle_conflicto := 'Docente ya asignado en este día/franja';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_colision_docente
    BEFORE INSERT OR UPDATE ON academico.item_propuesta_horario
    FOR EACH ROW EXECUTE FUNCTION academico.fn_verificar_colision_docente();

-- =============================================================================
-- DATOS SEMILLA MÍNIMOS
-- =============================================================================

INSERT INTO academico.facultad(nombre, codigo) VALUES
    ('Facultad de Tecnología e Innovación', 'FTI');

INSERT INTO academico.carrera(id_facultad, nombre, codigo, modalidad, duracion_ciclos, titulo_otorga)
VALUES (1, 'Ingeniería en Sistemas Inteligentes', 'ISI', 'PRESENCIAL', 8, 'Ingeniero/a en Sistemas Inteligentes');

INSERT INTO academico.nivel(numero, nombre) VALUES
    (1,'Primer Nivel'),(2,'Segundo Nivel'),(3,'Tercer Nivel'),(4,'Cuarto Nivel'),
    (5,'Quinto Nivel'),(6,'Sexto Nivel'),(7,'Séptimo Nivel'),(8,'Octavo Nivel');

-- =============================================================================
-- COMENTARIOS PARA DOCUMENTACIÓN
-- =============================================================================

COMMENT ON SCHEMA core        IS 'Entidades base: persona, usuario, roles, ubicación';
COMMENT ON SCHEMA academico   IS 'Estructura académica: carrera, asignatura, periodo, horario, espacio';
COMMENT ON SCHEMA docencia    IS 'Gestión docente: plan temático, recursos, evaluación, capacitación';
COMMENT ON SCHEMA estudiantil IS 'Seguimiento estudiantil: matrícula, calificaciones, asistencia, riesgo';
COMMENT ON SCHEMA admision    IS 'Orientación vocacional y admisión de aspirantes';
COMMENT ON SCHEMA talento     IS 'Concursos de méritos y gestión de talento humano docente';
COMMENT ON SCHEMA practicas   IS 'Prácticas preprofesionales e internado';
COMMENT ON SCHEMA ia          IS 'Registro de modelos IA, predicciones y feedback';

COMMENT ON TABLE core.persona                           IS 'Tabla raíz de toda entidad humana del sistema';
COMMENT ON TABLE estudiantil.alerta_desercion           IS 'Sistema 1: Alertas de riesgo de deserción generadas por IA';
COMMENT ON TABLE admision.resultado_orientacion         IS 'Sistema 2: Resultado de orientación vocacional por IA';
COMMENT ON TABLE academico.propuesta_horario            IS 'Sistema 3: Distribución automática de docentes por IA';
COMMENT ON TABLE academico.reserva_espacio              IS 'Sistema 4: Gestión de espacios físicos';
COMMENT ON TABLE estudiantil.actividad_recuperacion     IS 'Sistema 5: Actividades de recuperación generadas por IA';
COMMENT ON TABLE docencia.recurso_aprendizaje           IS 'Sistema 6: Recursos de aprendizaje (generados o subidos)';
COMMENT ON TABLE estudiantil.calificacion               IS 'Sistema 7: Calificación automática (campo calificado_por_ia)';
COMMENT ON TABLE estudiantil.resultado_plagio           IS 'Sistema 8: Detección de plagio entre entregas';
COMMENT ON TABLE docencia.tutoria_generada              IS 'Sistema 9: Tutorías académicas automáticas';
COMMENT ON TABLE estudiantil.actividad_calificable      IS 'Sistema 10: Tareas y talleres (generados_por_ia)';
COMMENT ON TABLE docencia.test_generado                 IS 'Sistema 11: Tests generados automáticamente';
COMMENT ON TABLE docencia.leccion_interactiva           IS 'Sistema 12: Lecciones interactivas en video';
COMMENT ON TABLE docencia.informe_resultados_aprendizaje IS 'Sistema 13: Informe de resultados de aprendizaje';
COMMENT ON TABLE docencia.verificacion_heteroevaluacion IS 'Sistema 14: Verificación de objetividad en heteroevaluación';
COMMENT ON TABLE docencia.plan_capacitacion             IS 'Sistema 15: Plan de capacitación docente generado por IA';
COMMENT ON TABLE talento.calificacion_merito            IS 'Sistema 16: Calificación automática de méritos docentes';
COMMENT ON TABLE practicas.ranking_internado            IS 'Sistema 17: Ranking y asignación de internado por IA';
