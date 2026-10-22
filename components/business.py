"""Presentación de resultados agregados; no envía registros de clientes al navegador."""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, dash_table

from components.charts import aplicar_estilo_grafico
from components.logistics_map import mapa_logistica_regiones
from data.business_metrics import (
    pedidos_logistica,
    resumen_logistica,
    agrupar_logistica,
    perfil_clientes,
    resumen_clientes,
    agrupar_clientes,
)


GEOJSON_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "br_states.geojson"
)

MIN_CASES_LOGISTICS = 30
LOGISTICS_LATE_THRESHOLD = 15.0


def number(value, decimals=0, suffix=""):
    if value is None or pd.isna(value):
        return "Sin datos"

    result = (
        f"{value:,.{decimals}f}"
        .replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )
    return result + suffix


def money(value):
    return (
        "R$ " + number(value, 2)
        if value is not None and not pd.isna(value)
        else "Sin datos"
    )


def cards(items, neutral=False):
    """Muestra tarjetas KPI con nombre, métrica y descripción."""
    card_style = (
        {
            "backgroundColor": "#ffffff",
            "border": "1px solid #e5e7eb",
            "color": "#111827",
        }
        if neutral else None
    )

    result = []

    for item in items:
        label, value, detail = item[:3]
        value_color = item[3] if len(item) > 3 else None

        result.append(
            html.Div([
                html.P(
                    label,
                    className="business-card-label",
                    style={"color": "#111827"} if neutral else None,
                ),
                html.H3(
                    value,
                    className="business-card-value",
                    style={
                        "color": value_color or "#111827"
                    } if neutral else (
                        {"color": value_color}
                        if value_color else None
                    ),
                ),
                html.P(
                    detail,
                    className="business-card-detail",
                    style={"color": "#374151"} if neutral else None,
                ),
            ], className="business-card", style=card_style)
        )

    return html.Div(result, className="business-kpis")


def chart(fig, title, height=330):
    if fig is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Sin datos para estos filtros",
            showarrow=False,
            x=.5,
            y=.5,
            xref="paper",
            yref="paper",
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)

    aplicar_estilo_grafico(fig, 40)
    fig.update_layout(
        title_text=title,
        height=height,
        font_size=11,
        legend_title_text="",
        legend_orientation="h",
    )

    return html.Div(
        dcc.Graph(
            figure=fig,
            config={"displaylogo": False, "responsive": True},
        ),
        className="business-chart",
    )


@lru_cache(maxsize=1)
def cargar_geojson_estados():
    """Carga localmente los límites geográficos de los estados de Brasil."""
    if not GEOJSON_PATH.exists():
        return None

    with GEOJSON_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def mapa_pedidos_por_estado(rows, state_column, title):
    """Genera un mapa por estado contando pedidos únicos en cada estado."""
    geojson = cargar_geojson_estados()

    if geojson is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Falta el archivo assets/br_states.geojson",
            showarrow=False,
            x=.5,
            y=.5,
            xref="paper",
            yref="paper",
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    if state_column not in rows.columns:
        return None

    features = geojson.get("features", [])

    states = sorted({
        str(feature["id"]).strip().upper()
        for feature in features
        if feature.get("id") is not None
    })

    if not states:
        fig = go.Figure()
        fig.add_annotation(
            text="El GeoJSON no contiene identificadores de estados en 'id'",
            showarrow=False,
            x=.5,
            y=.5,
            xref="paper",
            yref="paper",
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    data = rows[["order_id", state_column]].dropna().copy()
    data["state"] = data[state_column].astype(str).str.strip().str.upper()
    data = data[data["state"].isin(states)]

    counts = (
        data.drop_duplicates(["order_id", "state"])
        .groupby("state", as_index=False)
        .agg(orders=("order_id", "nunique"))
    )

    map_data = pd.DataFrame({"state": states}).merge(
        counts,
        on="state",
        how="left",
    )
    map_data["orders"] = map_data["orders"].fillna(0).astype(int)

    fig = px.choropleth(
        map_data,
        geojson=geojson,
        locations="state",
        featureidkey="id",
        color="orders",
        color_continuous_scale="Blues",
        hover_name="state",
        hover_data={"orders": ":,", "state": False},
        labels={
            "state": "Estado",
            "orders": "Pedidos",
        },
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        coloraxis_colorbar_title_text="Pedidos",
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
    )
    return fig


def table(
    df,
    columns,
    title,
    detail=None,
    export_button=False,
    table_id=None,
):
    selected = df[list(columns)].rename(columns=columns).copy()

    for col in selected.select_dtypes(include="number"):
        selected[col] = selected[col].round(2)

    records = json.loads(
        selected.to_json(orient="records", date_format="iso")
    )

    heading = html.Div([
        html.H3(title, style={"margin": "0"}),
        (
            html.Button(
                "Exportar",
                id="business-logistics-export-button",
                n_clicks=0,
                className="business-export-button",
                style={"marginLeft": "auto"},
            )
            if export_button else None
        ),
    ], className="business-table-heading", style={
        "display": "flex",
        "alignItems": "center",
        "gap": "12px",
        "width": "100%",
        "marginBottom": "12px",
    })

    table_component = dash_table.DataTable(
        id=table_id or "business-generic-table",
        data=records,
        columns=[
            {"name": label, "id": label}
            for label in columns.values()
        ],
        page_size=10,
        sort_action="native",
        filter_action="native",
        export_format=None if export_button else "csv",
        export_headers="display",
        style_table={"overflowX": "auto"},
        style_cell={
            "fontFamily": "Arial",
            "fontSize": 12,
            "padding": "10px",
            "textAlign": "left",
            "whiteSpace": "normal",
            "height": "auto",
            "minWidth": "90px",
            "maxWidth": "290px",
        },
        style_header={
            "backgroundColor": "#e8eff7",
            "color": "#003D7C",
            "fontWeight": "600",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#f8fafc",
            }
        ],
    )

    return html.Div([
        dcc.Download(id="business-logistics-export-download")
        if export_button else None,
        heading,
        html.P(detail, className="business-note") if detail else None,
        table_component,
        html.P(
            "Sin filas para los filtros seleccionados.",
            className="business-note",
        ) if selected.empty else None,
    ], className="business-table")


