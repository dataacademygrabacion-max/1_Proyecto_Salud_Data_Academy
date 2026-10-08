-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 02 · Capa Plata – Limpieza y Unificación con Spark SQL
-- MAGIC **Fase 3 del proyecto (parte 1).** Misma lógica del proyecto original de ingeniería de datos, pero sencilla:
-- MAGIC
-- MAGIC 1. **Unir** Hospital A + Hospital B con `UNION ALL` y marcar la `fuente` (`hosa` / `hosb`).
-- MAGIC 2. **Unificar columnas** cuando cada hospital las llama distinto (Modelo de Datos Común).
-- MAGIC 3. **Limpiar**: `DISTINCT` (sin duplicados), `TRY_CAST` (fechas y montos), estandarizar textos.
-- MAGIC 4. Crear una **clave única** `id + '-' + fuente` (los IDs se repiten entre hospitales).
-- MAGIC 5. Marcar **cuarentena** (`en_cuarentena = true`) si falta un dato obligatorio. No se borra: se filtra en Oro.
-- MAGIC
-- MAGIC > El proyecto original además aplicaba **SCD Tipo 2** (`MERGE` con historial). Aquí lo omitimos:
-- MAGIC > cargamos todo completo cada vez con `CREATE OR REPLACE TABLE`.
-- MAGIC
-- MAGIC **Requisito:** haber ejecutado `01_carga_y_EDA` (crea las tablas `workspace.salud_bronce.*`).

-- COMMAND ----------

USE CATALOG workspace;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1 · Departamentos

-- COMMAND ----------

SELECT *
FROM workspace.salud_bronce.departamentos_ha

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_plata.departamentos AS
SELECT DISTINCT
    CONCAT(id_departamento, '-', fuente) AS clave_departamento,
    id_departamento,
    nombre,
    fuente,
    CASE WHEN id_departamento IS NULL OR nombre IS NULL THEN true ELSE false END AS en_cuarentena,
    current_timestamp() AS fecha_carga
