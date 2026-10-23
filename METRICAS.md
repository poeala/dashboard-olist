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

**Alcance metodológico.** Una asociación entre vendedor, distancia y retraso
describe los pedidos en los que participa ese vendedor. No identifica quién
causó el retraso: un pedido con dos vendedores comparte el resultado de entrega
en ambos grupos, aunque no se conozca el desempeño de cada envío. La deduplicación
evita inflar conteos dentro de un grupo, pero no convierte ese resultado del
pedido en una medición individual del vendedor. Para atribuir responsabilidades
harían falta fechas y eventos por envío, transportista y tramo, además de
controlar diferencias de rutas, promesas, estacionalidad y composición de pedidos.
Esta aclaración aparece al inicio de las tres vistas de Logística.

Decisiones marca grupos cuya tasa supera el mayor entre **10 %** y
**promedio filtrado + 5 puntos porcentuales**, con al menos 30 entregas
comparables por defecto. El mínimo es editable entre 5 y 10.000.
Son reglas académicas explícitas; no representan un SLA contratado.

### Fundamento y evaluación de la regla logística

Sea `p` la tasa de retraso de **pedidos únicos con ambas fechas** dentro de los
filtros actuales. Un grupo se selecciona si tiene al menos `n` entregas comparables
y su tasa es **estrictamente mayor** que `max(piso, p + margen)`. Los valores base
son `n = 30`, `piso = 10 %` y `margen = 5 puntos porcentuales`. La igualdad no activa
la regla y las comparaciones se hacen sin redondear.

El piso pretende evitar que una referencia baja produzca alertas por tasas
absolutas bajas; el margen exige una separación descriptiva respecto del contexto
seleccionado. Esta combinación es una justificación de diseño para una revisión
exploratoria, **no evidencia de que 10 % y 5 puntos sean óptimos**. No se documentó
una calibración contra costos, capacidad de intervención, un SLA ni resultados
de intervenciones. El mínimo de 30 reduce la exposición a grupos muy pequeños,
pero no establece por sí solo precisión ni significación estadística.

La referencia `p` incluye los pedidos de grupos que no alcanzan el mínimo; no es
la media simple de porcentajes por grupo. Así se conserva un denominador global
de pedidos únicos incluso cuando los grupos se superponen. Los pedidos sin ambas
fechas no se clasifican como puntuales; la ausencia de fechas puede sesgar lo
observado y debe revisarse junto con la cobertura.

Decisiones incorpora una evaluación de sensibilidad calculada con los datos
filtrados, manteniendo la agrupación, la referencia y el mínimo de casos:

| Escenario | Piso | Margen sobre `p` |
| --- | --- | --- |
| Base | 10 % | 5 pp |
| Piso menor | 5 % | 5 pp |
| Piso mayor | 15 % | 5 pp |
| Margen menor | 10 % | 2 pp |
| Margen mayor | 10 % | 10 pp |

Se varía un parámetro por vez. La tabla muestra el umbral efectivo, los grupos
evaluables y seleccionados, y cuántos permanecen, entran o salen respecto de la
base. Una segunda tabla identifica la selección de cada grupo por escenario.
Ambas incluyen todos los grupos; el listado de hallazgos también deja de recortarse
a los primeros 12 y utiliza paginación. Se puede exportar la comparación a CSV.
Cambiar el mínimo de casos en el filtro recalcula la evaluación completa.

**Ejemplos ilustrativos, no resultados del dataset:** si `p = 3 %`, el umbral base
es 10 %; con piso de 5 % pasa a 8 %. Si `p = 20 %`, el umbral base es 25 % y cambiar
solo el piso entre 5 % y 15 % no cambia la selección. Si `p + margen ≥ 100 %`,
ningún grupo puede superar el umbral: esto es una limitación del criterio relativo,
no evidencia de buen desempeño. Sin entregas comparables no se evalúa la regla.

