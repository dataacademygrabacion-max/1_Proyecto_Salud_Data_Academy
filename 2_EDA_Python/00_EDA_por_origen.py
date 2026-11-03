# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 00 · EDA por origen – conocer cada archivo antes de cargarlo
# MAGIC **Antes del notebook `01_carga_y_EDA`.** Aquí exploramos **un archivo a la vez** (departamentos, médicos,
# MAGIC pacientes, atenciones, transacciones, reclamos y códigos CPT), con cantidades y gráficos, para sacar los
# MAGIC primeros *insights*. No escribe nada en Databricks: solo lee los CSV.
# MAGIC
# MAGIC | Orden | Notebook | Qué hace |
# MAGIC |---|---|---|
# MAGIC | 1 | **00_EDA_por_origen** (este) | Exploración manual y visual de cada origen |
# MAGIC | 2 | `01_carga_y_EDA` | Carga automática a Bronce + perfilado general |
# MAGIC | 3 | `02_plata_SQL` → `03_oro_SQL` | Limpieza y tablas para Power BI |
# MAGIC
# MAGIC Usamos **seaborn** (encima de matplotlib) porque hace cada gráfico en una sola línea.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 0 · Librerías y funciones de ayuda

# COMMAND ----------

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", palette="Blues_r")
plt.rcParams["figure.figsize"] = (10, 4)

# Misma ruta que 01_carga_y_EDA; si corres el archivo en tu PC usa la carpeta local
RUTA_BRONCE = "/Workspace/Users/dataacademygrabacion@gmail.com/Repos/1_Proyecto_Salud_Data_Academy/datos_bronce"
if not os.path.exists(RUTA_BRONCE):
    RUTA_BRONCE = "../datos_bronce"

try:
    display
except NameError:  # fuera de Databricks
    display = print


def cargar(origen):
    """Une Hospital A y B de un mismo origen y agrega la columna 'hospital'."""
    a = pd.read_csv(f"{RUTA_BRONCE}/{origen}_ha.csv").assign(hospital="A")
    b = pd.read_csv(f"{RUTA_BRONCE}/{origen}_hb.csv").assign(hospital="B")
    return a, b


def resumen(df, nombre):
    """Tamaño, nulos y duplicados de una tabla."""
    print(f"{nombre}: {len(df):,} filas | {df.shape[1]} columnas | "
          f"{int(df.isna().sum().sum())} celdas nulas | {int(df.duplicated().sum())} filas duplicadas")


def a_fecha(df, columnas):
    for c in columnas:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Departamentos
# MAGIC **Pregunta:** ¿los dos hospitales tienen los mismos departamentos?

# COMMAND ----------

dep_a, dep_b = cargar("departamentos")
resumen(dep_a, "departamentos_ha")
resumen(dep_b, "departamentos_hb")

comparar = dep_a.merge(dep_b, on="id_departamento", how="outer", suffixes=("_A", "_B"))
display(comparar[["id_departamento", "nombre_A", "nombre_B"]])
print("Departamentos con distinto nombre entre A y B:", (comparar.nombre_A != comparar.nombre_B).sum())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Médicos
# MAGIC **Preguntas:** ¿cuántos médicos tiene cada hospital? ¿Qué especialidades predominan?

# COMMAND ----------

med_a, med_b = cargar("medicos")
resumen(med_a, "medicos_ha")
resumen(med_b, "medicos_hb")
medicos = pd.concat([med_a, med_b], ignore_index=True)

fig, ax = plt.subplots(1, 2, figsize=(14, 5))
sns.countplot(data=medicos, x="hospital", ax=ax[0])
ax[0].set_title("Médicos por hospital")
sns.countplot(data=medicos, y="especialidad", hue="hospital",
              order=medicos.especialidad.value_counts().index, ax=ax[1])
ax[1].set_title("Médicos por especialidad")
plt.tight_layout()
plt.show()

print("Formato de id_medico en A:", med_a.id_medico.iloc[0], "| en B:", med_b.id_medico.iloc[0])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Pacientes
# MAGIC **Preguntas:** ¿las columnas coinciden? ¿Cómo se reparten por género y edad? ¿Qué campos vienen vacíos?

# COMMAND ----------

pac_a, pac_b = cargar("pacientes")
resumen(pac_a, "pacientes_ha")
resumen(pac_b, "pacientes_hb")
print("Columnas solo en A:", sorted(set(pac_a.columns) - set(pac_b.columns)))
print("Columnas solo en B:", sorted(set(pac_b.columns) - set(pac_a.columns)))

# Para explorar juntos, renombramos B igual que A (en Plata se hace lo mismo con SQL)
pac_b = pac_b.rename(columns={"codigo": "id_paciente", "p_nombre": "nombre", "p_apellido": "apellido",
                              "s_nombre": "segundo_nombre", "fecha_actualizacion": "fecha_modificacion"})
