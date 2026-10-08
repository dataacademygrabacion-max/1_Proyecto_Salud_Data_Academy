Conectado a tu modelo **project_dataanalyst**. Reviso el calendario existente, las columnas clave y las medidas que ya tengas:

El modelo ya tiene una `dim_calendario` muy completa, así que la reutilizo en lugar de crear otra. Antes de cambiar nada, consulto algunos datos:

Encontré que los datos en Databricks y Power BI siguen en inglés (Approved, Paid, Denied) porque se cargaron antes de traducir los CSV; crearé las medidas en español y validaré los números con una consulta que acepte ambos idiomas. Empiezo con el modelo, revisando primero las relaciones.

Ahora creo la relación por `fecha_servicio` y la tabla Hospital:

Relaciones de la tabla Hospital, columna "Semana del mes", ordenamientos y ocultar la columna auxiliar:

Ahora creo las medidas en la carpeta **Medidas**, organizadas en subcarpetas:

Validación con consultas DAX: totales, evolutivo mensual, filtro de hospital y aseguradoras:

Los totales cuadran. Ejecuto las demás validaciones por separado:

Ya creé las medidas en tu Power BI, corregí el modelo y comprobé los números con consultas DAX. **Todavía no están guardados**: haz **Ctrl+S** en Power BI Desktop.

El único pendiente es que tus datos siguen en inglés (lo explico en el paso 0).

## Qué cambié en tu modelo `project_dataanalyst`

| Cambio | Detalle |
|---|---|
| ✅ **Carpeta de medidas** | Tabla `_Medidas` con 20 medidas en tres subcarpetas: **1. Facturación**, **2. Reclamos** y **3. Formato** (etiquetas y colores para el formato condicional). Cada una ya tiene su formato de moneda, porcentaje o entero. |
| 🔧 **Relación de fechas corregida** | `fact_transacciones` estaba unida al calendario por `fecha_pago`. La cambié a **`fecha_servicio`**, que es la fecha que usan la guía y el SQL. La de `fecha_pago` sigue en el modelo pero inactiva. |
| ✅ **Nueva tabla `dim_hospital`** | Hospital A y Hospital B, unida a transacciones y reclamos por `fuente`. Así un solo segmentador filtra las dos tablas. |
| ✅ **`dim_calendario`** | Reutilicé la tuya y le agregué la columna **Semana del Mes** (Sem 1 a Sem 5). Ordené Mes y Mes Corto por Mes Num, y Día Semana por su número. También la marqué como tabla de fechas. |
| ✔️ **Lo demás ya estaba bien** | Los pacientes y departamentos están unidos a sus tablas de hechos. La relación con `fecha_reclamo` existe y está activa. Las relaciones con médicos están inactivas, y es correcto dejarlas así porque se cruzarían con la de departamentos. |

## Números comprobados en Power BI (coinciden con el dashboard)
- **Facturado y cobrado:** $10,490,422.05 facturado, $8,196,514.10 cobrado, **78.1%** cobrado y una brecha de $2.29 M.
- **Pacientes y hospitales:** 8,619 pacientes. Hospital A tiene $5.29 M y Hospital B $5.20 M, así que el filtro por hospital funciona.
- **Aprobación de reclamos:** **40.4%** en el año. Los meses bajo la meta son Feb (38.9%), Mar (39.5%), Abr (39.5%) y Oct (39.2%).
- **Drill a semanas:** en marzo, la semana 5 está en 36.8% y las semanas 1 y 2 en 38.8% y 38.7%.
- **Rechazo por aseguradora:** Aetna 40.7%, Medicare 40.2%, UnitedHealthcare 40.2%, BlueCross 39.7% y Medicaid 38.8%.

---

## Paso a paso para armar el dashboard

**0. Recarga los datos en español (obligatorio)**
Databricks tiene los datos antiguos, con valores como `Approved` o `Denied`. Mientras no los recargues, **% Aprobación y % Rechazo saldrán vacíos**. Para recargarlos:
1. Vuelve a subir los 13 CSV de `datos_bronce/` al volumen y reemplaza los anteriores.
2. Ejecuta en orden `01_carga_y_EDA`, `02_plata_SQL` y `03_oro_SQL`.
3. En Power BI, haz **Inicio > Actualizar**.

