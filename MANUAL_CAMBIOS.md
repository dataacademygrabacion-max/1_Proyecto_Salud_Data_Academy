# Manual de cambios · Datos 2025–2026

**Fecha del cambio:** 09/10/2026
**Alcance:** solo los CSV de origen (`datos_bronce/`). No se modificaron el `.pbix`, el notebook de Python ni los SQL.

---

## 1. Por qué el tablero salía en blanco

El modelo de Power BI filtra todo por `dim_calendario`, que va del **01/01/2025 al 31/12/2026**:

| Tabla de hechos | Relación con el calendario | Fechas en Power BI antes del cambio | Resultado |
|---|---|---|---|
| `fact_transacciones` | `fecha_servicio` | 2025-01-01 → 2026-10-08 (ya recargada) | ✅ se ve |
| `fact_reclamos` | `fecha_reclamo` | **2024**-01-01 → **2024**-11-06 (sin recargar) | ❌ % Aprobación y % Rechazo en blanco |
| `fact_atenciones` | `fecha_atencion` | **2020** → **2024** | ❌ fuera del calendario |

**Causa:** en Databricks solo se recargaron las transacciones. Los reclamos seguían con fechas de 2024 y las atenciones con fechas de 2020 a 2024, así que al filtrar por *Año = 2025* no quedaba ningún reclamo.

---

## 2. Archivos modificados

Los originales quedaron respaldados en `datos_bronce_backup_2024/`.

| Archivo | Filas antes | Filas ahora | Cambio |
|---|---|---|---|
| `transacciones_ha.csv` | 10 000 | 18 946 | 2024→2025 y 8 946 filas nuevas de 2026 |
| `transacciones_hb.csv` | 10 000 | 19 059 | 2024→2025 y 9 059 filas nuevas de 2026 |
| `reclamos_ha.csv` | 10 000 | 18 946 | 2024→2025 y 8 946 filas nuevas de 2026 |
| `reclamos_hb.csv` | 10 000 | 19 059 | 2024→2025 y 9 059 filas nuevas de 2026 |
| `atenciones_ha.csv` | 10 000 | 18 946 | Fechas alineadas a 2025 y 8 946 filas nuevas de 2026 |
| `atenciones_hb.csv` | 10 000 | 19 059 | Fechas alineadas a 2025 y 9 059 filas nuevas de 2026 |

Los catálogos (`pacientes`, `medicos`, `departamentos` y `codigos_cpt`) **no cambian**: los datos nuevos solo usan pacientes, médicos, departamentos, pagadores y códigos que ya existían.

---

## 3. Reglas aplicadas por tabla

### 3.1 Transacciones (facturación)
- **Datos de 2025:** a todas las fechas que empezaban con `2024-` se les cambió el año a `2025-`. El `2024-02-29` pasó a `2025-02-28`, porque 2025 no es bisiesto. Los montos no cambian.
- **Datos de 2026 (01/01 al 08/10):**
  - Cada fila nueva es una copia aleatoria de una fila real (montos, paciente, médico, departamento, pagador, CPT y CIE).
  - Hay unas 1 000 filas por mes en cada hospital. Octubre es proporcional a los 8 días transcurridos.
  - IDs nuevos: `TRANS010001…`. Cada transacción apunta a su propio reclamo (`CLAIM010001…`) y a su propia atención (`ENC010001…`).
  - Fechas: `fecha_visita` = `fecha_servicio`; `fecha_pago` cae entre 0 y 45 días después del servicio. Ninguna fecha pasa del 08/10/2026.

### 3.2 Reclamos
- **Datos de 2025:** mismo cambio de 2024 a 2025.
- **Datos de 2026:**
  - Hay un reclamo por cada transacción nueva, con el mismo paciente, atención, médico y departamento.
  - `fecha_reclamo` cae entre 0 y 20 días después del servicio, sin pasar de hoy.
  - De enero a septiembre, el estado del reclamo sale de la distribución original (aprobación ≈ 40%).
  - **Octubre 2026:** el estado se forzó para que la aprobación quede **por debajo del 40%**: Aprobado 17%, Pagado 15%, Pendiente 22%, Rechazado 24%, Denegado 22%.

