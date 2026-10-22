
# Callbacks para la vista de toma de decisiones de clientes

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Input, Output, State

from components.charts import aplicar_estilo_grafico
from data.business import cargar_clientes_gold


COLUMNAS_HALLAZGOS = [
    "Prioridad",
    "Hallazgo",
    "Período",
    "Evidencia",
    "Acción sugerida",
]

MESES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

BANDAS_GASTO = [
    0,
    20,
    50,
    100,
    500,
    1000,
    2000,
    float("inf"),
]

ETIQUETAS_GASTO = [
    "0–20",
    "20–50",
    "50–100",
    "100–500",
    "500–1.000",
    "1.000–2.000",
    "Más de 2.000",
]

COLOR_NARANJA = "#f59e0b"
COLOR_VERDE_CLARO = "#86c98a"
COLOR_VERDE_OSCURO = "#237a3b"


def preparar_datos_clientes():
    """Carga y prepara el snapshot Gold de clientes."""

    df = cargar_clientes_gold().copy()

    columnas_fecha = [
        "first_purchase_date",
        "last_purchase_date",
    ]

    columnas_numericas = [
        "total_orders",
        "total_items",
        "total_spent",
        "avg_order_value",
        "avg_freight",
        "avg_installments",
        "categories_count",
        "sellers_count",
        "avg_review_score",
    ]

    for columna in columnas_fecha:
        if columna not in df.columns:
            df[columna] = pd.NaT

        df[columna] = pd.to_datetime(
            df[columna],
            errors="coerce",
        )

    for columna in columnas_numericas:
        if columna not in df.columns:
            df[columna] = float("nan")

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce",
        )

    if "customer_id" not in df.columns:
        df["customer_id"] = pd.NA

    if "customer_segment" not in df.columns:
        df["customer_segment"] = "Sin segmento"

    df["customer_segment"] = (
        df["customer_segment"]
        .fillna("Sin segmento")
        .astype(str)
        .str.strip()
        .replace("", "Sin segmento")
    )

    # El identificador de Gold representa al cliente único.
    df = df.drop_duplicates(subset=["customer_id"])

    # Los registros sin identificador no se cuentan como clientes.
    df = df[df["customer_id"].notna()].copy()

    return df


def formatear_numero(valor, decimales=0):
    """Formatea números con separadores habituales en Argentina."""

    if valor is None or pd.isna(valor):
        return "Sin datos"

    resultado = f"{valor:,.{decimales}f}"
    return resultado.replace(",", "_").replace(".", ",").replace("_", ".")


def formatear_porcentaje(valor):
    if valor is None or pd.isna(valor):
        return "Sin datos"

    return f"{formatear_numero(valor, 1)} %"


def formatear_dinero(valor):
    if valor is None or pd.isna(valor):
        return "Sin datos"

    return f"R$ {formatear_numero(valor, 2)}"


def crear_figura_vacia(titulo):
    figura = go.Figure()

    figura.add_annotation(
        text="Sin datos para los filtros seleccionados",
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
    )

    figura.update_xaxes(visible=False)
    figura.update_yaxes(visible=False)
    figura.update_layout(title_text=titulo)

    return figura


def preparar_figura(figura, titulo):
    aplicar_estilo_grafico(figura, 40)

    figura.update_layout(
        title_text=titulo,
        height=330,
        font_size=11,
        margin={"l": 25, "r": 20, "t": 55, "b": 35},
        legend_title_text="",
        legend_orientation="h",
    )

    return figura


def crear_grafico_satisfaccion(df):
    """Muestra la satisfacción promedio por segmento, de menor a mayor."""

    datos = df.loc[
        df["avg_review_score"].between(1, 5)
    ].copy()

    titulo = "Satisfacción promedio por segmento"

    if datos.empty:
        return preparar_figura(
            crear_figura_vacia(titulo),
            titulo,
        )

    resumen = (
        datos.groupby("customer_segment", as_index=False)
        .agg(
            satisfaccion=("avg_review_score", "mean"),
            clientes=("customer_id", "nunique"),
        )
        .sort_values(
            "satisfaccion",
            ascending=True,
        )
    )

    colores = [
        COLOR_NARANJA if valor < 4
        else COLOR_VERDE_CLARO if valor < 4.2
        else COLOR_VERDE_OSCURO
        for valor in resumen["satisfaccion"]
    ]

    figura = px.bar(
        resumen,
        x="satisfaccion",
        y="customer_segment",
        orientation="h",
        custom_data=["clientes"],
        labels={
            "customer_segment": "Segmento de cliente",
            "satisfaccion": "Calificación promedio (1–5)",
        },
    )

    figura.update_traces(
        marker_color=colores,
        hovertemplate=(
            "Segmento: %{y}<br>"
            "Calificación promedio: %{x:.2f}/5<br>"
            "Clientes con calificación: %{customdata[0]:,.0f}"
            "<extra></extra>"
        ),
    )

    figura.update_xaxes(
        range=[0, 5],
        dtick=1,
    )

    figura.update_yaxes(
        categoryorder="array",
        categoryarray=resumen["customer_segment"].tolist(),
    )

    return preparar_figura(figura, titulo)