**1. Prepara el archivo**
- Ve a **Archivo > Opciones > Archivo actual > Carga de datos** y desactiva **Fecha y hora automáticas**. Eso elimina 12 tablas de fecha ocultas que solo hacen pesado el modelo.
- Carga el tema `tema_red_salud.json`. El texto está en la sección 6 de la guía; se carga en **Vista > Temas > Examinar temas**.
- En **Formato de página**, pon el lienzo en 16:9 (1280 × 720) con fondo `#EEF1F5`.
- Dale a cada visual fondo `#F8F9FB`, esquinas de 16 px, sombra suave y sin borde.

**2. Encabezado**
Dos rectángulos redondeados con cuadros de texto: **"Red Salud"** y **"Ciclo de Ingresos | Evolutivo mensual | Ene–Nov 2024 | Fuente: salud_oro"**.

**3. Segmentador de hospital**
`dim_hospital[Hospital]`, estilo **Mosaico**, con "Seleccionar todo" activado para que funcione como "Todos".

**4. Las 5 tarjetas (visual "Tarjeta (nueva)")**

| Tarjeta | Medida | Etiqueta de referencia |
|---|---|---|
| Total facturado | Total Facturado (unidades: Millones) | — |
| Total cobrado | Total Cobrado (unidades: Millones) | — |
| % Cobrado | % Cobrado | `Etiqueta Cobrado`, en color ámbar |
| Pacientes atendidos | Pacientes Atendidos | — |
| % Aprobación | % Aprobación | `Etiqueta Aprobación`, con color fx por valor de campo = `Color Aprobación` |

**5. Gráfico de columnas agrupadas: "Facturado vs. cobrado por mes"**
- **Eje X:** `dim_calendario[Mes Corto]` y debajo `dim_calendario[Día]`. Así se forma la jerarquía Mes > Día para el drill.
- **Eje Y:** Total Facturado y Total Cobrado. Colores: Facturado `#86B6EF`, Cobrado `#1C5CAB`.
- **Información sobre herramientas:** Brecha y % Cobrado.
- **Etiquetas de datos:** solo en la serie Facturado. Si tu versión tiene la opción **Detalle**, ponle % Cobrado.

**6. Gráfico de líneas: "% Aprobación por mes"**
- **Eje X:** `Mes Corto` y debajo `Semana del Mes`. **Eje Y:** % Aprobación, color `#2A78D6`.
- **Meta:** en el panel **Análisis**, agrega una **Línea constante** de 0.4, color `#C2410C`, con la etiqueta "Meta 40%".
- **Marcadores:** actívalos y pon color fx por valor de campo = **Color Punto**. Si tu versión no lo permite, agrega la medida **Bajo Meta** como segunda serie con ancho de línea 0 y marcadores naranjas.

**7. Barras agrupadas: "¿Qué aseguradoras rechazan más?"**
- **Eje Y:** `fact_reclamos[aseguradora]`. **Eje X:** % Rechazo, ordenado de mayor a menor.
- **Color de barras:** fx por valor de campo = **Color Rechazo**, que resalta a Aetna. Activa las etiquetas de datos.

**8. Barras agrupadas: "Facturación por departamento"**
`dim_departamentos[nombre]` contra Total Facturado, ordenado de mayor a menor, color `#86B6EF`.

**9. Activa el drill**
1. En los visuales 5 y 6, activa la **flecha hacia abajo** del encabezado (exploración en profundidad). Así, un clic en un mes baja a sus días o a sus semanas.
2. Ve a **Formato > Interacciones** y activa **"Explorar en profundidad filtra otros objetos visuales"**. Con eso, las tarjetas y los gráficos de aseguradoras y departamentos muestran solo el mes en el que entraste.
3. Para regresar a todos los meses, usa la **flecha hacia arriba** del encabezado del visual.

**10. Valida y publica**
- Compara tus resultados con los números de arriba.
- Agrega una nota al pie: "Noviembre parcial (datos hasta 06/11/2024)".
- Publica en Power BI Service y sigue con la Fase 5 (alertas sobre la tarjeta % Aprobación).

Ten en cuenta que en `Mes Corto` septiembre aparece como **"Set"**, porque el calendario usa el formato es-PE. Es correcto.