Una selección muy variable requiere revisar casos cercanos al umbral y explicitar
esa dependencia. Una selección estable solo indica estabilidad dentro de estos
escenarios; no valida causalidad, capacidad predictiva ni beneficio de la acción.
Los resultados dependen del período, la dimensión, la cobertura y la composición
de los pedidos; los grupos superpuestos no son muestras independientes y el
promedio incluye al propio grupo evaluado. No hay ajuste por comparaciones múltiples
ni una prueba estadística de diferencia respecto de la referencia.

Para evaluar su utilidad operativa queda pendiente definir costos y capacidad de
revisión, contrastar las alertas con casos investigados y comprobar su estabilidad
en períodos posteriores. Para evaluar acciones, medir resultados en ventanas
comparables y, cuando sea viable, frente a un grupo de control. Las pruebas del
repositorio verifican el cálculo, las fronteras y las membresías de escenarios;
no sustituyen esa validación empírica.

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

Gerencial concentra la situación general con cuatro KPIs: tasa de clientes
recurrentes, pedidos por cliente, gasto promedio por cliente y ticket por pedido.
Muestra evolución mensual de compradores y gasto promedio por comprador.
Los compradores mensuales no son aditivos entre meses.

Analítica conserva la tabla configurable, detalle y exportación PDF y concentra
la distribución de segmentos, recurrencia por segmento, histograma de gasto
y relación entre frecuencia y gasto. Las burbujas agrupan por segmento y número
de pedidos: posición vertical = gasto promedio; tamaño = cantidad de clientes.
Los gráficos respetan los filtros de agrupación principal y secundaria.

Analítica y Decisiones usan `gld_customer_analytics`: sus métricas abarcan el
historial Gold completo. Los filtros por última compra seleccionan clientes;
no recalculan sus compras dentro de un período. La calificación es una media
de promedios por cliente, no una media ponderada por pedidos.

Decisiones muestra únicamente intervenciones por segmento, evidencia, acción
y seguimiento, ordenadas por prioridad y luego por cantidad de clientes.
No repite KPIs generales ni gráficos descriptivos. Reglas exploratorias:

- Baja satisfacción: al menos 20 clientes con calificación válida (1 a 5).
  Prioridad alta si la media es ≤ 3/5; media si es > 3 y ≤ 3,5/5.
- Baja recurrencia: menos del 25 % con al menos dos pedidos, sobre un mínimo
  de 20 clientes con pedidos válidos (≥ 1). Prioridad media.
- Alto gasto con compra única: al menos 20 clientes del segmento con un pedido
  y gasto ≥ percentil 75 de clientes filtrados con gasto válido (≥ 0).
  Se exige un percentil positivo. Prioridad media.

Los valores ausentes no se consideran ceros en los denominadores de las reglas.
Un cliente puede participar en más de una intervención; las filas no se suman.
El percentil se recalcula al filtrar y los empates pueden superar el 25 %.
Recurrencia observada no equivale a retención por cohortes ni abandono.
Las acciones requieren validar tiempo de observación y evaluar resultados.

## Pagos

Fuente: `gld_payment_detail`, a grano **pedido + secuencia de pago**. La consulta
une pagos con ventas previamente consolidadas por pedido, evitando multiplicar
pagos por artículos. Los filtros usan fecha de compra, el mismo corte histórico
y la exclusión de cancelados/no disponibles. Se conservan pedidos sin registros
de pago para informar cobertura. La instantánea se renueva al reiniciar el backend.

Se eliminan registros idénticos de una misma clave; claves contradictorias
producen un estado de error para revisar la fuente. Un pedido con algún importe
faltante, negativo, no finito o una secuencia faltante se excluye completo de
importes, tickets y comparaciones. Un importe cero es válido. La pantalla informa
pedidos sin pagos, pedidos excluidos y atributos desconocidos.