def crear_grafico_distribucion_gasto(df):
    """Distribuye clientes según su gasto histórico acumulado."""

    datos = df.loc[
        df["total_spent"].notna()
        & df["total_spent"].ge(0),
        ["customer_id", "total_spent"],
    ].copy()

    titulo = "Distribución del gasto por cliente"

    if datos.empty:
        return preparar_figura(
            crear_figura_vacia(titulo),
            titulo,
        )

    datos["banda_gasto"] = pd.cut(
        datos["total_spent"],
        bins=BANDAS_GASTO,
        labels=ETIQUETAS_GASTO,
        right=False,
        include_lowest=True,
    )

    resumen = (
        datos.groupby(
            "banda_gasto",
            observed=False,
        )["customer_id"]
        .nunique()
        .reindex(ETIQUETAS_GASTO, fill_value=0)
        .rename("clientes")
        .reset_index()
    )

    resumen["banda_gasto"] = resumen["banda_gasto"].astype(str)

    figura = px.bar(
        resumen,
        x="banda_gasto",
        y="clientes",
        labels={
            "banda_gasto": "Gasto acumulado por cliente (R$)",
            "clientes": "Cantidad de clientes",
        },
        category_orders={
            "banda_gasto": ETIQUETAS_GASTO,
        },
    )

    figura.update_traces(
        hovertemplate=(
            "Gasto acumulado: %{x}<br>"
            "Clientes: %{y:,.0f}"
            "<extra></extra>"
        ),
    )

    return preparar_figura(figura, titulo)


def calcular_indicadores(df):
    """Calcula los cuatro indicadores sobre todos los clientes filtrados."""

    total = int(df["customer_id"].nunique())

    if total == 0:
        return {
            "hallazgos": "0",
            "baja_satisfaccion": "Sin datos",
            "alto_valor": "Sin datos",
            "compra_unica": "Sin datos",
            "baja_satisfaccion_pct": None,
            "compra_unica_pct": None,
        }

    puntuaciones_validas = df["avg_review_score"].between(1, 5)
    baja_satisfaccion = (
        puntuaciones_validas
        & df["avg_review_score"].le(3)
    )

    gastos_validos = df.loc[
        df["total_spent"].notna()
        & df["total_spent"].ge(0),
        "total_spent",
    ]

    umbral_alto_valor = (
        gastos_validos.quantile(0.75)
        if not gastos_validos.empty
        else float("nan")
    )

    if pd.notna(umbral_alto_valor):
        alto_valor_baja_satisfaccion = (
            df["total_spent"].ge(umbral_alto_valor)
            & df["total_spent"].notna()
            & baja_satisfaccion
        )
    else:
        alto_valor_baja_satisfaccion = pd.Series(
            False,
            index=df.index,
        )

    compra_unica = df["total_orders"].eq(1)

    porcentaje_baja_satisfaccion = (
        baja_satisfaccion.sum() * 100 / total
    )
    porcentaje_compra_unica = compra_unica.sum() * 100 / total

    return {
        "hallazgos": "0",
        "baja_satisfaccion": formatear_porcentaje(
            porcentaje_baja_satisfaccion
        ),
        "alto_valor": formatear_porcentaje(
            alto_valor_baja_satisfaccion.sum() * 100 / total
        ),
        "compra_unica": formatear_porcentaje(
            porcentaje_compra_unica
        ),
        "baja_satisfaccion_pct": porcentaje_baja_satisfaccion,
        "compra_unica_pct": porcentaje_compra_unica,
    }


