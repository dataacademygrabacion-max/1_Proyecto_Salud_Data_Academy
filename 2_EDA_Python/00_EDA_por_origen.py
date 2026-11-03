# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 00 · EDA paso a paso – de un archivo a todos
# MAGIC **Antes del notebook `01_carga_y_EDA`.** Aprendemos a explorar datos **de menos a más**:
# MAGIC
# MAGIC 1. **Parte 1:** exploramos **un solo archivo** (`transacciones_ha.csv`) a mano, paso a paso.
# MAGIC 2. **Parte 2:** juntamos esos pasos en **una función** `explorar()`.
# MAGIC 3. **Parte 3:** usamos la función con **los dos orígenes** (Hospital A y Hospital B) y los comparamos.
# MAGIC 4. **Parte 4:** con un `for` la aplicamos a **todos los archivos**.
# MAGIC
# MAGIC En cada análisis seguimos siempre el mismo patrón:
# MAGIC **① conectar (leer el CSV) → ② crear una tabla resumen → ③ graficar esa tabla.**
# MAGIC
# MAGIC Después seguimos con `01_carga_y_EDA`, que hace la carga a Bronce de forma automática.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 0 · Librerías y ruta de los archivos

# COMMAND ----------

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

# Misma ruta que 01_carga_y_EDA (si lo corres en tu PC, usa la carpeta local)
RUTA_BRONCE = "/Workspace/Users/dataacademygrabacion@gmail.com/Repos/1_Proyecto_Salud_Data_Academy/datos_bronce"
if not os.path.exists(RUTA_BRONCE):
    RUTA_BRONCE = "../datos_bronce"

try:
    display  # existe en Databricks
except NameError:
    display = print

# COMMAND ----------

# MAGIC %md
# MAGIC # Parte 1 · Explorar UN archivo a mano
# MAGIC Trabajamos con las transacciones (facturación) del **Hospital A**.
# MAGIC Cada celda responde una sola pregunta.

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.1 · ¿Cómo se ven los datos?

# COMMAND ----------

df = pd.read_csv(f"{RUTA_BRONCE}/transacciones_ha.csv")
df.head()

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.2 · ¿Cuántas filas y columnas tiene?

# COMMAND ----------

print("Filas:", df.shape[0])
print("Columnas:", df.shape[1])

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.3 · ¿Qué tipo de dato tiene cada columna?
# MAGIC Ojo: las fechas llegan como `object` (texto). En Plata las convertiremos a fecha con SQL.

# COMMAND ----------

df.dtypes

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.4 · ¿Hay valores nulos o filas duplicadas?
# MAGIC Es como hacer en SQL: `SELECT COUNT(*) FROM tabla WHERE columna IS NULL`.

# COMMAND ----------

print("Nulos por columna:")
print(df.isna().sum())
print("Filas duplicadas:", df.duplicated().sum())

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.5 · ¿Cómo son los montos? (mínimo, promedio, máximo)
# MAGIC Es como `SELECT MIN(monto), AVG(monto), MAX(monto) FROM tabla`.

# COMMAND ----------

df[["monto_facturado", "monto_pagado"]].describe().round(2)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.6 · Tabla resumen por categoría → gráfico
# MAGIC **Tabla resumen** = un `GROUP BY` de SQL:
# MAGIC ```sql
# MAGIC SELECT tipo_visita, COUNT(*) AS transacciones, SUM(monto_facturado) AS facturado, SUM(monto_pagado) AS cobrado
# MAGIC FROM transacciones_ha GROUP BY tipo_visita
# MAGIC ```

# COMMAND ----------

resumen_visita = (
    df.groupby("tipo_visita")
      .agg(transacciones=("id_transaccion", "count"),
           facturado=("monto_facturado", "sum"),
           cobrado=("monto_pagado", "sum"))
      .reset_index()
      .sort_values("transacciones", ascending=False)
)
resumen_visita["pct_cobrado"] = (resumen_visita["cobrado"] / resumen_visita["facturado"]).round(3)
display(resumen_visita.round(2))

# COMMAND ----------

# Gráfico hecho a partir de la tabla resumen
sns.barplot(data=resumen_visita, x="tipo_visita", y="transacciones")
plt.title("Transacciones por tipo de visita")
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.7 · Tabla resumen por rangos de monto → gráfico
# MAGIC `pd.cut` agrupa los montos en rangos, como un `CASE WHEN` en SQL:
# MAGIC ```sql
# MAGIC SELECT CASE WHEN monto_facturado < 250 THEN '0-250' WHEN ... END AS rango, COUNT(*)
# MAGIC FROM transacciones_ha GROUP BY rango
# MAGIC ```