### 3.2.1 Montos de reclamos (corrección 02/11/2026)
Antes los montos eran aleatorios (45% de reclamos con `monto_pagado` > `monto_reclamado`, rechazados con pago). Ahora, en todas las filas:
- `copago` (fijo) y `deducible` se conservan, topados a `monto_reclamado`.
- `coaseguro` = % × (`monto_reclamado` − `deducible` − `copago`): Medicare 20%, Medicaid 5%, privadas 10/20/30%.
- `monto_pagado` (lo que pagó la aseguradora) = `monto_reclamado` − `copago` − `deducible` − `coaseguro` **solo si** `estado_reclamo = Pagado`; en cualquier otro estado es 0.
- `tipo_pagador`: Medicare/Medicaid = `Público`; Aetna, BlueCross y UnitedHealthcare = `Privado`.
- Estados y fechas no cambian, así que % Aprobación y % Rechazo siguen iguales.

### 3.3 Atenciones
- **Datos de 2025:**
  - Cada atención que tiene facturación toma la fecha de su primera transacción. Así, `fecha_atencion` coincide con `fecha_servicio`.
  - Las atenciones sin facturar reciben una fecha aleatoria dentro del mismo rango (01/01/2025 al 06/11/2025).
- **Datos de 2026:** hay una atención por cada transacción nueva (`ENC010001…`). Usa la misma fecha, paciente, médico, departamento y procedimiento que la transacción. `tipo_atencion` se toma de una atención real.
- **Fechas de auditoría:** `fecha_insercion` cae entre 0 y 3 días después de la atención, y `fecha_modificacion` entre 0 y 30 días después de la inserción.

---

## 4. Cómo cargar los cambios (paso a paso)

1. **Databricks → Catalog → workspace → salud_bronce → archivos:** sube y reemplaza estos **6 CSV**:
   `transacciones_ha/hb`, `reclamos_ha/hb`, `atenciones_ha/hb`.
2. Ejecuta `01_carga_y_EDA` (Run all) para recargar las tablas de Bronce.
3. Ejecuta `02_plata_SQL` (Bronce → Plata).
4. Ejecuta `03_oro_SQL` (Plata → Oro).
5. **Power BI Desktop → Inicio → Actualizar.**

> ⚠️ Si actualizas una sola tabla (como pasó con transacciones), las demás quedan desfasadas y el tablero vuelve a salir en blanco. Siempre recarga las tres tablas de hechos.

---

## 5. Valores esperados para validar

| KPI | Año 2025 | Año 2026 (al 08/10) |
|---|---|---|
| Total Facturado | $10.49 mill. | $9.50 mill. |
| Total Cobrado | $8.20 mill. | $7.36 mill. |
| % Cobrado | 78.1% | 77.5% |
| Pacientes Atendidos | 8 619 | 6 960 |
| Total Reclamos | 20 000 | 18 005 |
| % Aprobación (año) | 40.4% | 39.6% |
| Atenciones | 20 000 | 18 005 |

**% Aprobación por mes (fecha_reclamo):**

| Mes | 2025 | 2026 |
|---|---|---|
| Ene | 41.5% | 41.1% |
| Feb | 38.9% | 39.7% |
| Mar | 39.5% | 40.3% |
| Abr | 39.5% | 41.4% |
| May | 41.4% | 39.6% |
| Jun | 40.6% | 39.3% |
| Jul | 41.3% | 40.9% |
| Ago | 41.7% | 39.0% |
| Sep | 40.5% | 38.1% |
| Oct | 39.2% | **34.2%** ⚠️ |
| Nov | 40.3% (hasta el 06/11) | – |

**Controles de integridad (todos OK):**
- 0 nulos y 0 IDs duplicados por hospital.
- Todas las transacciones y reclamos tienen una atención existente.
- Ninguna fecha es posterior al 08/10/2026.

---

## 6. Limitaciones conocidas
- **Noviembre y diciembre de 2025:** noviembre queda parcial (hasta el 06/11) y diciembre no tiene datos, porque los datos originales de 2024 terminaban el 06/11.
- **Datos de 2025 heredados:** conservan las inconsistencias del origen, por ejemplo pagos con fecha anterior al servicio o `id_reclamo` que no existe en reclamos. Se dejaron así a propósito para el ejercicio de limpieza y EDA. Las filas de 2026 sí son coherentes.

## 7. Cómo volver atrás
Copia los 6 archivos de `datos_bronce_backup_2024/` a `datos_bronce/` y repite los pasos de la sección 4.
