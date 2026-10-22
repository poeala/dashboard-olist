
"""Presentación de resultados agregados; no envía registros de clientes al navegador."""
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, dash_table

from components.charts import aplicar_estilo_grafico
from data.business_metrics import (
    pedidos_logistica, resumen_logistica, agrupar_logistica,
    perfil_clientes, resumen_clientes, agrupar_clientes,
)


GEOJSON_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "br_states.geojson"
)


def number(value, decimals=0, suffix=""):
    if value is None or pd.isna(value):
        return "Sin datos"
    result = f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return result + suffix


def money(value):
    return "R$ " + number(value, 2) if value is not None and not pd.isna(value) else "Sin datos"


def cards(items):
    """Muestra tarjetas KPI sin subtítulos."""
    return html.Div([
        html.Div([
            html.P(label),
            html.H3(value),
        ], className="business-card")
        for label, value, _detail in items
    ], className="business-kpis")


def chart(fig, title, height=330):
    if fig is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Sin datos para estos filtros",
            showarrow=False,
            x=.5, y=.5,
            xref="paper", yref="paper",
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
            x=.5, y=.5,
            xref="paper", yref="paper",
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
            x=.5, y=.5,
            xref="paper", yref="paper",
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
        counts, on="state", how="left"
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


def table(df, columns, title, detail=None):
    selected = df[list(columns)].rename(columns=columns).copy()
    for col in selected.select_dtypes(include="number"):
        selected[col] = selected[col].round(2)
    records = json.loads(selected.to_json(orient="records", date_format="iso"))
    return html.Div([
        html.H3(title),
        html.P(detail, className="business-note") if detail else None,
        dash_table.DataTable(
            data=records,
            columns=[{"name": label, "id": label} for label in columns.values()],
            page_size=10,
            sort_action="native",
            filter_action="native",
            export_format="csv",
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
                {"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"}
            ],
        ),
        html.P(
            "Sin filas para los filtros seleccionados.",
            className="business-note",
        ) if selected.empty else None,
    ], className="business-table")