def findings(items):
    """Tabla de hallazgos utilizada por las decisiones de Clientes."""
    if not items:
        return html.Div([
            html.H3("Sin hallazgos con estos criterios"),
            html.P(
                "No se encontraron grupos que superen el umbral con al "
                "menos 30 casos comparables. Esto no equivale a ausencia "
                "de problemas."
            ),
        ], className="business-empty")

    df = pd.DataFrame(items)

    return table(
        df,
        {
            "finding": "Hallazgo",
            "evidence": "Evidencia",
            "action": "Acción sugerida",
        },
        "Hallazgos para revisar",
        "Reglas exploratorias para el trabajo académico; no prueban causalidad.",
        table_id="business-logistics-findings-table",
    )


def _logistics_findings(items):
    """Muestra los hallazgos logísticos con la estructura de la vista de Ventas."""
    if not items:
        return html.Div([
            html.H3("No se detectaron alertas con estos criterios"),
            html.P(
                "No se identificaron grupos con una tasa de retraso "
                "superior al 15 % y al menos 30 entregas comparables. "
                "Esto no significa que no existan problemas logísticos."
            ),
        ], className="business-empty")

    df = pd.DataFrame(items)

    return html.Div([
        html.H3(
            "Hallazgos detectados",
            style={"margin": "0 0 6px"},
        ),
        html.P(
            "Se evalúan estados de destino, estados de origen, vendedores, "
            "distancias con información válida y calificaciones bajas.",
            className="business-note",
        ),
        dash_table.DataTable(
            id="business-logistics-findings-table",
            data=json.loads(
                df.to_json(orient="records", date_format="iso")
            ),
            columns=[
                {"name": "Prioridad", "id": "Prioridad"},
                {"name": "Hallazgo", "id": "Hallazgo"},
                {"name": "Período", "id": "Período"},
                {"name": "Evidencia", "id": "Evidencia"},
                {"name": "Acción sugerida", "id": "Acción sugerida"},
            ],
            page_size=10,
            sort_action="native",
            filter_action="native",
            style_table={
                "overflowX": "auto",
                "minWidth": "100%",
            },
            style_cell={
                "fontFamily": "Arial",
                "fontSize": 12,
                "padding": "9px",
                "textAlign": "left",
                "whiteSpace": "normal",
                "height": "auto",
                "minWidth": "120px",
                "maxWidth": "320px",
            },
            style_header={
                "backgroundColor": "#f0f2f5",
                "fontWeight": "bold",
            },
            style_data_conditional=[
                {
                    "if": {
                        "filter_query": '{Prioridad} = "Alta"',
                        "column_id": "Prioridad",
                    },
                    "color": "#b91c1c",
                    "fontWeight": "bold",
                },
                {
                    "if": {
                        "filter_query": '{Prioridad} = "Media"',
                        "column_id": "Prioridad",
                    },
                    "color": "#a16207",
                    "fontWeight": "bold",
                },
            ],
        ),
        html.P(
            "Las tasas se calculan sobre entregas con fecha real y "
            "estimada. Los hallazgos son descriptivos y no demuestran "
            "por sí solos las causas de los retrasos.",
            className="business-note",
        ),
    ], className="business-table")


def _preparar_rutas_logisticas(rows):
    """
    Calcula indicadores por combinación de estado de origen y destino.

    El grano es pedido-vendedor-origen-destino. Así se evita contar varias
    veces los artículos del mismo vendedor dentro de un pedido.
    """
    required = {
        "order_id",
        "seller_id",
        "seller_state",
        "customer_state",
        "delivered_date",
        "estimated_date",
    }

    if not required.issubset(rows.columns):
        return pd.DataFrame()

    routes = rows[list(required)].copy()

    routes = routes.drop_duplicates([
        "order_id",
        "seller_id",
        "seller_state",
        "customer_state",
    ])

    routes = routes.dropna(subset=[
        "order_id",
        "seller_id",
        "seller_state",
        "customer_state",
    ])

    routes["delivered_date"] = pd.to_datetime(
        routes["delivered_date"],
        errors="coerce",
    )
    routes["estimated_date"] = pd.to_datetime(
        routes["estimated_date"],
        errors="coerce",
    )

    routes["eligible"] = (
        routes["delivered_date"].notna()
        & routes["estimated_date"].notna()
    )

    routes["late"] = (
        routes["eligible"]
        & (
            routes["delivered_date"]
            > routes["estimated_date"]
        )
    )

    routes["origin"] = (
        routes["seller_state"].astype(str).str.strip().str.upper()
    )
    routes["destination"] = (
        routes["customer_state"].astype(str).str.strip().str.upper()
    )
    routes["route"] = routes["origin"] + " → " + routes["destination"]

    grouped = routes.groupby("route", as_index=False).agg(
        shipments=("order_id", "size"),
        eligible=("eligible", "sum"),
        late=("late", "sum"),
    )

    grouped["late_pct"] = (
        100 * grouped["late"]
        / grouped["eligible"].where(grouped["eligible"] > 0)
    )

    return grouped


def _color_retraso_ruta(value):
    """Asigna colores por rangos de tasa de retraso."""
    if pd.isna(value):
        return "#9CA3AF"
    if value > 25:
        return "#B91C1C"
    if value > 20:
        return "#DC2626"
    if value > 15:
        return "#EF4444"
    if value > 10:
        return "#EAB308"
    return "#15803D"


