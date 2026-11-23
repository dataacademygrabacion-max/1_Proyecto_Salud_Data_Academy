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
| `4_PowerBI/` | 4 | `Guia_PowerBI.pdf` – conexión, modelo, DAX, diseño y drill del dashboard · `dashboard_salud.html` – prototipo interactivo a replicar |
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

| Tabla Oro | Filas esperadas (2025–2026) |
|---|---|
| dim_departamentos | 40 |
| dim_medicos | 55 |
| dim_pacientes | 9,985 |
| dim_codigos_cpt | 1,161 |
| fact_atenciones | 38,005 |
| fact_transacciones | 38,005 |
| fact_reclamos | 38,005 |

> El proyecto original aplicaba **SCD Tipo 2** (historial con `MERGE`). Aquí se omite para mantenerlo simple: cada ejecución recarga todo con `CREATE OR REPLACE TABLE`.

---

## Fase 4 · Power BI y dashboard ejecutivo

Sigue `4_PowerBI/Guia_PowerBI.pdf`. Resumen:

1. Databricks → **SQL Warehouses → Connection details**: copia *Server hostname* y *HTTP path*.
2. Avatar → **Settings → Developer → Access tokens** → genera un token.
3. Power BI Desktop → **Obtener datos → Databricks** → hostname + HTTP path → modo **Importar** → token.
4. Navegador: `workspace → salud_oro` → marca las 7 tablas → **Cargar**.
5. Tablas de apoyo **Calendario** y **Hospital** (DAX) + relaciones por fechas, `fuente`, `clave_paciente`, `clave_departamento`, `clave_medico`.
6. Crea las medidas DAX y el dashboard de 1 página: 5 tarjetas, **facturado vs. cobrado por mes** (drill a días), **% aprobación por mes** con meta 40% (drill a semanas), **% rechazo por aseguradora** y facturación por departamento. Prototipo de referencia: `4_PowerBI/dashboard_salud.html`.
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

---

## Anexos · Hallazgos de Calidad, Lógica de Negocio y Guía de Análisis

### Anexo 1 · Hallazgos de Limpieza y Cuarentena en Capa Plata

En `3_SQL_Databricks/02_plata_SQL.sql` se aplican reglas de calidad sobre los datos crudos de `datos_bronce/` sin borrar registros inválidos: los duplicados exactos se eliminan con `SELECT DISTINCT` y las inconsistencias (nulos, fechas invertidas, montos inválidos y registros huérfanos) se marcan con `en_cuarentena = true` para filtrarse automáticamente al construir la capa Oro (`WHERE en_cuarentena = false`).

#### Resumen por tabla (Bronce → Plata → Oro)

| Tabla | Bronce (CSV) | Duplicados (`DISTINCT`) | En Cuarentena | Motivos de cuarentena / limpieza | Oro (Limpias) |
|---|---:|---:|---:|---|---:|
| **`departamentos`** | 40 | 0 | **0** | — | 40 |
| **`medicos`** | 55 | 0 | **0** | Limpieza de prefijo `H1-`/`H2-` con `split_part` | 55 |
| **`codigos_cpt`** | 1,161 | 0 | **0** | 51 textos `"Sin cambios"` estandarizados a `"Sin Cambios"` | 1,161 |
| **`pacientes`** | 10,000 | 0 | **15** | 15 con `nombre` nulo en Hospital B + unificación de columnas | 9,985 |
| **`atenciones`** | 38,009 | 1 | **3** | 1 huérfano paciente · 1 huérfano médico · 1 `tipo_atencion` nulo | 38,005 |
| **`transacciones`** | 38,009 | 1 | **3** | 1 huérfano atención · 1 fecha invertida · 1 monto pagado > facturado | 38,005 |
| **`reclamos`** | 38,009 | 0 | **4** | 1 huérfano transacción · 1 fecha invertida · 1 monto pagado > reclamado · 1 `estado_reclamo` nulo | 38,005 |
| **TOTAL** | **125,283** | **2** | **25** | **4 huérfanos · 2 fechas invertidas · 2 montos inválidos · 17 nulos** | **125,256** |

