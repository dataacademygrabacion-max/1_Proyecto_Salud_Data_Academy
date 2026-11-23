-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 03 · Capa Oro – Tablas listas para Power BI (Spark SQL)
-- MAGIC **Fase 3 del proyecto (parte 2).** Pasamos las tablas de Plata a Oro:
-- MAGIC - Solo filas **válidas** (`en_cuarentena = false`).
-- MAGIC - Sin columnas técnicas (`en_cuarentena`, `fecha_carga`) → `SELECT * EXCEPT (...)`.
-- MAGIC - Nombres de **modelo estrella**: `dim_` (quién / qué / dónde) y `fact_` (lo que pasó, con montos).
-- MAGIC
-- MAGIC Los KPIs (ingresos, tasa de aprobación, etc.) se calculan en **Power BI con DAX** (Fase 4).

-- COMMAND ----------

USE CATALOG workspace;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Dimensiones

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.salud_oro.dim_departamentos AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.departamentos WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE workspace.salud_oro.dim_medicos AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.medicos WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE workspace.salud_oro.dim_pacientes AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.pacientes WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE workspace.salud_oro.dim_codigos_cpt AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.codigos_cpt WHERE en_cuarentena = false;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Hechos

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.salud_oro.fact_atenciones AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.atenciones WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE workspace.salud_oro.fact_transacciones AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.transacciones WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE workspace.salud_oro.fact_reclamos AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.reclamos WHERE en_cuarentena = false;

-- COMMAND ----------

SELECT YEAR(fecha_atencion) AS anio, COUNT(1) AS total_atenciones
FROM workspace.salud_oro.fact_atenciones
GROUP BY ALL
ORDER BY anio;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Validación: KPIs del negocio
-- MAGIC Estos números deben coincidir con tu dashboard en Power BI.

-- COMMAND ----------

-- KPIs financieros generales
SELECT
    YEAR(fecha_servicio)                                                 AS anio,
    ROUND(SUM(monto_facturado), 2)                                       AS total_facturado,
    ROUND(SUM(monto_pagado), 2)                                          AS total_pagado,
    ROUND(TRY_DIVIDE(SUM(monto_pagado), SUM(monto_facturado)) * 100, 2)  AS pct_cobrado,
    COUNT(DISTINCT clave_paciente)                                       AS pacientes_atendidos
FROM workspace.salud_oro.fact_transacciones
GROUP BY YEAR(fecha_servicio)
ORDER BY anio;

-- COMMAND ----------

-- Tasa de aprobación de reclamos por aseguradora (4 peruanas + 2 internacionales)
SELECT
    aseguradora,
    tipo_pagador,
    COUNT(*)                                                                                AS total_reclamos,
    ROUND(AVG(CASE WHEN estado_reclamo IN ('Aprobado', 'Pagado') THEN 1 ELSE 0 END) * 100, 2) AS pct_aprobados,
    ROUND(SUM(monto_reclamado - monto_pagado), 2)                                           AS saldo_pendiente
FROM workspace.salud_oro.fact_reclamos
GROUP BY aseguradora, tipo_pagador
ORDER BY total_reclamos DESC;

-- COMMAND ----------

-- Facturación por departamento
SELECT d.nombre AS departamento,
       COUNT(*) AS transacciones,
       ROUND(SUM(t.monto_facturado), 2) AS total_facturado
FROM workspace.salud_oro.fact_transacciones t
JOIN workspace.salud_oro.dim_departamentos d ON t.clave_departamento = d.clave_departamento
GROUP BY d.nombre
ORDER BY total_facturado DESC;

-- COMMAND ----------

-- Evolutivo mensual: facturado vs. cobrado (gráfico principal del dashboard)
SELECT YEAR(fecha_servicio)                                              AS anio,
       MONTH(fecha_servicio)                                             AS mes,
       ROUND(SUM(monto_facturado), 2)                                    AS total_facturado,
       ROUND(SUM(monto_pagado), 2)                                       AS total_cobrado,
       ROUND(TRY_DIVIDE(SUM(monto_pagado), SUM(monto_facturado)) * 100, 1) AS pct_cobrado
FROM workspace.salud_oro.fact_transacciones
GROUP BY YEAR(fecha_servicio), MONTH(fecha_servicio)
ORDER BY anio, mes;

-- COMMAND ----------

-- % Aprobación por mes (meta 40%): detecta los meses con caída
SELECT YEAR(fecha_reclamo)                                                                      AS anio,
       MONTH(fecha_reclamo)                                                                     AS mes,
       COUNT(*)                                                                                 AS total_reclamos,
       ROUND(AVG(CASE WHEN estado_reclamo IN ('Aprobado', 'Pagado') THEN 1 ELSE 0 END) * 100, 1) AS pct_aprobacion