def _grafico_top_rutas(rows, min_sample=MIN_CASES_LOGISTICS):
    """Devuelve las diez rutas con mayor tasa de retraso."""
    routes = _preparar_rutas_logisticas(rows)

    if routes.empty:
        return None

    ranked = (
        routes[
            (routes["eligible"] >= min_sample)
            & routes["late_pct"].notna()
        ]
        .sort_values(
            ["late_pct", "eligible", "route"],
            ascending=[False, False, True],
        )
        .head(10)
        .sort_values("late_pct", ascending=True)
        .copy()
    )

    if ranked.empty:
        return None

    fig = px.bar(
        ranked,
        x="late_pct",
        y="route",
        orientation="h",
        custom_data=["eligible", "late", "shipments"],
        labels={
            "route": "Origen → destino",
            "late_pct": "Entregas con retraso (%)",
        },
    )

    fig.update_traces(
        marker_color=[
            _color_retraso_ruta(value)
            for value in ranked["late_pct"]
        ],
        hovertemplate=(
            "Ruta: %{y}<br>"
            "Tasa de retraso: %{x:.2f}%<br>"
            "Entregas comparables: %{customdata[0]}<br>"
            "Entregas retrasadas: %{customdata[1]}<br>"
            "Combinaciones pedido-vendedor: %{customdata[2]}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        xaxis_title="Entregas con retraso (%)",
        yaxis_title="Origen → destino",
    )

    return fig


def _grafico_resenas_por_puntuacion(orders):
    """
    Compara la cantidad de pedidos por puntuación, separando las entregas
    puntuales de las retrasadas.

    El flete medio de cada combinación puntuación-resultado se muestra
    al pasar el cursor por cada barra.
    """
    required = {
        "order_id",
        "eligible",
        "late",
        "valid_review",
        "freight",
    }

    if not required.issubset(orders.columns):
        return None

    comparison = orders[
        orders["eligible"]
        & orders["valid_review"].between(1, 5)
    ].copy()

    if comparison.empty:
        return None

    comparison["Puntuación"] = (
        comparison["valid_review"].round().astype(int)
    )
    comparison["Resultado"] = comparison["late"].map({
        False: "En plazo",
        True: "Con retraso",
    })

    grouped = comparison.groupby(
        ["Puntuación", "Resultado"],
        as_index=False,
        observed=True,
    ).agg(
        pedidos=("order_id", "nunique"),
        flete_medio=("freight", "mean"),
    )

    # Completa las combinaciones sin pedidos para mantener una estructura
    # consistente de dos barras por puntuación.
    full_index = pd.MultiIndex.from_product(
        [
            [1, 2, 3, 4, 5],
            ["En plazo", "Con retraso"],
        ],
        names=["Puntuación", "Resultado"],
    )

    grouped = (
        grouped.set_index(["Puntuación", "Resultado"])
        .reindex(full_index)
        .reset_index()
    )
    grouped["pedidos"] = grouped["pedidos"].fillna(0).astype(int)

    colors = {
        "En plazo": "#15803D",
        "Con retraso": "#DC2626",
    }

    fig = px.bar(
        grouped,
        x="Puntuación",
        y="pedidos",
        color="Resultado",
        barmode="group",
        custom_data=["flete_medio", "Resultado"],
        category_orders={
            "Puntuación": [1, 2, 3, 4, 5],
            "Resultado": ["En plazo", "Con retraso"],
        },
        color_discrete_map=colors,
        labels={
            "Puntuación": "Calificación del pedido",
            "pedidos": "Cantidad de pedidos",
            "Resultado": "Resultado de entrega",
        },
    )

    fig.update_traces(
        hovertemplate=(
            "Calificación: %{x}<br>"
            "Resultado: %{customdata[1]}<br>"
            "Pedidos: %{y}<br>"
            "Flete medio: R$ %{customdata[0]:.2f}"
            "<extra></extra>"
        ),
    )

    fig.update_xaxes(
        title_text="Calificación del pedido (1–5)",
        dtick=1,
        tickmode="linear",
    )
    fig.update_yaxes(
        title_text="Cantidad de pedidos",
        rangemode="tozero",
    )

    fig.update_layout(
        bargap=0.18,
        bargroupgap=0.06,
        legend_title_text="Resultado de entrega",
        margin={"l": 45, "r": 20, "t": 30, "b": 45},
    )

    return fig


def _limpiar_grupos_distancia(groups):
    """Elimina los grupos sin distancia estimada válida."""
    if groups.empty or "group" not in groups.columns:
        return groups

    labels_invalidos = {
        "",
        "sin información",
        "sin informacion",
        "nan",
        "none",
        "null",
        "no informado",
        "no disponible",
    }

    normalized = (
        groups["group"]
        .astype("string")
        .str.strip()
        .str.casefold()
    )

    return groups[
        normalized.notna()
        & ~normalized.isin(labels_invalidos)
    ].copy()


def _generar_hallazgos_logistica(rows, orders, period):
    """
    Genera hallazgos con umbrales fijos y un mínimo de casos comparables.

    Las tasas de retraso se evalúan con un umbral superior al 15 %.
    Los grupos de distancia sin información se excluyen.
    """
    items = []
    threshold = LOGISTICS_LATE_THRESHOLD
    min_sample = MIN_CASES_LOGISTICS

    dimensions = [
        (
            "customer_state",
            "Estado de destino",
            "Revisar si las demoras se concentran en destinos específicos "
            "y contrastar las rutas que los abastecen.",
        ),
        (
            "seller_state",
            "Estado de origen",
            "Comparar las rutas de salida y los tiempos registrados para "
            "identificar dónde conviene profundizar el análisis.",
        ),
        (
            "seller_id",
            "Vendedor",
            "Revisar preparación y despacho de pedidos, contrastando "
            "productos, destinos y períodos antes de atribuir causas.",
        ),
        (
            "distance_band",
            "Rango de distancia",
            "Comparar los resultados entre rangos con distancia estimada "
            "válida y revisar si hay diferencias en la composición de rutas.",
        ),
    ]

    for dimension, label, action in dimensions:
        try:
            groups = agrupar_logistica(rows, dimension)
        except (KeyError, ValueError):
            continue

        if groups.empty:
            continue

        if dimension == "distance_band":
            groups = _limpiar_grupos_distancia(groups)

        eligible_groups = groups[
            (groups["eligible"] >= min_sample)
            & groups["late_pct"].notna()
            & (groups["late_pct"] > threshold)
        ].copy()

        eligible_groups = eligible_groups.sort_values(
            ["late_pct", "eligible"],
            ascending=[False, False],
        )

        for _, row in eligible_groups.head(3).iterrows():
            late_pct = float(row["late_pct"])
            priority = (
                "Alta"
                if late_pct >= threshold + 10
                else "Media"
            )

            items.append({
                "Prioridad": priority,
                "Hallazgo": (
                    f"{label} con tasa de retraso elevada: {row['group']}"
                ),
                "Período": period,
                "Evidencia": (
                    f"{number(row['late'])} de "
                    f"{number(row['eligible'])} entregas comparables "
                    f"({number(late_pct, 2)} %). "
                    f"Umbral: más del {number(threshold)} %."
                ),
                "Acción sugerida": action,
            })

    # Analiza las reseñas de pedidos entregados con fechas comparables.
    required = {
        "eligible",
        "late",
        "valid_review",
        "order_id",
        "freight",
    }

    if required.issubset(orders.columns):
        reviewed = orders[
            orders["eligible"]
            & orders["valid_review"].between(1, 5)
        ].copy()

        if not reviewed.empty:
            delayed = reviewed[reviewed["late"]]
            on_time = reviewed[~reviewed["late"]]

            low_reviews = delayed[
                delayed["valid_review"] < 3
            ]

            if len(low_reviews) >= min_sample:
                low_pct = (
                    100 * len(low_reviews) / len(delayed)
                    if len(delayed) else None
                )

                items.append({
                    "Prioridad": (
                        "Alta"
                        if low_pct is not None and low_pct >= 20
                        else "Media"
                    ),
                    "Hallazgo": (
                        "Calificaciones bajas en entregas retrasadas"
                    ),
                    "Período": period,
                    "Evidencia": (
                        f"{number(len(low_reviews))} pedidos retrasados "
                        f"con puntuación inferior a 3/5, sobre "
                        f"{number(len(delayed))} pedidos retrasados con "
                        f"reseña válida ({number(low_pct, 2)} %)."
                    ),
                    "Acción sugerida": (
                        "Revisar los comentarios disponibles y cruzar las "
                        "calificaciones con destinos, vendedores y rutas "
                        "para detectar patrones que requieran investigación."
                    ),
                })

            # Compara el promedio de calificación entre ambos resultados.
            if len(delayed) >= min_sample and len(on_time) >= min_sample:
                delayed_avg = delayed["valid_review"].mean()
                on_time_avg = on_time["valid_review"].mean()
                difference = on_time_avg - delayed_avg

                if difference >= 0.5:
                    items.append({
                        "Prioridad": (
                            "Alta" if difference >= 1 else "Media"
                        ),
                        "Hallazgo": (
                            "Calificación media inferior en entregas retrasadas"
                        ),
                        "Período": period,
                        "Evidencia": (
                            f"Entregas puntuales: {number(on_time_avg, 2)}/5 "
                            f"(n={number(len(on_time))}); entregas retrasadas: "
                            f"{number(delayed_avg, 2)}/5 "
                            f"(n={number(len(delayed))}). "
                            f"Diferencia: {number(difference, 2)} puntos."
                        ),
                        "Acción sugerida": (
                            "Analizar los comentarios de las reseñas y "
                            "contrastar los resultados por destino, vendedor "
                            "y distancia. La diferencia no demuestra por sí "
                            "sola que el retraso sea la causa de la puntuación."
                        ),
                    })

            # Señala una diferencia descriptiva en el flete medio sin
            # afirmar que el importe cause o resuelva los retrasos.
            if len(delayed) >= min_sample and len(on_time) >= min_sample:
                on_time_freight = on_time["freight"].mean()
                delayed_freight = delayed["freight"].mean()

                if (
                    pd.notna(on_time_freight)
                    and pd.notna(delayed_freight)
                    and on_time_freight > 0
                    and delayed_freight >= on_time_freight * 1.2
                ):
                    increase = (
                        100 * (delayed_freight - on_time_freight)
                        / on_time_freight
                    )

                    items.append({
                        "Prioridad": "Media",
                        "Hallazgo": (
                            "Flete medio mayor en entregas retrasadas"
                        ),
                        "Período": period,
                        "Evidencia": (
                            f"Flete medio puntual: {money(on_time_freight)}; "
                            f"flete medio retrasado: {money(delayed_freight)}. "
                            f"Diferencia: {number(increase, 2)} %."
                        ),
                        "Acción sugerida": (
                            "Comparar distancias, rutas y composición de los "
                            "pedidos antes de interpretar la diferencia. "
                            "El análisis no permite afirmar que pagar más "
                            "flete cause o evite retrasos."
                        ),
                    })

    return items, threshold


def _seccion_reglas_logistica(min_sample, limit, stats):
    """Explica las reglas de detección de la vista Decisiones."""
    min_sample = MIN_CASES_LOGISTICS
    threshold_text = number(LOGISTICS_LATE_THRESHOLD, 0, " %")

    rules = pd.DataFrame([
        {
            "Hallazgo": "Estado de destino",
            "Regla de detección": (
                "La tasa de retraso del grupo debe ser superior al 15 %."
            ),
            "Evidencia mínima": (
                f"{min_sample} entregas con fecha real y estimada."
            ),
        },
        {
            "Hallazgo": "Estado de origen",
            "Regla de detección": (
                "La tasa de retraso del grupo debe ser superior al 15 %."
            ),
            "Evidencia mínima": (
                f"{min_sample} entregas con fecha real y estimada."
            ),
        },
        {
            "Hallazgo": "Vendedor",
            "Regla de detección": (
                "La tasa de retraso del grupo debe ser superior al 15 %."
            ),
            "Evidencia mínima": (
                f"{min_sample} entregas comparables asociadas al vendedor."
            ),
        },
        {
            "Hallazgo": "Rango de distancia",
            "Regla de detección": (
                "La tasa de retraso debe superar el 15 %. Se excluyen "
                "los registros sin distancia estimada válida."
            ),
            "Evidencia mínima": (
                f"{min_sample} entregas comparables con distancia válida."
            ),
        },
        {
            "Hallazgo": "Calificaciones bajas",
            "Regla de detección": (
                "Se genera un hallazgo cuando hay suficientes pedidos "
                "retrasados con puntuación inferior a 3/5."
            ),
            "Evidencia mínima": (
                f"{min_sample} pedidos retrasados con reseña válida inferior a 3."
            ),
        },
        {
            "Hallazgo": "Diferencia de calificación",
            "Regla de detección": (
                "La calificación media de las entregas puntuales debe "
                "superar en al menos 0,5 puntos a la de las retrasadas."
            ),
            "Evidencia mínima": (
                f"{min_sample} pedidos con reseña válida en cada grupo."
            ),
        },
        {
            "Hallazgo": "Flete medio",
            "Regla de detección": (
                "Se identifica una diferencia descriptiva si el flete "
                "medio de las entregas retrasadas es al menos un 20 % "
                "mayor que el de las puntuales."
            ),
            "Evidencia mínima": (
                f"{min_sample} pedidos comparables en cada grupo."
            ),
        },
    ])

    records = json.loads(rules.to_json(orient="records"))

    return html.Details([
        html.Summary(
            "Reglas de detección y criterios de análisis",
            style={
                "cursor": "pointer",
                "fontWeight": "bold",
                "fontSize": "15px",
            },
        ),
        html.P(
            "Una entrega se considera retrasada cuando la fecha real "
            "es posterior a la fecha estimada. Las entregas sin ambas "
            "fechas no se clasifican como puntuales ni retrasadas."
        ),
        dash_table.DataTable(
            id="business-logistics-rules-table",
            data=records,
            columns=[
                {"name": "Hallazgo", "id": "Hallazgo"},
                {
                    "name": "Regla de detección",
                    "id": "Regla de detección",
                },
                {
                    "name": "Evidencia mínima",
                    "id": "Evidencia mínima",
                },
            ],
            style_table={
                "overflowX": "auto",
                "minWidth": "100%",
                "marginTop": "12px",
                "marginBottom": "12px",
            },
            style_cell={
                "fontFamily": "Arial",
                "fontSize": 12,
                "padding": "9px",
                "textAlign": "left",
                "whiteSpace": "normal",
                "height": "auto",
                "minWidth": "140px",
                "maxWidth": "360px",
            },
            style_header={
                "backgroundColor": "#f0f2f5",
                "fontWeight": "bold",
            },
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f8fafc",
                }
            ],
        ),
        html.P(
            f"El mínimo de {min_sample} casos reduce la influencia de "
            "grupos pequeños, pero no garantiza precisión estadística. "
            "Los hallazgos son descriptivos y no demuestran causalidad. "
            "Las diferencias entre grupos pueden estar relacionadas con "
            "distancia, época del año, productos u otros factores. Las "
            "acciones sugeridas deben validarse antes de tomar decisiones "
            "operativas.",
            className="business-note",
        ),
    ], open=False, style={
        "backgroundColor": "#ffffff",
        "padding": "14px",
        "borderRadius": "8px",
        "boxShadow": "0 1px 5px #dddddd",
        "marginBottom": "14px",
    })