def generar_intervenciones(
    df,
    periodo,
    minimo_satisfaccion=20,
    minimo_alto_valor=5,
    minimo_compra_unica=10,
):
    """Genera hallazgos por segmento con evidencia y acciones sugeridas."""

    if df.empty:
        return []

    datos = df.drop_duplicates("customer_id").copy()

    for columna in [
        "total_orders",
        "total_spent",
        "avg_review_score",
    ]:
        datos[columna] = pd.to_numeric(
            datos[columna],
            errors="coerce",
        )

    datos["customer_segment"] = (
        datos["customer_segment"]
        .fillna("Sin segmento")
        .astype(str)
    )

    gastos_validos = datos.loc[
        datos["total_spent"].notna()
        & datos["total_spent"].ge(0),
        "total_spent",
    ]

    umbral_alto_valor = (
        gastos_validos.quantile(0.75)
        if not gastos_validos.empty
        else float("nan")
    )

    hallazgos = []

    def agregar(prioridad, hallazgo, evidencia, accion):
        hallazgos.append(
            {
                "Prioridad": prioridad,
                "Hallazgo": hallazgo,
                "Período": periodo,
                "Evidencia": evidencia,
                "Acción sugerida": accion,
            }
        )

    for segmento, grupo in datos.groupby(
        "customer_segment",
        sort=True,
    ):
        calificaciones = grupo.loc[
            grupo["avg_review_score"].between(1, 5),
            "avg_review_score",
        ]

        # Regla 1: baja satisfacción en el segmento.
        if (
            len(calificaciones) >= minimo_satisfaccion
            and calificaciones.mean() <= 3.5
        ):
            media = calificaciones.mean()

            agregar(
                "Alta" if media <= 3 else "Media",
                f"Baja satisfacción en {segmento}",
                (
                    f"Calificación promedio: {media:.2f}/5, "
                    f"sobre {len(calificaciones)} clientes con "
                    "calificación válida."
                ),
                (
                    "Revisar reseñas y cruzarlas con información de "
                    "entregas, categorías y vendedores para identificar "
                    "los problemas más frecuentes."
                ),
            )

        if pd.notna(umbral_alto_valor):
            # Regla 2: alto gasto con baja satisfacción.
            clientes_alto_valor = grupo.loc[
                grupo["total_spent"].ge(umbral_alto_valor)
                & grupo["total_spent"].notna()
                & grupo["avg_review_score"].between(1, 3)
            ]

            if len(clientes_alto_valor) >= minimo_alto_valor:
                agregar(
                    "Alta",
                    f"Clientes de alto valor con baja satisfacción: {segmento}",
                    (
                        f"{len(clientes_alto_valor)} clientes cumplen "
                        f"ambas condiciones. Umbral de gasto: "
                        f"{formatear_dinero(umbral_alto_valor)}; "
                        "calificación promedio por cliente ≤ 3/5."
                    ),
                    (
                        "Priorizar una revisión de los casos y sus "
                        "pedidos. Identificar problemas comunes antes "
                        "de definir acciones de recuperación."
                    ),
                )

            # Regla 3: alto gasto y una sola compra.
            compra_unica_alto_gasto = grupo.loc[
                grupo["total_orders"].eq(1)
                & grupo["total_spent"].ge(umbral_alto_valor)
                & grupo["total_spent"].notna()
            ]

            if len(compra_unica_alto_gasto) >= minimo_compra_unica:
                agregar(
                    "Media",
                    f"Alto gasto con compra única: {segmento}",
                    (
                        f"{len(compra_unica_alto_gasto)} clientes "
                        f"registran un pedido y gasto histórico ≥ "
                        f"{formatear_dinero(umbral_alto_valor)}."
                    ),
                    (
                        "Probar una acción de segunda compra adecuada "
                        "a las categorías adquiridas y comparar la "
                        "conversión con un grupo de control."
                    ),
                )

    return sorted(
        hallazgos,
        key=lambda hallazgo: (
            0 if hallazgo["Prioridad"] == "Alta" else 1,
            hallazgo["Hallazgo"],
        ),
    )


def obtener_periodo(anio, mes):
    if anio in (None, "todos"):
        return "Todos los años"

    if mes in (None, "todos"):
        return str(anio)

    return f"{MESES.get(int(mes), mes)} {anio}"