> Los 10 registros en cuarentena y 2 duplicados en las tablas de hechos fueron incluidos con fines didácticos (IDs `ENC999001`–`003`, `TRANS999001`–`003`, `CLAIM999001`–`004` y duplicados de `ENC000001` / `TRANS000001`) para demostrar en vivo cómo la capa Plata protege la capa Oro sin alterar en nada los KPIs finales.

---

### Anexo 2 · Aplicación de la Clave Subrogada / Compuesta (`id + '-' + fuente`)

Cada hospital genera sus propios correlativos de manera independiente, por lo que **el mismo ID corresponde a personas distintas** en Hospital A (`hosa`) y Hospital B (`hosb`):

| Entidad | ID de origen repetido | Hospital A (`hosa`) | Hospital B (`hosb`) | Clave única en Plata |
|---|---|---|---|---|
| **Pacientes** *(5,000 colisiones)* | `HOSP1-000001` | **Rick Russo** (`1937-06-04`) | **Victoria Gamble** (`1994-12-24`) | `HOSP1-000001-hosa` / `HOSP1-000001-hosb` |
| **Pacientes** | `HOSP1-000002` | **Gregory Graham** (`1937-06-10`) | **Meghan West** (`2009-04-03`) | `HOSP1-000002-hosa` / `HOSP1-000002-hosb` |
| **Médicos** *(25 colisiones)* | `PROV0001` | **Brandon Harper** (Oncología) | **Wanda Ramos** (Pediatría) | `PROV0001-hosa` / `PROV0001-hosb` |
| **Médicos** | `PROV0002` | **Luke Clark** (Emergencia) | **Steven Roach** (Radiología) | `PROV0002-hosa` / `PROV0002-hosb` |

**Por qué es indispensable:** si se hiciera un `JOIN` usando únicamente `id_paciente = 'HOSP1-000001'`, se mezclarían las atenciones y facturas de Rick Russo con las de Victoria Gamble, generando duplicación de filas y montos inflados (producto cartesiano). Concatenar la fuente (`id + '-' + fuente`) garantiza unicidad 100% en el modelo estrella.

---

### Anexo 3 · Lógica de Negocio y Cómo Analizar las Tablas de Hechos (`atenciones`, `transacciones` y `reclamos`)

#### 3.1 Reglas de negocio y aseguradoras
- **Línea de tiempo coherente:**
  $$\text{fecha\_atencion} = \text{fecha\_visita} = \text{fecha\_servicio} \le \text{fecha\_reclamo} \quad \text{y} \quad \text{fecha\_servicio} \le \text{fecha\_pago}$$
- **Relación 1 a 1:** cada transacción (`fact_transacciones`) tiene su reclamo asociado (`fact_reclamos`) por `clave_transaccion` y ambos apuntan a su atención (`fact_atenciones`) por `clave_atencion`.
- **Aseguradoras (4 peruanas + 2 internacionales):**
  - **Nacionales (`tipo_pagador = 'Nacional'`):** Pacífico Seguros, Rímac Seguros, La Positiva, Interseguro.
  - **Internacionales (`tipo_pagador = 'Internacional'`):** Bupa, Mapfre.

#### 3.2 Lógica financiera: ¿quién paga y quién recibe el dinero?
En el ciclo de ingresos hospitalario (RCM), **quien recibe el dinero es el Hospital/Clínica**:
- **`fact_transacciones`** muestra la **factura total** del hospital (`monto_facturado`) y el **total efectivamente cobrado** (`monto_pagado`).
- **`fact_reclamos`** muestra el **desglose entre Paciente y Aseguradora** (`copago`, `deducible`, `coaseguro` y `monto_pagado` de la aseguradora).

$$\text{monto\_facturado} = \text{monto\_reclamado} = \underbrace{(\text{copago} + \text{deducible} + \text{coaseguro})}_{\text{Paga el Paciente al Hospital}} + \underbrace{\text{Pago Aseguradora}}_{\text{Solo si estado\_reclamo = Pagado}}$$