def _periodo_decisiones(year, month):
    """Devuelve una etiqueta legible para los filtros temporales."""
    months = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
        "Diciembre",
    ]

    year_selected = year not in (None, "__todos__")
    month_selected = month not in (None, "__todos__")

    if year_selected and month_selected:
        try:
            month_name = months[int(month) - 1]
            return f"{month_name} {int(year)}"
        except (ValueError, TypeError, IndexError):
            return f"Período seleccionado ({year})"

    if year_selected:
        return f"Año {int(year)}"

    return "Todos los períodos"


def logistics_content(
    rows,
    view,
    dimension,
    min_sample,
    reference,
    year=None,
    month=None,
):
    orders = pedidos_logistica(rows)
    stats = resumen_logistica(orders)
    groups = agrupar_logistica(rows, dimension)

    if view == "decisiones":
        min_sample = MIN_CASES_LOGISTICS

    # Cuenta cada combinación única de pedido y vendedor entregada como un flete.
    if {"order_id", "seller_id"}.issubset(rows.columns):
        delivered_order_ids = orders.loc[
            orders["delivered"], "order_id"
        ].dropna().unique()

        fletes_realizados = (
            rows.loc[
                rows["order_id"].isin(delivered_order_ids),
                ["order_id", "seller_id"],
            ]
            .dropna()
            .drop_duplicates()
            .shape[0]
        )
    else:
        fletes_realizados = None

    content = []
    items = []
    limit = None
    period = _periodo_decisiones(year, month)

    if view == "decisiones":
        items, limit = _generar_hallazgos_logistica(
            rows,
            orders,
            period,
        )

    if view == "decisiones":
        delayed_reviews = orders[
            orders["late"] & orders["valid_review"].between(1, 5)
        ].copy()

        if not delayed_reviews.empty:
            delayed_reviews["delay_days"] = (
                pd.to_datetime(
                    delayed_reviews["delivered_date"],
                    errors="coerce",
                )
                - pd.to_datetime(
                    delayed_reviews["estimated_date"],
                    errors="coerce",
                )
            ).dt.total_seconds() / 86400

            delayed_reviews = delayed_reviews[
                delayed_reviews["delay_days"].gt(0)
            ]

        avg_delayed_review = (
            delayed_reviews["valid_review"].mean()
            if not delayed_reviews.empty
            else None
        )
        avg_delay = (
            delayed_reviews["delay_days"].mean()
            if not delayed_reviews.empty
            else None
        )
        avg_delayed_freight = (
            delayed_reviews["freight"].mean()
            if not delayed_reviews.empty
            else None
        )

        content.append(cards([
            (
                "Cantidad de hallazgos",
                number(len(items)),
                "Reglas activadas con la evidencia mínima requerida",
            ),
            (
                "Entregas con retraso",
                number(stats["late_pct"], 2, " %"),
                f"{number(stats['late'])} de {number(stats['eligible'])} "
                "entregas con fechas comparables",
            ),
            (
                "Calificación media de entregas retrasadas",
                number(avg_delayed_review, 2, " / 5"),
                "Promedio de las reseñas válidas de pedidos retrasados",
                "#F59E0B",
            ),
            (
                "Flete medio de entregas retrasadas",
                money(avg_delayed_freight),
                (
                    f"Retraso medio: {number(avg_delay, 2, ' días')}"
                    if avg_delay is not None
                    else "Sin datos de duración válidos"
                ),
            ),
        ], neutral=True))

    elif view == "gerencial":
        content.append(cards([
            (
                "Fletes realizados",
                number(fletes_realizados),
                "Combinaciones únicas de pedido y vendedor entregadas",
            ),
            (
                "Entregas con retraso",
                number(stats["late_pct"], 2, " %"),
                f"{number(stats['late'])} de {number(stats['eligible'])} "
                "con ambas fechas",
            ),
            (
                "Tiempo medio de entrega",
                number(stats["avg_days"], 2, " días"),
                "Solo entregados con duración válida",
            ),
            (
                "Costo de flete medio",
                money(stats["avg_freight"]),
                "Suma de los fletes de sus vendedores",
            ),
        ]))

    if orders.empty:
        content.append(
            html.Div(
                "No hay pedidos para estos filtros.",
                className="business-empty",
            )
        )

        if view == "gerencial":
            content.append(mapa_logistica_regiones(orders))

        if view == "decisiones":
            content.append(_logistics_findings(items))
            content.append(
                _seccion_reglas_logistica(
                    MIN_CASES_LOGISTICS,
                    limit,
                    stats,
                )
            )

        return html.Div(content)

    if view == "gerencial":
        vista_diaria = (
            year not in (None, "__todos__")
            and month not in (None, "__todos__")
        )

        if vista_diaria:
            diario = orders.copy()
            diario["period"] = (
                pd.to_datetime(
                    diario["purchase_date"],
                    errors="coerce",
                )
                .dt.normalize()
            )
            retrasos = diario.groupby("period", as_index=False).agg(
                eligible=("eligible", "sum"),
                late=("late", "sum"),
                orders=("order_id", "size"),
            )
            titulo_retrasos = "Retrasos por día de compra"
            etiqueta_periodo = "Día de compra"
            formato_fecha = "%d/%m/%Y"
        else:
            monthly = orders.assign(
                period=orders["purchase_date"].dt.to_period("M").astype(str)
            )
            retrasos = monthly.groupby("period", as_index=False).agg(
                eligible=("eligible", "sum"),
                late=("late", "sum"),
                orders=("order_id", "size"),
            )
            titulo_retrasos = "Retrasos por mes de compra"
            etiqueta_periodo = "Mes de compra"
            formato_fecha = None

        retrasos["late_pct"] = (
            100 * retrasos["late"]
            / retrasos["eligible"].where(retrasos["eligible"] > 0)
        )

        retrasos_fig = px.line(
            retrasos,
            x="period",
            y="late_pct",
            markers=True,
            custom_data=["eligible", "late"],
            labels={
                "period": etiqueta_periodo,
                "late_pct": "Entregas tardías (%)",
            },
        )
        retrasos_fig.update_traces(
            hovertemplate=(
                f"{etiqueta_periodo}: %{{x}}<br>"
                "Entregas tardías: %{y:.2f}%<br>"
                "Entregas comparables: %{customdata[0]}<br>"
                "Entregas tardías (cantidad): %{customdata[1]}"
                "<extra></extra>"
            )
        )

        if formato_fecha:
            retrasos_fig.update_xaxes(
                tickformat=formato_fecha,
                title=etiqueta_periodo,
            )

        content.append(
            html.Div(
                chart(
                    retrasos_fig,
                    titulo_retrasos,
                    height=390,
                ),
                className="business-main-chart",
            )
        )

        destinations = rows[
            ["order_id", "customer_state"]
        ].dropna().copy()
        destinations["state"] = (
            destinations["customer_state"]
            .astype(str)
            .str.strip()
            .str.upper()
        )
        destinations = (
            destinations.drop_duplicates(["order_id", "state"])
            .groupby("state", as_index=False)
            .agg(orders=("order_id", "nunique"))
            .sort_values("orders", ascending=False)
            .head(10)
            .sort_values("orders", ascending=True)
        )

        destinations_fig = px.bar(
            destinations,
            x="orders",
            y="state",
            orientation="h",
            labels={
                "orders": "Pedidos únicos",
                "state": "Estado de destino",
            },
            text="orders",
        )
        destinations_fig.update_traces(textposition="outside")

        content.append(html.Div([
            chart(
                destinations_fig,
                "Top 10 destinos con más pedidos",
                height=430,
            ),
            mapa_logistica_regiones(orders),
        ], className="business-charts"))

        content.append(html.P(
            f"{number(stats['without_delivery'])} pedidos no tienen fecha "
            "de entrega. No se consideran entregas puntuales ni retrasadas. "
            "Las barras muestran los 10 estados con más pedidos; el mapa "
            "cuenta pedidos únicos por región de destino. Son datos históricos, "
            "no una cola operativa actual.",
            className="business-note",
        ))

    elif view == "analitica":
        min_entregas = 30

        # La distancia sin información no es un grupo analítico válido.
        if dimension == "distance_band":
            analytic_groups = _limpiar_grupos_distancia(groups)
        else:
            analytic_groups = groups.copy()

        ranked = (
            analytic_groups[
                (analytic_groups["eligible"] >= min_entregas)
                & analytic_groups["late_pct"].notna()
            ]
            .sort_values("late_pct", ascending=False)
            .head(10)
            .sort_values("late_pct", ascending=True)
            .copy()
        )

        def color_retraso(value):
            if pd.isna(value):
                return "#9CA3AF"
            if value > 15:
                return "#DC2626"
            if value >= 10:
                return "#F97316"
            if value >= 5:
                return "#EAB308"
            return "#15803D"

        ranked["bar_color"] = ranked["late_pct"].apply(color_retraso)

        ranked_fig = None
        if not ranked.empty:
            ranked_fig = px.bar(
                ranked,
                x="late_pct",
                y="group",
                orientation="h",
                custom_data=["eligible", "late"],
                labels={
                    "late_pct": "Entregas tardías (%)",
                    "group": "Grupo",
                },
            )
            ranked_fig.update_traces(
                marker_color=ranked["bar_color"].tolist(),
                hovertemplate=(
                    "Grupo: %{y}<br>"
                    "Tasa de retraso: %{x:.2f}%<br>"
                    "Entregas comparables: %{customdata[0]}<br>"
                    "Entregas tardías: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )

        comparison = orders[
            orders["eligible"]
            & orders["valid_review"].between(1, 5)
        ].copy()

        reviews = comparison.groupby(
            "delivery_result",
            as_index=False,
        ).agg(
            score=("valid_review", "mean"),
            count=("order_id", "nunique"),
        )

        def color_resena(value):
            if pd.isna(value):
                return "#9CA3AF"
            if value < 3:
                return "#DC2626"
            if value > 4:
                return "#166534"
            return "#64748B"

        reviews_fig = None
        if not reviews.empty:
            reviews_fig = px.bar(
                reviews,
                x="delivery_result",
                y="score",
                text="count",
                custom_data=["count"],
                labels={
                    "delivery_result": "Resultado de la entrega",
                    "score": "Reseña media (1–5)",
                },
            )
            reviews_fig.update_traces(
                marker_color=[
                    color_resena(value)
                    for value in reviews["score"]
                ],
                textposition="outside",
                hovertemplate=(
                    "Resultado de entrega: %{x}<br>"
                    "Reseña media: %{y:.2f}/5<br>"
                    "Cantidad de pedidos: %{customdata[0]}"
                    "<extra></extra>"
                ),
            )
            reviews_fig.update_yaxes(range=[0, 5.5])

        content.append(table(
            analytic_groups,
            {
                "group": "Grupo",
                "orders": "Pedidos",
                "eligible": "Entregas comparables",
                "late": "Tardíos",
                "late_pct": "Retrasos (%)",
                "avg_days": "Entrega media (días)",
                "avg_freight": "Flete medio (R$)",
                "avg_review": "Reseña media",
            },
            "Detalle logístico",
            "Los vacíos indican ausencia de datos comparables.",
            export_button=True,
            table_id="business-logistics-detail-table",
        ))

        content.append(html.Div([
            chart(
                ranked_fig,
                "Top 10 grupos por tasa de retraso",
                height=430,
            ),
            chart(
                reviews_fig,
                "Reseña según tiempo de entrega",
                height=380,
            ),
        ], className="business-charts"))

        content.append(html.P(
            "El gráfico de retrasos incluye los 10 grupos con mayor tasa "
            "entre aquellos que tienen al menos 30 entregas comparables. "
            "Cuando la agrupación es por distancia, se excluyen los registros "
            "sin distancia estimada válida. Pasá el cursor sobre una barra "
            "para consultar el detalle.",
            className="business-note",
        ))

    else:
        routes_fig = _grafico_top_rutas(rows, MIN_CASES_LOGISTICS)
        reviews_fig = _grafico_resenas_por_puntuacion(orders)

        content.append(html.Div([
            chart(
                routes_fig,
                "Top 10 rutas por tasa de retraso",
                height=460,
            ),
            chart(
                reviews_fig,
                "Cantidad de pedidos por calificación y resultado de entrega",
                height=420,
            ),
        ], className="business-charts"))

        content.append(html.P(
            f"El gráfico de rutas muestra las 10 combinaciones de origen "
            f"y destino con mayor tasa de retraso, entre aquellas con al "
            f"menos {MIN_CASES_LOGISTICS} entregas comparables. "
            "El segundo gráfico compara la cantidad de pedidos con "
            "calificaciones de 1 a 5, separando entregas puntuales y "
            "retrasadas. Al pasar el cursor por cada barra se muestra "
            "el flete medio de esa combinación.",
            className="business-note",
        ))

        content.append(_logistics_findings(items))

        content.append(_seccion_reglas_logistica(
            MIN_CASES_LOGISTICS,
            limit,
            stats,
        ))

    return html.Div(content)


def customers_content(
    orders,
    view,
    dimension,
    min_sample,
    recency_days,
    reference,
):
    profiles = perfil_clientes(orders, reference)
    stats = resumen_clientes(profiles)
    groups = agrupar_clientes(profiles, dimension)

    reference_text = (
        reference.strftime("%d/%m/%Y")
        if not pd.isna(reference)
        else "sin fecha"
    )

    content = [
        html.P(
            f"Corte histórico: {reference_text}. Compras del período "
            "seleccionado; excluye cancelados y no disponibles. Valor de "
            "productos sin flete. No representa ganancias ni valor futuro "
            "del cliente.",
            className="business-note",
        ),
        cards([
            (
                "Clientes compradores",
                number(stats["customers"]),
                "Clientes únicos en el período",
            ),
            (
                "Clientes recurrentes",
                number(stats["repeat_pct"], 2, " %"),
                f"{number(stats['repeat'])} con al menos 2 pedidos en el período",
            ),
            (
                "Valor de productos",
                money(stats["spent"]),
                "Compras de los clientes seleccionados",
            ),
            (
                "Ticket por pedido",
                money(stats["ticket"]),
                f"Sobre {number(stats['orders'])} pedidos únicos",
            ),
        ]),
    ]

    if profiles.empty:
        content.append(
            html.Div(
                "No hay compradores para estos filtros.",
                className="business-empty",
            )
        )
        return html.Div(content)

    threshold = profiles.attrs["high_value_threshold"]

    content.append(html.P(
        f"Segmentación del período: recurrente = al menos 2 pedidos; "
        f"alto valor = gasto igual o superior al percentil 75 "
        f"({money(threshold)}). Recencia calculada al {reference_text}, "
        "nunca a la fecha actual. El segmento histórico Gold conserva "
        "la clasificación original y puede usar compras fuera del período.",
        className="business-note",
    ))

    if view == "gerencial":
        monthly = orders.assign(
            period=orders["purchase_date"].dt.to_period("M").astype(str)
        )
        monthly = monthly.groupby("period", as_index=False).agg(
            customers=("customer_id", "nunique")
        )
        segments = agrupar_clientes(profiles)

        content.append(html.Div([
            chart(
                px.line(
                    monthly,
                    x="period",
                    y="customers",
                    markers=True,
                    labels={
                        "period": "Mes de compra",
                        "customers": "Clientes",
                    },
                ),
                "Compradores activos por mes",
            ),
            chart(
                px.pie(
                    segments,
                    names="group",
                    values="customers",
                    hole=.55,
                ),
                "Segmentos recalculados del período",
            ),
        ], className="business-charts"))

        content.append(html.P(
            "Una persona puede comprar en varios meses: sumar compradores "
            "mensuales duplica clientes. La recurrencia no equivale a una "
            "tasa de retención por cohortes.",
            className="business-note",
        ))

    elif view == "analitica":
        content.append(html.Div([
            chart(
                px.bar(
                    groups,
                    x="group",
                    y="spent",
                    labels={
                        "group": "Segmento",
                        "spent": "Valor de productos (R$)",
                    },
                ),
                "Valor de compras por segmento",
            ),
            chart(
                px.bar(
                    groups,
                    x="group",
                    y="repeat_pct",
                    labels={
                        "group": "Segmento",
                        "repeat_pct": "Recurrentes (%)",
                    },
                ),
                "Recurrencia observada en el período",
            ),
        ], className="business-charts"))

    else:
        items = []
        inactive = profiles[
            profiles["high_value"]
            & profiles["recency_days"].gt(recency_days)
        ]

        if len(inactive) >= min_sample:
            items.append({
                "finding": "Alto valor sin compra reciente observada",
                "evidence": (
                    f"{number(len(inactive))} clientes, con más de "
                    f"{recency_days} días sin compra al {reference_text}; "
                    f"{money(inactive['spent'].sum())} en el período."
                ),
                "action": (
                    "Explorar una estrategia de reactivación y validar "
                    "estacionalidad. No se afirma abandono."
                ),
            })

        poor = groups[
            (groups["review_orders"] >= min_sample)
            & (groups["avg_review"] <= 3)
        ]

        for _, row in poor.iterrows():
            items.append({
                "finding": f"Baja satisfacción: {row['group']}",
                "evidence": (
                    f"{number(row['avg_review'], 2)}/5 sobre "
                    f"{number(row['review_orders'])} pedidos con reseña."
                ),
                "action": (
                    "Cruzar motivos con entregas y categorías; no atribuir "
                    "la causa solo al segmento."
                ),
            })

        if len(profiles) >= min_sample and stats["repeat_pct"] < 5:
            items.append({
                "finding": "Poca recompra observada en el período",
                "evidence": (
                    f"{number(stats['repeat'])}/{number(stats['customers'])} "
                    f"compradores ({number(stats['repeat_pct'], 2)} %) "
                    "tienen 2 o más pedidos."
                ),
                "action": (
                    "Examinar cohortes con igual tiempo de observación antes "
                    "de proponer acciones de fidelización."
                ),
            })

        content.append(findings(items))
        content.append(html.P(
            f"Umbrales exploratorios: mínimo {min_sample} casos, reseña "
            "media ≤ 3/5, recurrencia < 5 %. Seleccionar meses aislados "
            "reduce la oportunidad de observar recompras.",
            className="business-note",
        ))

    if view != "gerencial":
        content.append(table(
            groups,
            {
                "group": "Segmento",
                "customers": "Clientes",
                "orders": "Pedidos",
                "spent": "Productos (R$)",
                "ticket": "Ticket por pedido (R$)",
                "repeat_pct": "Recurrentes (%)",
                "recency_days": "Recencia media (días)",
                "avg_review": "Reseña media",
                "review_orders": "Pedidos con reseña",
            },
            "Detalle de clientes por segmento",
            "El ticket usa valor total / pedidos; las reseñas se ponderan "
            "por pedidos con puntuación.",
            table_id="business-customers-groups-table",
        ))

    return html.Div(content)