def findings(items):
    if not items:
        return html.Div([
            html.H3("Sin hallazgos con estos criterios"),
            html.P(
                "No se alcanzaron los umbrales o el mínimo de casos. "
                "Esto no equivale a ausencia de problemas."
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
    )


def logistics_content(rows, view, dimension, min_sample, reference):
    orders = pedidos_logistica(rows)
    stats = resumen_logistica(orders)
    groups = agrupar_logistica(rows, dimension)
    reference_text = (
        reference.strftime("%d/%m/%Y")
        if not pd.isna(reference)
        else "sin fecha"
    )

    delivered_count = int(orders["delivered"].sum())

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

    content = [
        html.P(
            f"Corte histórico: {reference_text}. Filtros por fecha de compra; "
            "excluye cancelados y no disponibles. Los importes son fletes "
            "registrados, no costos operativos ni márgenes.",
            className="business-note",
        ),
        cards([
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
                "Flete medio por pedido",
                money(stats["avg_freight"]),
                "Suma de los fletes de sus vendedores",
            ),
        ]),
    ]

    if orders.empty:
        content.append(
            html.Div(
                "No hay pedidos para estos filtros.",
                className="business-empty",
            )
        )
        return html.Div(content)

    if view == "gerencial":
        monthly = orders.assign(
            period=orders["purchase_date"].dt.to_period("M").astype(str)
        )
        monthly = monthly.groupby("period", as_index=False).agg(
            eligible=("eligible", "sum"),
            late=("late", "sum"),
            orders=("order_id", "size"),
        )
        monthly["late_pct"] = (
            100 * monthly["late"]
            / monthly["eligible"].where(monthly["eligible"] > 0)
        )

        monthly_fig = px.line(
            monthly,
            x="period",
            y="late_pct",
            markers=True,
            custom_data=["eligible", "late"],
            labels={
                "period": "Mes de compra",
                "late_pct": "Entregas tardías (%)",
            },
        )
        monthly_fig.update_traces(
            hovertemplate=(
                "Mes: %{x}<br>"
                "Entregas tardías: %{y:.2f}%<br>"
                "Entregas comparables: %{customdata[0]}<br>"
                "Entregas tardías (cantidad): %{customdata[1]}"
                "<extra></extra>"
            )
        )

        content.append(
            html.Div(
                chart(
                    monthly_fig,
                    "Retrasos por mes de compra",
                    height=390,
                ),
                className="business-main-chart",
            )
        )

        # Barras: los 10 estados de destino con más pedidos.
        destinations = rows[["order_id", "customer_state"]].dropna().copy()
        destinations["state"] = (
            destinations["customer_state"].astype(str).str.strip().str.upper()
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

        destination_map = mapa_pedidos_por_estado(
            rows,
            "customer_state",
            "Destinos con más pedidos",
        )

        content.append(
            html.Div([
                chart(
                    destinations_fig,
                    "Destinos con más pedidos",
                    height=430,
                ),
                chart(
                    destination_map,
                    "Distribución geográfica de pedidos",
                    height=430,
                ),
            ], className="business-charts")
        )

        content.append(html.P(
            f"{number(stats['without_delivery'])} pedidos no tienen fecha "
            "de entrega. No se consideran entregas puntuales ni retrasadas. "
            "Las barras muestran los 10 estados con más pedidos; el mapa "
            "cuenta pedidos únicos por estado. Son datos históricos, no "
            "una cola operativa actual.",
            className="business-note",
        ))

    elif view == "analitica":
        ranked = (
            groups[groups["eligible"] >= min_sample]
            .sort_values("late_pct", ascending=False)
            .head(12)
        )
        comparison = orders[
            orders["eligible"] & orders["valid_review"].notna()
        ]
        reviews = comparison.groupby(
            "delivery_result", as_index=False
        ).agg(
            score=("valid_review", "mean"),
            count=("order_id", "size"),
        )

        content.append(html.Div([
            chart(
                px.bar(
                    ranked,
                    x="late_pct",
                    y="group",
                    orientation="h",
                    labels={
                        "late_pct": "Entregas tardías (%)",
                        "group": "Grupo",
                    },
                ) if not ranked.empty else None,
                f"Mayor tasa de retraso · mínimo {min_sample} entregas",
            ),
            chart(
                px.bar(
                    reviews,
                    x="delivery_result",
                    y="score",
                    text="count",
                    labels={
                        "delivery_result": "Entrega",
                        "score": "Reseña media (1–5)",
                    },
                ) if not reviews.empty else None,
                "Reseñas según entrega · número de casos sobre barras",
            ),
        ], className="business-charts"))

    else:
        eligible_groups = groups[groups["eligible"] >= min_sample]
        limit = max(10, (stats["late_pct"] or 0) + 5)
        alerts = (
            eligible_groups[eligible_groups["late_pct"] > limit]
            .sort_values("late_pct", ascending=False)
        )
        items = [{
            "finding": f"Retrasos elevados: {r['group']}",
            "evidence": (
                f"{number(r['late'])}/{number(r['eligible'])} entregas "
                f"({number(r['late_pct'], 2)} %). "
                f"Umbral: {number(limit, 2)} %."
            ),
            "action": (
                "Revisar rutas, promesas de entrega y composición de "
                "pedidos antes de atribuir responsabilidades."
            ),
        } for _, r in alerts.head(12).iterrows()]

        content.append(findings(items))
        content.append(html.P(
            f"Regla: tasa de retraso superior al mayor entre 10 % y el "
            f"promedio seleccionado + 5 puntos; al menos {min_sample} "
            "entregas comparables por grupo.",
            className="business-note",
        ))

    if view != "gerencial":
        content.append(table(
            groups,
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
        ))

        if dimension != "customer_state":
            content.append(html.P(
                "Un pedido puede pertenecer a varios vendedores, orígenes "
                "o rangos de distancia; no sumar sus conteos para obtener "
                "el total. La fecha de entrega corresponde al pedido "
                "completo, no a un envío individual del vendedor. "
                "Las distancias son estimadas.",
                className="business-note",
            ))

    return html.Div(content)


def customers_content(orders, view, dimension, min_sample, recency_days, reference):
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
        ))

    return html.Div(content)