FROM workspace.salud_oro.fact_reclamos
GROUP BY YEAR(fecha_reclamo), MONTH(fecha_reclamo)
ORDER BY anio, mes;

-- COMMAND ----------

-- ¿Qué aseguradoras rechazan más?
SELECT aseguradora,
       tipo_pagador,
       COUNT(*)                                                                                     AS total_reclamos,
       ROUND(AVG(CASE WHEN estado_reclamo IN ('Rechazado', 'Denegado') THEN 1 ELSE 0 END) * 100, 1) AS pct_rechazo
FROM workspace.salud_oro.fact_reclamos
GROUP BY aseguradora, tipo_pagador
ORDER BY pct_rechazo DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Auditoría de Integridad y Reglas de Negocio (debe devolver 0 en todos los controles)

-- COMMAND ----------

SELECT 'reclamos: fecha_reclamo < fecha_atencion' AS control, COUNT(*) AS incumplimientos
FROM workspace.salud_oro.fact_reclamos r
JOIN workspace.salud_oro.fact_atenciones a ON r.clave_atencion = a.clave_atencion
WHERE r.fecha_reclamo < a.fecha_atencion

UNION ALL
SELECT 'reclamos: fecha_servicio != fecha_atencion', COUNT(*)
FROM workspace.salud_oro.fact_reclamos r
JOIN workspace.salud_oro.fact_atenciones a ON r.clave_atencion = a.clave_atencion
WHERE r.fecha_servicio <> a.fecha_atencion

UNION ALL
SELECT 'transacciones: fecha_pago < fecha_servicio', COUNT(*)
FROM workspace.salud_oro.fact_transacciones
WHERE fecha_pago < fecha_servicio

UNION ALL
SELECT 'transacciones: fecha_servicio != fecha_atencion', COUNT(*)
FROM workspace.salud_oro.fact_transacciones t
JOIN workspace.salud_oro.fact_atenciones a ON t.clave_atencion = a.clave_atencion
WHERE t.fecha_servicio <> a.fecha_atencion

UNION ALL
SELECT 'transacciones: monto_pagado > monto_facturado', COUNT(*)
FROM workspace.salud_oro.fact_transacciones
WHERE monto_pagado > monto_facturado

UNION ALL
SELECT 'reclamos: monto_reclamado != monto_facturado', COUNT(*)
FROM workspace.salud_oro.fact_reclamos r
JOIN workspace.salud_oro.fact_transacciones t ON r.clave_transaccion = t.clave_transaccion
WHERE ROUND(r.monto_reclamado, 2) <> ROUND(t.monto_facturado, 2)

UNION ALL
SELECT 'reclamos: estado Pagado con monto_pagado <= 0', COUNT(*)
FROM workspace.salud_oro.fact_reclamos
WHERE estado_reclamo = 'Pagado' AND monto_pagado <= 0

UNION ALL
SELECT 'reclamos: estado != Pagado con monto_pagado > 0', COUNT(*)
FROM workspace.salud_oro.fact_reclamos
WHERE estado_reclamo <> 'Pagado' AND monto_pagado > 0

UNION ALL
SELECT 'integridad: atenciones sin medico en dim_medicos', COUNT(*)
FROM workspace.salud_oro.fact_atenciones a
LEFT JOIN workspace.salud_oro.dim_medicos m ON a.clave_medico = m.clave_medico
WHERE m.clave_medico IS NULL

UNION ALL
SELECT 'integridad: reclamos sin atencion en fact_atenciones', COUNT(*)
FROM workspace.salud_oro.fact_reclamos r
LEFT JOIN workspace.salud_oro.fact_atenciones a ON r.clave_atencion = a.clave_atencion
WHERE a.clave_atencion IS NULL

UNION ALL
SELECT 'contabilidad: tran.monto_pagado != paciente + pago_aseguradora', COUNT(*)
FROM workspace.salud_oro.fact_transacciones t
JOIN workspace.salud_oro.fact_reclamos r ON t.clave_transaccion = r.clave_transaccion
WHERE ROUND(t.monto_pagado, 2) <> ROUND(r.copago + r.deducible + r.coaseguro + r.monto_pagado, 2)

UNION ALL
SELECT 'cardinalidad: transacciones con mas de 1 reclamo', COUNT(*)
FROM (
    SELECT clave_transaccion
    FROM workspace.salud_oro.fact_reclamos
    GROUP BY clave_transaccion
    HAVING COUNT(*) > 1
);