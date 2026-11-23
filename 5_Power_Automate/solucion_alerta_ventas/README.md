# Solución "Alerta de Ventas"

Flujo diario (8:00, hora de Perú) que consulta la medida `[ventas]` de un modelo de Power BI. Si supera la meta, envía un correo y un aviso por Teams. Si la consulta falla, avisa por correo y la ejecución queda marcada como fallida.

| Archivo | Uso |
|---|---|
| `AlertaVentas_1_0_0_0_managed.zip` | Para instalar en el cliente (Alicorp). No se puede editar allá; solo se actualiza importando una versión nueva. |
| `AlertaVentas_1_0_0_0_unmanaged.zip` | Para un entorno de desarrollo donde quieras seguir editándola. |

Publicador: **Ceteryx** (prefijo `cty`). La solución no incluye datos de Ceteryx: ni correos, ni IDs de modelos, ni valores de variables.

## Antes de importar en el tenant destino

1. Un entorno con **Dataverse** y rol de *System Customizer* o *System Administrator*.
2. El modelo de Power BI publicado en ese tenant, con la medida `[ventas]`.
3. En el portal de administración de Power BI, la opción **"Dataset Execute Queries REST API"** activada.
4. Tu cuenta del tenant destino con permiso de compilación (*Build*) sobre el modelo.

## Importar

1. Entra a make.powerautomate.com con la cuenta del tenant destino y elige el entorno.
2. **Soluciones → Importar solución** → sube el `.zip` *managed*.
3. **Conexiones:** crea o elige una conexión para cada referencia:
   - `Alerta de Ventas - Power BI`
   - `Alerta de Ventas - Office 365 Outlook`
   - `Alerta de Ventas - Microsoft Teams`
4. **Variables de entorno:** completa los valores del cliente:

   | Variable | Qué poner |
   |---|---|
   | Power BI - Workspace (`cty_PBI_WorkspaceId`) | ID del workspace, o `myworkspace` si el modelo está en *Mi área de trabajo* |
   | Power BI - Modelo semantico (`cty_PBI_DatasetId`) | ID del modelo, el GUID que aparece en la URL después de `/datasets/` |
   | Meta de ventas (`cty_MetaVentas`) | Monto, por ejemplo `70000` |
   | Correo destinatario (`cty_CorreoDestino`) | Correo del tenant destino que recibe la alerta |

5. Importa. Luego abre la solución → flujo **Alerta de Ventas** → **Activar** si quedó apagado → **Probar → Manualmente**.

## Cambiar la meta o el destinatario después

Soluciones → Alerta de Ventas → Variables de entorno → edita el **valor actual**. No hace falta tocar el flujo.