def registrar_callbacks_decisiones_clientes(app):

    # Opciones de año.
    @app.callback(
        Output("decisiones_clientes_filtro_anio", "options"),
        Output("decisiones_clientes_filtro_anio", "value"),
        Input("selector_dashboard", "value"),
        State("decisiones_clientes_filtro_anio", "value"),
    )
    def cargar_anios(_dashboard, anio_actual):
        df = preparar_datos_clientes()

        anios = sorted(
            df["last_purchase_date"]
            .dropna()
            .dt.year
            .unique()
            .tolist()
        )

        opciones = [{"label": "Todos", "value": "todos"}]
        opciones.extend(
            {"label": str(anio), "value": int(anio)}
            for anio in anios
        )

        valores_validos = ["todos"] + [int(anio) for anio in anios]

        if anio_actual not in valores_validos:
            anio_actual = "todos"

        return opciones, anio_actual

    # Opciones de mes.
    @app.callback(
        Output("decisiones_clientes_filtro_mes", "options"),
        Output("decisiones_clientes_filtro_mes", "value"),
        Output("decisiones_clientes_filtro_mes", "disabled"),
        Input("decisiones_clientes_filtro_anio", "value"),
        State("decisiones_clientes_filtro_mes", "value"),
    )
    def cargar_meses(anio, mes_actual):
        if anio in (None, "todos"):
            return (
                [{"label": "Todos", "value": "todos"}],
                "todos",
                True,
            )

        fechas = preparar_datos_clientes()["last_purchase_date"].dropna()

        meses_disponibles = sorted(
            fechas[fechas.dt.year == int(anio)]
            .dt.month
            .unique()
            .tolist()
        )

        opciones = [{"label": "Todos", "value": "todos"}]
        opciones.extend(
            {
                "label": MESES[mes],
                "value": int(mes),
            }
            for mes in meses_disponibles
        )

        valores_validos = ["todos"] + [
            int(mes) for mes in meses_disponibles
        ]

        if mes_actual not in valores_validos:
            mes_actual = "todos"

        return opciones, mes_actual, False

    # Actualización de indicadores, gráficos y hallazgos.
    @app.callback(
        Output("decisiones_clientes_kpi_hallazgos", "children"),
        Output("decisiones_clientes_kpi_baja_satisfaccion", "children"),
        Output("decisiones_clientes_kpi_alto_valor", "children"),
        Output("decisiones_clientes_kpi_compra_unica", "children"),
        Output("decisiones_clientes_kpi_baja_satisfaccion", "style"),
        Output("decisiones_clientes_kpi_compra_unica", "style"),
        Output("decisiones_clientes_grafico_satisfaccion", "figure"),
        Output("decisiones_clientes_grafico_gasto", "figure"),
        Output("decisiones_clientes_tabla_hallazgos", "columns"),
        Output("decisiones_clientes_tabla_hallazgos", "data"),
        Output("decisiones_clientes_estado", "children"),
        Input("decisiones_clientes_filtro_anio", "value"),
        Input("decisiones_clientes_filtro_mes", "value"),
    )
    def actualizar_decisiones(anio, mes):
        df = preparar_datos_clientes()

        # Los filtros seleccionan clientes por última compra.
        if anio not in (None, "todos"):
            df = df[
                df["last_purchase_date"].dt.year == int(anio)
            ]

            if mes not in (None, "todos"):
                df = df[
                    df["last_purchase_date"].dt.month == int(mes)
                ]

        periodo = obtener_periodo(anio, mes)

        hallazgos = generar_intervenciones(
            df,
            periodo=periodo,
        )

        indicadores = calcular_indicadores(df)
        indicadores["hallazgos"] = str(len(hallazgos))

        estilo_kpi_baja_satisfaccion = {
            "fontSize": "25px",
            "margin": "0 0 6px 0",
            "color": (
                COLOR_NARANJA
                if indicadores["baja_satisfaccion_pct"] is not None
                and indicadores["baja_satisfaccion_pct"] > 20
                else "#222"
            ),
        }

        estilo_kpi_compra_unica = {
            "fontSize": "25px",
            "margin": "0 0 6px 0",
            "color": (
                COLOR_NARANJA
                if indicadores["compra_unica_pct"] is not None
                and indicadores["compra_unica_pct"] > 90
                else "#222"
            ),
        }

        figura_satisfaccion = crear_grafico_satisfaccion(df)
        figura_gasto = crear_grafico_distribucion_gasto(df)

        columnas = [
            {"name": nombre, "id": nombre}
            for nombre in COLUMNAS_HALLAZGOS
        ]

        if df.empty:
            estado = "No hay clientes para los filtros seleccionados."
        elif not hallazgos:
            estado = (
                "No se detectaron hallazgos que cumplan los umbrales "
                "y mínimos de casos definidos. Esto no significa que "
                "no existan problemas."
            )
        else:
            estado = (
                f"{len(hallazgos)} hallazgos para revisar, "
                "ordenados por prioridad."
            )

        return (
            indicadores["hallazgos"],
            indicadores["baja_satisfaccion"],
            indicadores["alto_valor"],
            indicadores["compra_unica"],
            estilo_kpi_baja_satisfaccion,
            estilo_kpi_compra_unica,
            figura_satisfaccion,
            figura_gasto,
            columnas,
            hallazgos,
            estado,
        )
