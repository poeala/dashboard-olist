# Definiciones del tablero académico

Aplicación de prueba de la cátedra de Análisis de Datos Masivos, Maestría en
Ciencia de Datos de UCASAL. Autores: Fabio Quaino y María Luz Andrade.

## Alcance y fecha de corte

- Se analizan pedidos **con artículos presentes en Gold**. No equivalen
  necesariamente a todos los pedidos del sistema original.
- Se conserva el criterio temporal del dashboard de Ventas: si la máxima
  fecha de compra no es el último día de su mes, ese mes se excluye. Es una
  regla de cobertura del tablero, no una certificación de completitud.
- Ventas, Logística y Clientes usan el mismo corte calculado en
  `data/definitions.py`. Los filtros de las tres áreas usan **fecha de compra**.
- Si se elige un mes sin elegir año, se incluyen las compras de ese mes
  en todos los años disponibles.
- La fecha de referencia de recencia es el último día del período elegido,
  limitado por el corte disponible. Nunca se usa la fecha actual del equipo.
- Los importes se presentan en reales brasileños (`R$`). No se convierten
  monedas y no se infieren beneficios, costos operativos ni márgenes.
- Las consultas no modifican tablas. Ventas se carga al iniciar Python;
  las otras áreas se cargan al primer acceso, por proceso. Para actualizar
  las instantáneas se reinicia `dashboard`.

## Ventas

La facturación es la suma de `price`, sin flete, excluyendo estados
`canceled` y `unavailable`. Gerencial, Analítica y las caídas de facturación
de Decisiones usan este criterio. El filtro de entregados de Analítica
puede restringir adicionalmente la población.

Las variaciones comparan meses calendario consecutivos. Un mes sin registros
no se interpreta automáticamente como cero: no se genera una variación
contra el último mes no consecutivo. El denominador cero tampoco produce
una alerta porcentual.

Cancelación conserva todos los pedidos únicos del período con artículos;
incluye `canceled` y `unavailable` en el numerador, según la definición
original del tablero. Es un indicador diferente de la facturación.

Se conservan los umbrales exploratorios originales:

- Caída mensual inferior a −10 %; prioridad alta a partir de −20 %.
- Categorías con reseña media ≤ 3,5 y al menos 5 pedidos con reseña.
- La tabla incorpora acciones sugeridas, no conclusiones causales.

## Logística

Fuente: `gld_order_logistics`, cuya clave es **pedido + vendedor**.
Se cruza con Ventas previamente agrupada a pedido, para no multiplicar
registros por artículos. Se excluyen cancelados y no disponibles.

| Indicador | Definición |
| --- | --- |
| Pedidos | `order_id` únicos dentro de la selección |
| Entregas comparables | Pedido con fecha real y fecha prometida |
| Retrasos (%) | Fecha real posterior a la prometida / entregas comparables × 100 |
| Tiempo medio | Media de `delivery_time_days` no negativos en pedidos entregados |
| Flete medio | Suma de los fletes de cada pedido / pedidos con flete conocido |
| Reseña media | Media por pedido con puntuación válida entre 1 y 5 |

Los pedidos sin entrega no se cuentan como puntuales. Si no hay entregas
comparables, la tasa dice **Sin datos**, en lugar de 0 %.

Gerencial muestra evolución mensual de retrasos y destinos con más pedidos.
Analítica permite agrupar por estado de destino, vendedor, estado de origen
o distancia estimada. Incluye comparación descriptiva de reseñas de pedidos
puntuales y tardíos. Las tablas agregadas permiten ordenar, filtrar y exportar CSV.

En agrupaciones por vendedor, origen o distancia, un pedido puede aparecer
en más de un grupo: no sumar grupos para obtener el total. Dentro de un grupo
se cuenta el pedido una sola vez y se suman sus fletes correspondientes.
La fecha de entrega es del pedido completo; no permite atribuir el retraso
de un envío concreto al vendedor. La distancia es estimada, no una ruta real.

Decisiones marca grupos cuya tasa supera el mayor entre **10 %** y
**promedio filtrado + 5 puntos porcentuales**, con al menos 30 entregas
comparables por defecto. El mínimo es editable entre 5 y 10.000.
Son reglas académicas explícitas; no representan un SLA contratado.

## Clientes

Los pedidos, importes y recurrencia del período se calculan desde
`gld_sales_detail`, primero agregando artículos a **cliente + pedido** y
excluyendo cancelados/no disponibles. Los totales de `gld_customer_analytics`
son históricos y no se reinterpretan como totales mensuales.

| Indicador | Definición |
| --- | --- |
| Compradores | `customer_unique_id` distintos en la selección |
| Recurrentes (%) | Compradores con 2 o más pedidos en la selección / compradores × 100 |
| Valor de productos | Suma de `price` de los pedidos incluidos |
| Ticket por pedido | Valor de productos / número de pedidos, no media de tickets de clientes |
| Recencia | Días entre última compra seleccionada y fecha de corte del período |
| Alto valor | Gasto del cliente ≥ percentil 75 del gasto de compradores seleccionados |
| Reseñas por segmento | Suma de puntuaciones / pedidos con puntuación válida, no media de promedios |

El percentil se recalcula con los filtros. Por empates, alto valor puede
incluir más del 25 % de los compradores. Los segmentos del período combinan
compra única/recurrente y alto valor.

La opción **Segmento histórico Gold** utiliza `customer_segment` de la tabla
preparada en Supabase. Se identifica como histórica porque sus reglas pueden
usar compras fuera del período seleccionado. No se utiliza como evidencia
de una condición conocida en una fecha pasada ni como predicción.

Gerencial muestra compradores mensuales y segmentos; los compradores
mensuales no son aditivos entre meses. Analítica compara gasto y recurrencia
y permite exportar la tabla agregada. No se envían identificadores de
clientes individuales al navegador.

Decisiones aplica estas reglas exploratorias:

- Alto valor sin compra durante más de 90 días al corte, por defecto; el
  intervalo es configurable. Se exige el mínimo de casos seleccionado.
- Segmentos con reseña media ≤ 3/5 y al menos el mínimo de pedidos con reseña.
- Recurrencia inferior al 5 %, con el mínimo de compradores.

Recurrencia observada **no** equivale a retención de cohortes ni abandono.
Filtrar un mes limita la oportunidad de recomprar; filtrar meses no contiguos
también limita el histórico observado. Las acciones sugieren investigar y
validar estos efectos antes de tomar decisiones.

## Verificación

Las pruebas comprueban pedidos de varios vendedores, fechas ausentes,
ponderación de ticket y reseñas, cortes históricos, duplicaciones,
períodos vacíos y meses no consecutivos. También verifican las seis vistas
nuevas mediante callbacks HTTP y enlaces de navegación por área/vista.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cd frontend
npm test
```

Con Docker levantado, comprobar los callbacks reales y la navegación desde
la raíz del repositorio:

```powershell
python scripts/check_deployment.py http://127.0.0.1:8080
```

Este control comprueba las nueve vistas por HTTP; no reemplaza la revisión
visual ni la interacción manual con un navegador.