pacientes = a_fecha(pd.concat([pac_a, pac_b], ignore_index=True), ["fecha_nacimiento"])
pacientes["edad"] = (pd.Timestamp("today") - pacientes.fecha_nacimiento).dt.days // 365

fig, ax = plt.subplots(1, 3, figsize=(16, 4))
sns.countplot(data=pacientes, x="genero", hue="hospital", ax=ax[0])
ax[0].set_title("Pacientes por género")
sns.histplot(data=pacientes, x="edad", hue="hospital", bins=20, ax=ax[1])
ax[1].set_title("Distribución de edad")
nulos = pacientes.isna().sum()
nulos[nulos > 0].plot.barh(ax=ax[2], color="#B45309")
ax[2].set_title("Celdas nulas por columna")
plt.tight_layout()
plt.show()

print("Teléfonos con formatos distintos (ejemplos):", pacientes.telefono.sample(5, random_state=1).tolist())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Atenciones
# MAGIC **Preguntas:** ¿qué tipo de atención es más común? ¿Cómo evolucionan por mes?

# COMMAND ----------

ate_a, ate_b = cargar("atenciones")
resumen(ate_a, "atenciones_ha")
resumen(ate_b, "atenciones_hb")
atenciones = a_fecha(pd.concat([ate_a, ate_b], ignore_index=True), ["fecha_atencion"])
atenciones["mes"] = atenciones.fecha_atencion.dt.to_period("M").dt.to_timestamp()

fig, ax = plt.subplots(1, 2, figsize=(16, 4))
sns.countplot(data=atenciones, y="tipo_atencion", hue="hospital",
              order=atenciones.tipo_atencion.value_counts().index, ax=ax[0])
ax[0].set_title("Atenciones por tipo")
por_mes = atenciones.groupby(["mes", "hospital"]).size().reset_index(name="atenciones")
sns.lineplot(data=por_mes, x="mes", y="atenciones", hue="hospital", marker="o", ax=ax[1])
ax[1].set_title("Atenciones por mes")
plt.tight_layout()
plt.show()

print("Rango de fechas:", atenciones.fecha_atencion.min().date(), "→", atenciones.fecha_atencion.max().date())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Transacciones (facturación)
# MAGIC **Preguntas:** ¿cuánto se factura y cuánto se cobra? ¿Hay montos que no cuadran?

# COMMAND ----------

tra_a, tra_b = cargar("transacciones")
resumen(tra_a, "transacciones_ha")
resumen(tra_b, "transacciones_hb")
trans = a_fecha(pd.concat([tra_a, tra_b], ignore_index=True), ["fecha_servicio", "fecha_pago"])
trans["mes"] = trans.fecha_servicio.dt.to_period("M").dt.to_timestamp()

display(trans[["monto_facturado", "monto_pagado"]].describe().round(2))

fig, ax = plt.subplots(1, 3, figsize=(18, 4))
sns.histplot(data=trans, x="monto_facturado", hue="hospital", bins=30, ax=ax[0])
ax[0].set_title("Distribución del monto facturado")
sns.boxplot(data=trans, x="tipo_visita", y="monto_facturado", ax=ax[1])
ax[1].set_title("Monto facturado por tipo de visita")
sns.scatterplot(data=trans.sample(2000, random_state=1), x="monto_facturado", y="monto_pagado",
                alpha=0.4, ax=ax[2])
lim = trans.monto_facturado.max()
ax[2].plot([0, lim], [0, lim], color="#B45309", linestyle="--", label="pagado = facturado")
ax[2].legend()
ax[2].set_title("Facturado vs pagado (muestra)")
plt.tight_layout()
plt.show()

mensual = trans.groupby("mes")[["monto_facturado", "monto_pagado"]].sum()
mensual.plot.bar(figsize=(14, 4), color=["#1E3A8A", "#2A78D6"], title="Facturado vs cobrado por mes")
plt.show()

print(f"% cobrado total: {trans.monto_pagado.sum() / trans.monto_facturado.sum():.1%}")
print("Pagado > facturado:", (trans.monto_pagado > trans.monto_facturado).sum(), "transacciones")
print("Pago antes del servicio:", (trans.fecha_pago < trans.fecha_servicio).sum(), "transacciones")
print("id_medico de transacciones que existe en el catálogo de médicos:",
      f"{trans.id_medico.isin(medicos.id_medico).mean():.0%}", "(ej.", trans.id_medico.iloc[0], "vs", medicos.id_medico.iloc[0], ")")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · Reclamos a aseguradoras
# MAGIC **Preguntas:** ¿qué % se aprueba (meta 40%)? ¿Qué aseguradora rechaza más?
# MAGIC ¿Cuánto paga el paciente y cuánto la aseguradora?
# MAGIC
# MAGIC Regla del costo: **reclamado = copago + deducible + coaseguro (paciente) + pagado (aseguradora)**.
# MAGIC La aseguradora solo paga cuando el estado es `Pagado`.

