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

CREATE OR REPLACE TABLE salud_oro.dim_departamentos AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.departamentos WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE salud_oro.dim_medicos AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.medicos WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE salud_oro.dim_pacientes AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.pacientes WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE salud_oro.dim_codigos_cpt AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.codigos_cpt WHERE en_cuarentena = false;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Hechos

-- COMMAND ----------

CREATE OR REPLACE TABLE salud_oro.fact_atenciones AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.atenciones WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE salud_oro.fact_transacciones AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.transacciones WHERE en_cuarentena = false;

CREATE OR REPLACE TABLE salud_oro.fact_reclamos AS
SELECT * EXCEPT (en_cuarentena, fecha_carga) FROM workspace.salud_plata.reclamos WHERE en_cuarentena = false;

-- COMMAND ----------

select year(fecha_atencion) ,count(1)
from workspace.salud_oro.fact_atenciones
group by all

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Validación: KPIs del negocio
-- MAGIC Estos números deben coincidir con tu dashboard en Power BI.

-- COMMAND ----------

-- KPIs financieros generales
SELECT
    ROUND(SUM(monto_facturado), 2)                           AS total_facturado,
    ROUND(SUM(monto_pagado), 2)                              AS total_pagado,
    ROUND(SUM(monto_pagado) / SUM(monto_facturado) * 100, 2) AS pct_cobrado,
    COUNT(DISTINCT clave_paciente)                           AS pacientes_atendidos
FROM workspace.salud_oro.fact_transacciones;

-- COMMAND ----------

-- Tasa de aprobación de reclamos por aseguradora
SELECT
    aseguradora,
    COUNT(*)                                                                                AS total_reclamos,
    ROUND(AVG(CASE WHEN estado_reclamo IN ('Aprobado', 'Pagado') THEN 1 ELSE 0 END) * 100, 2) AS pct_aprobados,
    ROUND(SUM(monto_reclamado - monto_pagado), 2)                                           AS saldo_pendiente
FROM salud_oro.fact_reclamos
GROUP BY aseguradora
ORDER BY total_reclamos DESC;

-- COMMAND ----------

-- Facturación por departamento
SELECT d.nombre AS departamento,
       COUNT(*) AS transacciones,
       ROUND(SUM(t.monto_facturado), 2) AS total_facturado
FROM salud_oro.fact_transacciones t
JOIN salud_oro.dim_departamentos d ON t.clave_departamento = d.clave_departamento
GROUP BY d.nombre
ORDER BY total_facturado DESC;

-- COMMAND ----------

-- Evolutivo mensual: facturado vs. cobrado (gráfico principal del dashboard)
SELECT MONTH(fecha_servicio)                                     AS mes,
       ROUND(SUM(monto_facturado), 2)                            AS total_facturado,
       ROUND(SUM(monto_pagado), 2)                               AS total_cobrado,
       ROUND(SUM(monto_pagado) / SUM(monto_facturado) * 100, 1)  AS pct_cobrado
FROM salud_oro.fact_transacciones
GROUP BY MONTH(fecha_servicio)
ORDER BY mes;

-- COMMAND ----------

-- % Aprobación por mes (meta 40%): detecta los meses con caída
SELECT MONTH(fecha_reclamo)                                                                     AS mes,
       COUNT(*)                                                                                 AS total_reclamos,
       ROUND(AVG(CASE WHEN estado_reclamo IN ('Aprobado', 'Pagado') THEN 1 ELSE 0 END) * 100, 1) AS pct_aprobacion
FROM salud_oro.fact_reclamos
GROUP BY MONTH(fecha_reclamo)
ORDER BY mes;

-- COMMAND ----------

-- ¿Qué aseguradoras rechazan más?
SELECT aseguradora,
       COUNT(*)                                                                                     AS total_reclamos,
       ROUND(AVG(CASE WHEN estado_reclamo IN ('Rechazado', 'Denegado') THEN 1 ELSE 0 END) * 100, 1) AS pct_rechazo
FROM salud_oro.fact_reclamos
GROUP BY aseguradora
ORDER BY pct_rechazo DESC;