| Indicador | Definición |
| --- | --- |
| Importe total de pagos | Suma de pagos de pedidos completos válidos |
| Participación monetaria | Importe registrado por medio / importe total × 100; sin porcentaje si el total es cero |
| Ticket por pedido | Suma de pagos consolidados / pedidos completos válidos |
| Pedidos en cuotas | Pedidos con máximo de cuotas > 1 / pedidos con cuotas conocidas en todos sus registros × 100 |
| Promedio de cuotas | Media del máximo de cuotas por pedido, entre pedidos con cuotas conocidas |
| Cuotas promedio en pedidos financiados | Media del máximo, solo para pedidos con cuotas conocidas y máximo > 1 |
| Importe promedio por registro | Suma de pagos / cantidad de registros válidos; no es ticket por pedido |
| Pagos mixtos | Pedidos con al menos dos medios distintos / pedidos con todos sus medios conocidos × 100 |

Las cuotas válidas son enteros ≥ 1; cero, negativos, no finitos y faltantes son
desconocidos. El máximo es una convención por pedido, no una suma ni un promedio
ponderado por importe. Varios pagos del mismo medio no constituyen pagos mixtos.
Medios no reconocidos se muestran como «Sin información / otro» y se excluyen
del denominador de pagos mixtos y de las reglas por medio.

Las tres vistas muestran período seleccionado, fechas de compra observadas,
corte del histórico y cobertura sobre pedidos presentes en Ventas. El corte
no certifica meses completos. Las exclusiones y atributos desconocidos son
visibles incluso cuando no quedan pedidos válidos.

Gerencial presenta importe total, pedidos válidos, ticket por pedido y porcentaje
de pedidos en cuotas. Los indicadores secundarios distinguen registros de pagos,
pagos mixtos, cuotas promedio de todos los pedidos y solo de financiados.
La evolución de importe, ticket y cantidad de pedidos es diaria al elegir un
mes concreto, y mensual en las demás selecciones. Los períodos interiores sin
observaciones se conservan como huecos; no se convierten en cero ni se unen.

Analítica distingue dos participaciones monetarias: por medio real de cada
registro y por tipo exclusivo de pedido (todos los importes de pedidos mixtos
quedan en una categoría separada). El primer criterio coincide con el medio
principal informado en Gerencial; sus conteos de pedidos no son aditivos.
La tabla por tipo de pedido sí tiene pedidos e importes aditivos. No se muestran
porcentajes cuando el importe total es cero.

Las medianas y percentiles 25/75 por rangos 1, 2–3, 4–6 y 7+ cuotas utilizan
solo crédito exclusivo con cuotas conocidas y muestran el tamaño de muestra.
La línea de referencia es la mediana en una cuota, cuando está disponible.
La composición por segmento cuenta pedidos con medio y segmento conocidos,
no clientes únicos. Gold puede incluir información posterior a la selección.

Decisiones usa una única implementación de comparaciones descriptivas compartida
con las pruebas, con un mínimo fijo de 30 pedidos por grupo y referencia:

- Ticket de un medio al menos 20 % mayor que el resto de pedidos con medios conocidos.
  Los mixtos pueden formar parte de la referencia, pero no generan esta regla.
- Mediana de pedidos de crédito exclusivo en 2–3, 4–6 o 7+ cuotas al menos 20 %
  mayor que la de crédito en una cuota.

No se evalúan diferencias relativas con referencia monetaria cero. Cada
oportunidad incluye muestras, comparación, acción a evaluar y seguimiento.
Se ordenan por diferencia relativa descendente. «Magnitud» es alta desde 40 %
y media desde 20 % hasta menos de 40 %; no expresa prioridad comercial.
El detalle distingue muestra insuficiente, referencia monetaria no positiva
y comparación evaluable sin hallazgo. Un pedido puede respaldar varias reglas;
las muestras no se suman. Los umbrales son exploratorios y fijos, no valores
óptimos validados ni pruebas estadísticas. No hay reglas por segmento en
Decisiones; esa composición se explora en Analítica.

Los pagos registrados no son margen ni ingresos netos liquidados. Más cuotas
asociadas a compras mayores no demuestran que ofrecer cuotas aumente ventas.
Faltan costos financieros y controles por categoría, época y perfil de comprador.
Las propuestas requieren un piloto y evaluación de conversión y margen frente
a un control; no constituyen una recomendación de ejecución automática.

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