# COMMAND ----------

rec_a, rec_b = cargar("reclamos")
resumen(rec_a, "reclamos_ha")
resumen(rec_b, "reclamos_hb")
reclamos = a_fecha(pd.concat([rec_a, rec_b], ignore_index=True), ["fecha_reclamo"])
reclamos["aprobado"] = reclamos.estado_reclamo.isin(["Aprobado", "Pagado"])
reclamos["rechazado"] = reclamos.estado_reclamo.isin(["Rechazado", "Denegado"])
reclamos["paga_paciente"] = reclamos.copago + reclamos.deducible + reclamos.coaseguro
reclamos["mes"] = reclamos.fecha_reclamo.dt.to_period("M").dt.to_timestamp()

fig, ax = plt.subplots(1, 2, figsize=(16, 4))
sns.countplot(data=reclamos, x="estado_reclamo", hue="hospital", ax=ax[0])
ax[0].set_title("Reclamos por estado")
por_aseg = reclamos.groupby("aseguradora").rechazado.mean().sort_values()
sns.barplot(x=por_aseg.values, y=por_aseg.index, ax=ax[1])
ax[1].set_title("% de rechazo por aseguradora")
plt.tight_layout()
plt.show()

aprob_mes = reclamos.groupby("mes").aprobado.mean()
ax = aprob_mes.plot(marker="o", figsize=(14, 4), title="% de aprobación por mes")
ax.axhline(0.40, color="#B45309", linestyle="--", label="meta 40%")
ax.legend()
plt.show()

# Quién paga cada reclamo pagado
pagados = reclamos[reclamos.estado_reclamo == "Pagado"]
reparto = pagados.groupby("aseguradora")[["monto_pagado", "copago", "deducible", "coaseguro"]].sum()
ax = reparto.plot.barh(stacked=True, figsize=(12, 4), title="Reclamos pagados: aseguradora vs paciente (USD)")
ax.legend(bbox_to_anchor=(1, 1))
plt.tight_layout()
plt.show()

print(f"% aprobación global: {reclamos.aprobado.mean():.1%}")
print(f"En reclamos pagados, el paciente cubre en promedio "
      f"{pagados.paga_paciente.sum() / pagados.monto_reclamado.sum():.1%} del costo")
display(pd.crosstab(reclamos.aseguradora, reclamos.tipo_pagador))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 · Códigos CPT (catálogo de procedimientos)
# MAGIC **Preguntas:** ¿qué categorías tienen más procedimientos? ¿Los textos están estandarizados?

# COMMAND ----------

cpt = pd.read_csv(f"{RUTA_BRONCE}/codigos_cpt.csv")
resumen(cpt, "codigos_cpt")

fig, ax = plt.subplots(1, 2, figsize=(16, 4))
top = cpt.categoria_procedimiento.value_counts().head(10)
sns.barplot(x=top.values, y=top.index, ax=ax[0])
ax[0].set_title("Top 10 categorías de procedimientos")
sns.countplot(data=cpt, x="estado_codigo", ax=ax[1])
ax[1].set_title("estado_codigo (ojo con mayúsculas)")
plt.tight_layout()
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insights iniciales (complétalos con lo que ves en los gráficos)
# MAGIC | Origen | Lo que encontramos | Qué haremos |
# MAGIC |---|---|---|
# MAGIC | Departamentos | Mismos IDs en A y B | Clave `id + fuente` |
# MAGIC | Médicos | El catálogo usa `H1-PROV0001` pero los hechos usan `PROV0001`: 0% de coincidencia | Quitar el prefijo `H1-`/`H2-` en Plata para poder relacionarlos |
# MAGIC | Pacientes | Hospital B usa otros nombres de columna (`codigo`, `p_nombre`…) y tiene nulos | Modelo de datos común + cuarentena |
# MAGIC | Atenciones | Distribución por tipo y tendencia mensual | Relacionar con calendario |
# MAGIC | Transacciones | Hay pagos mayores a lo facturado y pagos antes del servicio | Reglas de calidad / cuarentena |
# MAGIC | Reclamos | % aprobación cerca de la meta del 40% y baja en oct-2026 | KPI y alerta en Power BI |
# MAGIC | Códigos CPT | `estado_codigo` con mayúsculas inconsistentes | Estandarizar en Plata |
# MAGIC
# MAGIC ### ➡️ Siguiente paso
# MAGIC Abre **`01_carga_y_EDA`** y ejecútalo completo (*Run all*): carga estos mismos CSV como tablas Bronce
# MAGIC y hace el perfilado general automático (nulos, duplicados, atípicos y categorías).
