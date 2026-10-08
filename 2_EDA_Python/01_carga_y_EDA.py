# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 01 · Carga y Análisis Exploratorio (EDA) con Python – Capa Bronce
# MAGIC **Fase 2 del proyecto.** Con **pandas** cargamos los CSV crudos (ya traducidos al español) como tablas Bronce
# MAGIC y los conocemos: tamaño, tipos, nulos, duplicados, valores atípicos y categorías.
# MAGIC La limpieza (Plata) y las tablas finales (Oro) se hacen después con **Spark SQL**.
# MAGIC
# MAGIC | Capa | Dónde vive | Qué contiene | Herramienta |
# MAGIC |---|---|---|---|
# MAGIC | Bronce | Volumen `workspace.salud_bronce.archivos` + tablas `workspace.salud_bronce.*` | CSV crudos, tal como llegan | Python (pandas) |
# MAGIC | Plata | Esquema `workspace.salud_plata` | Datos limpios y unificados (Hospital A + B) | Spark SQL |
# MAGIC | Oro | Esquema `workspace.salud_oro` | Tablas listas para Power BI | Spark SQL |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 1 · Crear los esquemas y el volumen (solo la primera vez)

# COMMAND ----------

CATALOGO = "workspace"  # catálogo por defecto en Databricks Free Edition
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.salud_bronce")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.salud_plata")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.salud_oro")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOGO}.salud_bronce.archivos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 2 · Subir los CSV
# MAGIC 1. Menú izquierdo **Catalog** → `workspace` → `salud_bronce` → `archivos`.
# MAGIC 2. Botón **Upload to this volume** → arrastra los **13 archivos** de la carpeta `bronce/`.
# MAGIC 3. Vuelve aquí y ejecuta la siguiente celda.

# COMMAND ----------

import pandas as pd

RUTA_BRONCE = f"/Workspace/Users/dataacademygrabacion@gmail.com/Repos/1_Proyecto_Salud_Data_Academy/datos_bronce"

TABLAS = ["departamentos_ha", "departamentos_hb", "medicos_ha", "medicos_hb",
          "pacientes_ha", "pacientes_hb", "atenciones_ha", "atenciones_hb",
          "transacciones_ha", "transacciones_hb", "reclamos_ha", "reclamos_hb", "codigos_cpt"]

bronce = {t: pd.read_csv(RUTA_BRONCE + f"/{t}.csv") for t in TABLAS}

# COMMAND ----------

import pandas as pd 
df=pd.read_csv('/Workspace/Users/dataacademygrabacion@gmail.com/Repos/1_Proyecto_Salud_Data_Academy/datos_bronce/departamentos_ha.csv')

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 2.1 · Cargar Bronce como tablas (para limpiarlas luego con SQL)
# MAGIC Se guardan **todo como texto**, tal como llegan. Los tipos (fechas, montos) se corrigen en Plata con SQL.

# COMMAND ----------

for t in TABLAS:
    df = pd.read_csv(RUTA_BRONCE + f"/{t}.csv", dtype=str)
    spark.createDataFrame(df).write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{CATALOGO}.salud_bronce.{t}")
    print(f"{CATALOGO}.salud_bronce.{t}: {len(df)} filas")

# COMMAND ----------

# conecccion a base datos 
spark.createDataFrame(df).write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{CATALOGO}.salud_bronce.departamentos_ha")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 3 · Perfilado general: filas, columnas, nulos y duplicados

# COMMAND ----------

perfil = pd.DataFrame([{
    "tabla": t,
    "filas": len(df),
    "columnas": df.shape[1],
    "celdas_nulas": int(df.isna().sum().sum()),
    "filas_duplicadas": int(df.duplicated().sum()),
} for t, df in bronce.items()])
display(perfil)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 4 · Mirar una tabla por dentro
# MAGIC Cambia el nombre de la tabla y vuelve a ejecutar.

# COMMAND ----------

df = bronce["transacciones_ha"]
df.info()
display(df.head(10))
display(df.describe().T)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 5 · Los dos hospitales NO tienen las mismas columnas
# MAGIC Por eso en Plata hay que **unificarlos** (Modelo de Datos Común).

# COMMAND ----------

print("Pacientes Hospital A:", list(bronce["pacientes_ha"].columns))
print("Pacientes Hospital B:", list(bronce["pacientes_hb"].columns))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 6 · Nulos por columna (¿qué campos vienen incompletos?)

# COMMAND ----------

for t, df in bronce.items():
    nulos = df.isna().sum()
    if nulos.any():
        print(t, nulos[nulos > 0].to_dict())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 7 · Valores atípicos en montos (método IQR)
# MAGIC Un valor es atípico si está fuera de `[Q1 - 1.5·IQR , Q3 + 1.5·IQR]`.

# COMMAND ----------

trans = pd.concat([bronce["transacciones_ha"], bronce["transacciones_hb"]])
for col in ["monto_facturado", "monto_pagado"]:
    q1, q3 = trans[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    atipicos = trans[(trans[col] < q1 - 1.5 * iqr) | (trans[col] > q3 + 1.5 * iqr)]
    print(f"{col}: min={trans[col].min():.2f} max={trans[col].max():.2f} atípicos={len(atipicos)}")

# Regla de negocio: lo pagado no debería superar lo facturado
print("Transacciones con monto_pagado > monto_facturado:", (trans.monto_pagado > trans.monto_facturado).sum())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 8 · Categorías (detectar textos inconsistentes)

# COMMAND ----------

display(bronce["codigos_cpt"]["estado_codigo"].value_counts().reset_index())   # ojo: "Sin Cambios" vs "Sin cambios"
display(bronce["reclamos_ha"]["estado_reclamo"].value_counts().reset_index())
display(bronce["atenciones_ha"]["tipo_atencion"].value_counts().reset_index())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conclusiones del EDA (anótalas para tu informe)
# MAGIC - Hospital A y B usan **nombres de columnas distintos** en pacientes → unificar en Plata.
# MAGIC - Los IDs se repiten entre hospitales (ej. `HOSP1-000001` existe en A y en B) → crear una **clave única** `id + fuente`.
# MAGIC - Hay **nulos** en `p_nombre` del Hospital B → esas filas van a **cuarentena**.
# MAGIC - `estado_codigo` tiene mayúsculas inconsistentes → estandarizar.
# MAGIC - Las fechas vienen como texto → convertir a fecha.