$$\text{transacciones.monto\_pagado} = (\text{copago} + \text{deducible} + \text{coaseguro}) + \text{reclamos.monto\_pagado}$$

- Si `estado_reclamo = 'Pagado'`: el hospital cobró el **100%** (parte del paciente + parte de la aseguradora → **brecha = \$0.00**).
- Si `estado_reclamo` es `Aprobado`, `Pendiente`, `Rechazado` o `Denegado`: la aseguradora aún pagó **\$0.00**; el hospital solo cobró la parte del paciente y la diferencia queda como **brecha / saldo pendiente**.

#### 3.3 Casos particulares reales para validar en tu data (Hospital A)

| Concepto | Caso 1 · **Pagado** (`TRANS000007` / `CLAIM000007`) | Caso 2 · **Rechazado** (`TRANS000005` / `CLAIM000005`) |
|---|---:|---:|
| **Aseguradora** | Mapfre (Internacional) | Rímac Seguros (Nacional) |
| **`fecha_atencion` → `fecha_reclamo`** | `2025-07-24` → `2025-08-05` (+12 días) | `2025-04-11` → `2025-04-12` (+1 día) |
| **`monto_facturado` = `monto_reclamado`** | **\$724.59** | **\$729.37** |
| `copago` + `deducible` + `coaseguro` | \$48.35 + \$91.50 + \$87.71 = **\$227.56** | \$37.20 + \$44.09 + \$97.21 = **\$178.50** |
| **Paga la Aseguradora (`reclamos.monto_pagado`)** | **\$497.03** | **\$0.00** *(reclamo rechazado)* |
| **Total cobrado por el Hospital (`transacciones.monto_pagado`)** | **\$724.59** (`227.56 + 497.03`) | **\$178.50** (`178.50 + 0.00`) |
| **Brecha / Saldo pendiente** | **\$0.00** (100% cobrado) | **\$550.87** (cartera impaga por rechazo) |

#### 3.4 Consulta SQL ejemplo para analizar un caso particular en Databricks

```sql
SELECT
    t.clave_transaccion,
    r.clave_reclamo,
    r.aseguradora,
    r.tipo_pagador,
    r.estado_reclamo,
    a.fecha_atencion,
    r.fecha_reclamo,
    DATEDIFF(r.fecha_reclamo, a.fecha_atencion)                      AS dias_hasta_reclamo,
    t.monto_facturado,
    ROUND(r.copago + r.deducible + r.coaseguro, 2)                   AS pago_paciente,
    r.monto_pagado                                                   AS pago_aseguradora,
    t.monto_pagado                                                   AS total_cobrado_hospital,
    ROUND(t.monto_facturado - t.monto_pagado, 2)                     AS brecha_por_cobrar
FROM workspace.salud_oro.fact_transacciones t
JOIN workspace.salud_oro.fact_reclamos   r ON t.clave_transaccion = r.clave_transaccion
JOIN workspace.salud_oro.fact_atenciones a ON t.clave_atencion    = a.clave_atencion
WHERE t.clave_transaccion IN ('TRANS000007-hosa', 'TRANS000005-hosa');
```

#### 3.5 Resumen financiero global esperado en Oro (2025–2026 · 38,005 atenciones)

| Indicador | Monto | % sobre Facturado |
|---|---:|---:|
| **Total Facturado** (`SUM(fact_transacciones.monto_facturado)`) | **\$19,990,596.94** | 100.00% |
| Cobrado al Paciente (`SUM(copago + deducible + coaseguro)`) | \$6,537,640.01 | 32.70% |
| Cobrado a Aseguradoras (`SUM(fact_reclamos.monto_pagado)`) | \$2,679,828.39 | 13.41% |
| **Total Cobrado por el Hospital** (`SUM(fact_transacciones.monto_pagado)`) | **\$9,217,468.40** | **46.11%** |
| **Brecha / Saldo Pendiente** | **\$10,773,128.54** | **53.89%** |