FROM (
    SELECT *, 'hosa' AS fuente FROM salud_bronce.departamentos_ha
    UNION ALL
    SELECT *, 'hosb' AS fuente FROM salud_bronce.departamentos_hb
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 · Médicos
-- MAGIC El ID viene como `H1-PROV0001`, pero las transacciones usan `PROV0001` → guardamos también el ID de origen.

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_plata.medicos AS
SELECT DISTINCT
    CONCAT(split_part(id_medico, '-', 2), '-', fuente) AS clave_medico,
    id_medico,
    split_part(id_medico, '-', 2)                      AS id_medico_origen,
    nombre,
    apellido,
    CONCAT(nombre, ' ', apellido)                      AS nombre_completo,
    especialidad,
    id_departamento,
    CONCAT(id_departamento, '-', fuente)               AS clave_departamento,
    TRY_CAST(npi AS BIGINT)                            AS npi,
    fuente,
    CASE WHEN id_medico IS NULL OR id_departamento IS NULL THEN true ELSE false END AS en_cuarentena,
    current_timestamp() AS fecha_carga
FROM (
    SELECT *, 'hosa' AS fuente FROM salud_bronce.medicos_ha
    UNION ALL
    SELECT *, 'hosb' AS fuente FROM salud_bronce.medicos_hb
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3 · Pacientes (aquí está el Modelo de Datos Común)
-- MAGIC El Hospital B llama distinto a sus columnas → las renombramos con `AS` al estándar del Hospital A.

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_plata.pacientes AS
SELECT DISTINCT
    CONCAT(id_paciente, '-', fuente)        AS clave_paciente,
    id_paciente,
    nombre,
    apellido,
    segundo_nombre,
    nro_seguro_social,
    telefono,
    genero,
    TRY_CAST(fecha_nacimiento AS DATE)      AS fecha_nacimiento,
    direccion,
    TRY_CAST(fecha_modificacion AS DATE)    AS fecha_modificacion,
    fuente,
    CASE WHEN id_paciente IS NULL OR fecha_nacimiento IS NULL
              OR nombre IS NULL OR LOWER(nombre) = 'null' THEN true ELSE false END AS en_cuarentena,
    current_timestamp() AS fecha_carga
FROM (
    SELECT id_paciente, nombre, apellido, segundo_nombre, nro_seguro_social, telefono,
           genero, fecha_nacimiento, direccion, fecha_modificacion, 'hosa' AS fuente
    FROM salud_bronce.pacientes_ha
    UNION ALL
    SELECT codigo AS id_paciente, p_nombre AS nombre, p_apellido AS apellido, s_nombre AS segundo_nombre,
           nro_seguro_social, telefono, genero, fecha_nacimiento, direccion,
           fecha_actualizacion AS fecha_modificacion, 'hosb' AS fuente
    FROM salud_bronce.pacientes_hb
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4 · Atenciones (visitas)

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_plata.atenciones AS
SELECT DISTINCT
    CONCAT(id_atencion, '-', fuente)      AS clave_atencion,
    id_atencion,
    id_paciente,
    id_medico,
    id_departamento,
    CONCAT(id_paciente, '-', fuente)      AS clave_paciente,
    CONCAT(id_medico, '-', fuente)        AS clave_medico,
    CONCAT(id_departamento, '-', fuente)  AS clave_departamento,
    TRY_CAST(fecha_atencion AS DATE)      AS fecha_atencion,
    tipo_atencion,
    codigo_procedimiento,
    TRY_CAST(fecha_insercion AS DATE)     AS fecha_insercion,
    TRY_CAST(fecha_modificacion AS DATE)  AS fecha_modificacion,
    fuente,
    CASE WHEN id_atencion IS NULL OR id_paciente IS NULL OR fecha_atencion IS NULL
              OR LOWER(tipo_atencion) = 'null' THEN true ELSE false END AS en_cuarentena,
    current_timestamp() AS fecha_carga
FROM (
    SELECT *, 'hosa' AS fuente FROM salud_bronce.atenciones_ha
    UNION ALL
    SELECT *, 'hosb' AS fuente FROM salud_bronce.atenciones_hb
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 5 · Transacciones (facturación)

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_plata.transacciones AS
SELECT DISTINCT
    CONCAT(id_transaccion, '-', fuente)   AS clave_transaccion,
    id_transaccion,
    id_atencion,
    id_paciente,
    id_medico,
    id_departamento,
    CONCAT(id_atencion, '-', fuente)      AS clave_atencion,
    CONCAT(id_paciente, '-', fuente)      AS clave_paciente,
    CONCAT(id_medico, '-', fuente)        AS clave_medico,
    CONCAT(id_departamento, '-', fuente)  AS clave_departamento,
    TRY_CAST(fecha_visita AS DATE)        AS fecha_visita,
    TRY_CAST(fecha_servicio AS DATE)      AS fecha_servicio,
    TRY_CAST(fecha_pago AS DATE)          AS fecha_pago,
    tipo_visita,
    ROUND(TRY_CAST(monto_facturado AS DOUBLE), 2) AS monto_facturado,
    tipo_monto,
    ROUND(TRY_CAST(monto_pagado AS DOUBLE), 2)    AS monto_pagado,
    id_reclamo,
    id_pagador,
    codigo_procedimiento,
    codigo_cie,
    linea_negocio,
    id_medicaid,
    id_medicare,
    TRY_CAST(fecha_insercion AS DATE)     AS fecha_insercion,
    TRY_CAST(fecha_modificacion AS DATE)  AS fecha_modificacion,
    fuente,
    CASE WHEN id_transaccion IS NULL OR id_atencion IS NULL OR id_paciente IS NULL
              OR fecha_visita IS NULL THEN true ELSE false END AS en_cuarentena,
    current_timestamp() AS fecha_carga
FROM (
    SELECT *, 'hosa' AS fuente FROM salud_bronce.transacciones_ha
    UNION ALL
    SELECT *, 'hosb' AS fuente FROM salud_bronce.transacciones_hb
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 6 · Reclamos a aseguradoras

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_plata.reclamos AS
SELECT DISTINCT
    CONCAT(id_reclamo, '-', fuente)       AS clave_reclamo,
    id_reclamo,
    id_transaccion,
    id_paciente,
    id_atencion,
    id_medico,
    id_departamento,
    CONCAT(id_transaccion, '-', fuente)   AS clave_transaccion,
    CONCAT(id_paciente, '-', fuente)      AS clave_paciente,
    TRY_CAST(fecha_servicio AS DATE)      AS fecha_servicio,
    TRY_CAST(fecha_reclamo AS DATE)       AS fecha_reclamo,
    aseguradora,
    TRY_CAST(monto_reclamado AS DOUBLE)   AS monto_reclamado,
    TRY_CAST(monto_pagado AS DOUBLE)      AS monto_pagado,
    estado_reclamo,
    tipo_pagador,
    TRY_CAST(deducible AS DOUBLE)         AS deducible,
    TRY_CAST(coaseguro AS DOUBLE)         AS coaseguro,
    TRY_CAST(copago AS DOUBLE)            AS copago,
    TRY_CAST(fecha_insercion AS DATE)     AS fecha_insercion,
    TRY_CAST(fecha_modificacion AS DATE)  AS fecha_modificacion,
    fuente,
    CASE WHEN id_reclamo IS NULL OR id_paciente IS NULL OR id_transaccion IS NULL
              OR LOWER(estado_reclamo) = 'null' THEN true ELSE false END AS en_cuarentena,
    current_timestamp() AS fecha_carga
FROM (
    SELECT *, 'hosa' AS fuente FROM salud_bronce.reclamos_ha
    UNION ALL
    SELECT *, 'hosb' AS fuente FROM salud_bronce.reclamos_hb
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 7 · Códigos CPT (catálogo de procedimientos)
-- MAGIC Estandarizamos `estado_codigo` ("Sin cambios" → "Sin Cambios").

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_plata.codigos_cpt AS
SELECT DISTINCT
    CONCAT(codigo_cpt, '-', 'hosa')  AS clave_cpt,
    categoria_procedimiento,
    codigo_cpt,
    descripcion_procedimiento,
    CASE WHEN LOWER(estado_codigo) = 'sin cambios' THEN 'Sin Cambios' ELSE estado_codigo END AS estado_codigo,
    'hosa' AS fuente,
    CASE WHEN codigo_cpt IS NULL OR LOWER(estado_codigo) = 'null' THEN true ELSE false END AS en_cuarentena,
    current_timestamp() AS fecha_carga
FROM salud_bronce.codigos_cpt;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Verificación: filas y registros en cuarentena por tabla

-- COMMAND ----------

SELECT 'departamentos' AS tabla, COUNT(*) AS filas, SUM(CAST(en_cuarentena AS INT)) AS en_cuarentena FROM salud_plata.departamentos
UNION ALL SELECT 'medicos',       COUNT(*), SUM(CAST(en_cuarentena AS INT)) FROM salud_plata.medicos
UNION ALL SELECT 'pacientes',     COUNT(*), SUM(CAST(en_cuarentena AS INT)) FROM salud_plata.pacientes
UNION ALL SELECT 'atenciones',    COUNT(*), SUM(CAST(en_cuarentena AS INT)) FROM salud_plata.atenciones
UNION ALL SELECT 'transacciones', COUNT(*), SUM(CAST(en_cuarentena AS INT)) FROM salud_plata.transacciones
UNION ALL SELECT 'reclamos',      COUNT(*), SUM(CAST(en_cuarentena AS INT)) FROM salud_plata.reclamos
UNION ALL SELECT 'codigos_cpt',   COUNT(*), SUM(CAST(en_cuarentena AS INT)) FROM salud_plata.codigos_cpt;