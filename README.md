# Proyecto Integrador Data Analyst · Sector Salud (Ciclo de Ingresos – RCM)

**Guía paso a paso** para un Analista de Datos Fullstack Junior: de archivos CSV crudos a un dashboard en Power BI con alertas automáticas, usando **Databricks** y el **Modelo Medallón** (Bronce → Plata → Oro).

---
Authon jhon velasque
## Estructura de carpetas

| Carpeta | Fase | Qué contiene |
|---|---|---|
| `0_Arquitectura/` | – | `Arquitectura.drawio` (solución Databricks + Power BI + Power Automate y modelo estrella) · `GCP_original.drawio` (arquitectura del proyecto original, traducida) |
| `1_Requerimientos/` | 1 | `Requerimientos.pdf` (problemática, objetivos, KPIs, alcance) · `Diccionario.pdf` (bases, tablas, columnas y valores) |
| `datos_bronce/` | 2 | 13 CSV crudos ya traducidos (lo que se sube a Databricks) |
| `2_EDA_Python/` | 2 | `01_carga_y_EDA.py` – notebook Python: carga a Bronce + análisis exploratorio |
| `3_SQL_Databricks/` | 3 | `02_plata_SQL.sql` (Bronce → Plata) · `03_oro_SQL.sql` (Plata → Oro + KPIs de validación) |
| `4_PowerBI/` | 4 | `Guia_PowerBI.pdf` – conexión a Databricks, modelo, DAX y dashboard |
| `5_Power_Automate/` | 5 | `Guia_Alertas.pdf` – alertas e incidencias automáticas |