# COMMAND ----------

df["rango_facturado"] = pd.cut(df["monto_facturado"], bins=[0, 250, 500, 750, 1000],
                               labels=["0-250", "250-500", "500-750", "750-1000"])

resumen_rango = df.groupby("rango_facturado", observed=True).size().reset_index(name="transacciones")
display(resumen_rango)

# COMMAND ----------

sns.barplot(data=resumen_rango, x="rango_facturado", y="transacciones")
plt.title("¿Cuánto se factura por transacción?")
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.8 · Una regla de negocio: ¿lo pagado supera lo facturado?
# MAGIC No debería pasar. Si pasa, es un dato a revisar (irá a cuarentena o se corrige en Plata).

# COMMAND ----------

pagado_mayor = df[df["monto_pagado"] > df["monto_facturado"]]
print("Transacciones con pagado > facturado:", len(pagado_mayor))
print(f"Porcentaje: {len(pagado_mayor) / len(df):.1%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### ✍️ Insights de la Parte 1
# MAGIC - El archivo tiene ~19 mil transacciones y **no tiene nulos ni duplicados**.
# MAGIC - Las fechas vienen como **texto** → hay que convertirlas.
# MAGIC - Los montos facturados van de ~$50 a ~$1,000.
# MAGIC - Hay transacciones donde **se pagó más de lo facturado** → problema de calidad.
# MAGIC
# MAGIC 🤔 **¿Y si tenemos 13 archivos?** Repetir estas 8 celdas 13 veces es mucho trabajo… ¡hagamos una función!

# COMMAND ----------

# MAGIC %md
# MAGIC # Parte 2 · Convertir los pasos en una función
# MAGIC La función `explorar()` hace lo mismo que la Parte 1, pero para **cualquier** tabla:
# MAGIC - Resume filas, columnas, nulos y duplicados.
# MAGIC - Describe las columnas **numéricas** (mín, promedio, máx).
# MAGIC - Para cada columna de **texto con pocas categorías** (10 o menos): crea la **tabla resumen** y luego su **gráfico**.

# COMMAND ----------

def explorar(df, nombre, graficos=True):
    print("=" * 60)
    print(f"📄 {nombre}")
    print("=" * 60)

    # 1. Tamaño, nulos y duplicados
    print("Filas:", df.shape[0], "| Columnas:", df.shape[1])
    print("Celdas nulas:", df.isna().sum().sum(), "| Filas duplicadas:", df.duplicated().sum())

    nulos = df.isna().sum()
    if nulos.sum() > 0:
        print("Columnas con nulos:", nulos[nulos > 0].to_dict())

    # 2. Columnas numéricas
    numericas = df.select_dtypes(include="number").columns
    if len(numericas) > 0:
        display(df[numericas].describe().round(2))

    # 3. Columnas de texto con pocas categorías: tabla resumen → gráfico
    categorias = [c for c in df.select_dtypes(include="object").columns if df[c].nunique() <= 10]
    for col in categorias:
        resumen = df.groupby(col).size().reset_index(name="cantidad").sort_values("cantidad", ascending=False)
        display(resumen)

        if graficos:
            sns.barplot(data=resumen, x="cantidad", y=col)
            plt.title(f"{nombre} · {col}")
            plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Probamos la función con el mismo archivo de la Parte 1
# MAGIC Debe dar los mismos números que vimos a mano.

# COMMAND ----------

explorar(df, "transacciones_ha")

# COMMAND ----------

# MAGIC %md
# MAGIC # Parte 3 · Usar la función con los dos orígenes (Hospital A y B)
# MAGIC Ahora exploramos los **reclamos** de los dos hospitales con una sola línea cada uno.

# COMMAND ----------

reclamos_a = pd.read_csv(f"{RUTA_BRONCE}/reclamos_ha.csv")
reclamos_b = pd.read_csv(f"{RUTA_BRONCE}/reclamos_hb.csv")

explorar(reclamos_a, "reclamos_ha", graficos=False)
explorar(reclamos_b, "reclamos_hb", graficos=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3.1 · Comparar A vs B: tabla resumen → gráfico
# MAGIC Unimos las dos tablas con `pd.concat` (como un `UNION ALL` en SQL) y agregamos la columna `hospital`.
# MAGIC Luego: `SELECT hospital, estado_reclamo, COUNT(*) FROM reclamos GROUP BY hospital, estado_reclamo`.

# COMMAND ----------

reclamos_a["hospital"] = "A"
reclamos_b["hospital"] = "B"
reclamos = pd.concat([reclamos_a, reclamos_b], ignore_index=True)

resumen_estado = reclamos.groupby(["hospital", "estado_reclamo"]).size().reset_index(name="reclamos")
display(resumen_estado)

# COMMAND ----------

sns.barplot(data=resumen_estado, x="estado_reclamo", y="reclamos", hue="hospital")
plt.title("Reclamos por estado: Hospital A vs B")
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3.2 · KPI: % de aprobación por hospital (meta 40%)
# MAGIC Un reclamo cuenta como aprobado si su estado es `Aprobado` o `Pagado`.

# COMMAND ----------

reclamos["aprobado"] = reclamos["estado_reclamo"].isin(["Aprobado", "Pagado"])

resumen_aprobacion = (
    reclamos.groupby("hospital")
            .agg(reclamos=("id_reclamo", "count"), aprobados=("aprobado", "sum"))
            .reset_index()
)
resumen_aprobacion["pct_aprobacion"] = (resumen_aprobacion["aprobados"] / resumen_aprobacion["reclamos"]).round(3)
display(resumen_aprobacion)

# COMMAND ----------

sns.barplot(data=resumen_aprobacion, x="hospital", y="pct_aprobacion")
plt.axhline(0.40, color="orange", linestyle="--", label="Meta 40%")
plt.title("% de aprobación por hospital")
plt.legend()
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3.3 · ¿Quién paga una atención? Ejemplo con un reclamo pagado
# MAGIC **monto reclamado = copago + deducible + coaseguro (paga el paciente) + monto pagado (paga la aseguradora)**

# COMMAND ----------

ejemplo = reclamos[reclamos["estado_reclamo"] == "Pagado"].iloc[0]
paciente = ejemplo["copago"] + ejemplo["deducible"] + ejemplo["coaseguro"]

print("Reclamo:", ejemplo["id_reclamo"], "-", ejemplo["aseguradora"])
print(f"Monto reclamado:      ${ejemplo['monto_reclamado']:,.2f}")
print(f"  Paga el paciente:   ${paciente:,.2f}  (copago + deducible + coaseguro)")
print(f"  Paga la aseguradora: ${ejemplo['monto_pagado']:,.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC # Parte 4 · Todos los archivos con un `for`
# MAGIC La misma función, ahora en bucle. Dejamos `graficos=False` para que la salida no sea enorme;
# MAGIC cámbialo a `True` si quieres ver todos los gráficos.

# COMMAND ----------

ARCHIVOS = ["departamentos_ha", "departamentos_hb", "medicos_ha", "medicos_hb",
            "pacientes_ha", "pacientes_hb", "atenciones_ha", "atenciones_hb",
            "transacciones_ha", "transacciones_hb", "reclamos_ha", "reclamos_hb", "codigos_cpt"]

for archivo in ARCHIVOS:
    tabla = pd.read_csv(f"{RUTA_BRONCE}/{archivo}.csv")
    explorar(tabla, archivo, graficos=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✍️ Insights finales (anótalos para tu informe)
# MAGIC | Archivo | Lo que encontramos | Qué haremos en Plata (SQL) |
# MAGIC |---|---|---|
# MAGIC | Pacientes | El Hospital B usa otros nombres de columna (`codigo`, `p_nombre`…) y tiene nulos | Unificar columnas y mandar nulos a cuarentena |
# MAGIC | Médicos | El catálogo usa `H1-PROV0001`, pero las transacciones usan `PROV0001` | Quitar el prefijo para poder relacionarlos |
# MAGIC | Transacciones | Pagos mayores a lo facturado | Regla de calidad |
# MAGIC | Reclamos | % de aprobación cerca de la meta del 40% | KPI y alerta en Power BI |
# MAGIC | Códigos CPT | `estado_codigo` con mayúsculas distintas ("Sin Cambios" / "Sin cambios") | Estandarizar texto |
# MAGIC | Todos | Fechas como texto | Convertir con `TRY_CAST(... AS DATE)` |
# MAGIC
# MAGIC ### ➡️ Siguiente paso
# MAGIC Abre **`01_carga_y_EDA`** y ejecútalo completo (*Run all*): carga estos mismos archivos como tablas Bronce
# MAGIC en Databricks y hace el perfilado general de forma automática.