> Abre los `.drawio` con [app.diagrams.net](https://app.diagrams.net) o draw.io Desktop. El archivo `Arquitectura.drawio` tiene 2 páginas: *Arquitectura Databricks* y *Modelo Power BI*.

---

## Fase 1 · Requerimientos del cliente

**Problema:** una red de 2 hospitales tiene su información en sistemas distintos (con columnas diferentes e IDs repetidos), más archivos de aseguradoras. Los reportes se hacen a mano, tardan días y nadie sabe con certeza cuánto se factura vs. cuánto se cobra ni qué aseguradoras rechazan más reclamos.

1. Lee `1_Requerimientos/Requerimientos.pdf`: contexto, problemática, stakeholders, preguntas de negocio, KPIs y alcance.
2. Revisa `1_Requerimientos/Diccionario.pdf` para conocer cada tabla y columna.
3. Mira `0_Arquitectura/Arquitectura.drawio` para entender el flujo completo.

**KPIs:** Total Facturado · Total Pagado · % Cobrado · Pacientes Atendidos · Ticket Promedio · % Aprobación de Reclamos · % Rechazo · Saldo Pendiente.

---

## Fase 2 · Carga y EDA con Python (Databricks)

1. Crea tu cuenta gratis en **Databricks Free Edition**.
2. **Workspace → Import** → sube `2_EDA_Python/01_carga_y_EDA.py` y los 2 `.sql` de `3_SQL_Databricks/`.
3. Abre `01_carga_y_EDA` y ejecuta la **celda del Paso 1** (crea los esquemas `salud_bronce`, `salud_plata`, `salud_oro` y el volumen `archivos`).
4. **Catalog → workspace → salud_bronce → archivos → Upload to this volume** → sube los **13 CSV** de `datos_bronce/`.
5. Ejecuta el resto del notebook (**Run all**):
   - Carga cada CSV con pandas y lo guarda como tabla `workspace.salud_bronce.<tabla>` (todo como texto, tal como llega).
   - Perfilado: filas, nulos, duplicados, tipos, atípicos (IQR) y categorías.
6. Anota tus hallazgos (también están en `Requerimientos.pdf`, sección 9).

| Capa | Esquema | Herramienta |
|---|---|---|
| Bronce | `workspace.salud_bronce` | Python (pandas) |
| Plata | `workspace.salud_plata` | Spark SQL |
| Oro | `workspace.salud_oro` | Spark SQL |

---

## Fase 3 · Limpieza y transformación con Spark SQL

1. Ejecuta **`02_plata_SQL`** (Bronce → Plata). Para cada tabla:
   - `UNION ALL` del Hospital A y B + columna `fuente` (`hosa` / `hosb`).
   - **Modelo de Datos Común:** el Hospital B se renombra con `AS` (`codigo → id_paciente`, `p_nombre → nombre`…).
   - `DISTINCT`, `TRY_CAST` a fechas y montos, estandarización de textos.
   - **Clave única** `id + '-' + fuente` (los IDs se repiten entre hospitales).
   - `en_cuarentena = true` si falta un dato obligatorio (ej. 15 pacientes sin nombre).
2. Ejecuta **`03_oro_SQL`** (Plata → Oro):
   - `SELECT * EXCEPT (en_cuarentena, fecha_carga) ... WHERE en_cuarentena = false`.
   - Resultado: modelo estrella con `dim_departamentos`, `dim_medicos`, `dim_pacientes`, `dim_codigos_cpt`, `fact_atenciones`, `fact_transacciones`, `fact_reclamos`.
   - Las últimas celdas calculan los KPIs en SQL: **guarda esos números** para validar Power BI.

| Tabla Oro | Filas esperadas |
|---|---|
| dim_departamentos | 40 |
| dim_medicos | 55 |
| dim_pacientes | 9.985 |
| dim_codigos_cpt | 1.161 |
| fact_atenciones | 20.000 |
| fact_transacciones | 20.000 |
| fact_reclamos | 20.000 |

> El proyecto original aplicaba **SCD Tipo 2** (historial con `MERGE`). Aquí se omite para mantenerlo simple: cada ejecución recarga todo con `CREATE OR REPLACE TABLE`.

---

## Fase 4 · Power BI y dashboard ejecutivo

Sigue `4_PowerBI/Guia_PowerBI.pdf`. Resumen:

1. Databricks → **SQL Warehouses → Connection details**: copia *Server hostname* y *HTTP path*.
2. Avatar → **Settings → Developer → Access tokens** → genera un token.
3. Power BI Desktop → **Obtener datos → Databricks** → hostname + HTTP path → modo **Importar** → token.
4. Navegador: `workspace → salud_oro` → marca las 7 tablas → **Cargar**.
5. Relaciones por `clave_paciente`, `clave_departamento`, `clave_medico` + tabla **Calendario** (DAX).
6. Crea las medidas DAX y el dashboard de 1 página (tarjetas, líneas por mes, barras por departamento, anillo por estado de reclamo, tabla por aseguradora).
7. Valida contra los KPIs SQL de `03_oro_SQL` y **publica** en Power BI Service.

---

## Fase 5 · Alertas e incidencias con Power Automate

Sigue `5_Power_Automate/Guia_Alertas.pdf`. Resumen:

1. En Power BI Service, ancla la tarjeta **% Aprobación** a un panel.
2. **Administrar alertas** → regla: *por debajo de 0,40*.
3. **Usar Power Automate** → desencadenador *Cuando se desencadena una alerta controlada por datos*.
4. Acciones: **Enviar correo (Outlook)** al responsable + **Agregar fila en Excel** de incidencias.
5. Prueba forzando el umbral y verifica correo y Excel.

---

## Entregables del alumno

- [ ] Documento de requerimientos con KPIs validados con el cliente (Fase 1).
- [ ] Notebook de EDA ejecutado con conclusiones (Fase 2).
- [ ] Esquemas `salud_plata` y `salud_oro` creados en Databricks (Fase 3).
- [ ] Archivo `.pbix` con modelo, medidas DAX y dashboard publicado (Fase 4).
- [ ] Flujo de Power Automate funcionando con evidencia (captura del correo y del Excel) (Fase 5).
