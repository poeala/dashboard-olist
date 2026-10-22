
"""Presentación de resultados de clientes."""
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, dash_table

from components.charts import aplicar_estilo_grafico
from data.business_metrics import (
    perfil_clientes,
    resumen_clientes,
    agrupar_clientes,
)


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
    if value is None or pd.isna(value):
        return "Sin datos"
    return "R$ " + number(value, 2)


def cards(items):
    """Muestra tarjetas de indicadores sin subtítulos."""
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


def table(df, columns, title, detail=None):
    selected = df[list(columns)].rename(columns=columns).copy()

    for col in selected.select_dtypes(include="number"):
        selected[col] = selected[col].round(2)

    records = json.loads(
        selected.to_json(orient="records", date_format="iso")
    )

    return html.Div([
        html.H3(title),
        html.P(detail, className="business-note") if detail else None,
        dash_table.DataTable(
            data=records,
            columns=[
                {"name": label, "id": label}
                for label in columns.values()
            ],
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
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f8fafc",
                }
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


def customers_content(
    orders,
    view,
    dimension,
    min_sample,
    recency_days,
    reference,
):
    """Construye la vista solicitada con resultados agregados de clientes."""
    profiles = perfil_clientes(orders, reference)
    stats = resumen_clientes(profiles)
    groups = agrupar_clientes(profiles, dimension)

    reference_text = (
        reference.strftime("%d/%m/%Y")
        if not pd.isna(reference)
        else "sin fecha"
    )

    customer_count = stats["customers"]
    order_count = stats["orders"]
    total_spent = stats["spent"]

    average_orders = (
        order_count / customer_count
        if customer_count
        else None
    )
    average_spent = (
        total_spent / customer_count
        if customer_count
        else None
    )

    content = [
        html.P(
            f"Corte histórico: {reference_text}. Filtros por fecha "
            "de compra; se excluyen pedidos cancelados y no disponibles. "
            "El gasto corresponde al valor de los productos, sin flete. "
            "La recurrencia se calcula dentro del período seleccionado.",
            className="business-note",
        ),
    ]

    if view == "gerencial":
        content.append(cards([
            (
                "Tasa de clientes recurrentes",
                number(stats["repeat_pct"], 2, " %"),
                "Clientes con dos o más pedidos en el período",
            ),
            (
                "Promedio de pedidos por cliente",
                number(average_orders, 2),
                "Pedidos únicos dividido por clientes únicos",
            ),
            (
                "Gasto promedio por cliente",
                money(average_spent),
                "Valor de productos dividido por clientes únicos",
            ),
            (
                "Ticket promedio por pedido",
                money(stats["ticket"]),
                "Valor de productos dividido por pedidos únicos",
            ),
        ]))
    else:
        content.append(cards([
            (
                "Clientes compradores",
                number(stats["customers"]),
                "Clientes únicos en el período",
            ),
            (
                "Clientes recurrentes",
                number(stats["repeat_pct"], 2, " %"),
                f"{number(stats['repeat'])} con al menos dos pedidos",
            ),
            (
                "Valor de productos",
                money(stats["spent"]),
                "Compras del período seleccionado",
            ),
            (
                "Ticket por pedido",
                money(stats["ticket"]),
                f"Sobre {number(stats['orders'])} pedidos únicos",
            ),
        ]))

    if profiles.empty:
        content.append(
            html.Div(
                "No hay compradores para estos filtros.",
                className="business-empty",
            )
        )
        return html.Div(content)

    if view != "gerencial":
        threshold = profiles.attrs["high_value_threshold"]

        content.append(html.P(
            f"Segmentación del período: recurrente = al menos dos pedidos; "
            f"alto valor = gasto igual o superior al percentil 75 "
            f"({money(threshold)}). La recencia se calcula al {reference_text}, "
            "no a la fecha actual. El segmento Gold conserva la clasificación "
            "histórica y puede incluir compras fuera del período seleccionado.",
            className="business-note",
        ))

    if view == "gerencial":
        monthly = orders.assign(
            period=orders["purchase_date"].dt.to_period("M").astype(str)
        )

        monthly = monthly.groupby("period", as_index=False).agg(
            customers=("customer_id", "nunique"),
            spent=("product_value", "sum"),
        )
        monthly["average_spent"] = monthly["spent"] / monthly["customers"]

        monthly_fig = px.line(
            monthly,
            x="period",
            y="customers",
            markers=True,
            labels={
                "period": "Mes de compra",
                "customers": "Compradores únicos",
            },
        )

        spending_fig = px.line(
            monthly, x="period", y="average_spent", markers=True,
            labels={"period": "Mes de compra", "average_spent": "Gasto por comprador (R$)"},
        )

        content.append(html.Div([
            chart(
                monthly_fig,
                "Compradores activos por mes",
                height=390,
            ),
            chart(
                spending_fig,
                "Evolución del gasto promedio por cliente",
                height=390,
            ),
        ], className="business-charts"))

        content.append(html.P(
            "Un cliente puede comprar en varios meses, por lo que los "
            "compradores mensuales no deben sumarse para calcular clientes "
            "únicos del período. La recurrencia observada tampoco equivale "
            "a una tasa de retención por cohortes.",
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
                ) if not groups.empty else None,
                "Valor de compras por segmento",
            ),
            chart(
                px.bar(
                    groups,
                    x="group",
                    y="repeat_pct",
                    labels={
                        "group": "Segmento",
                        "repeat_pct": "Clientes recurrentes (%)",
                    },
                ) if not groups.empty else None,
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
                    "la estacionalidad. No se afirma abandono."
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

        if (
            len(profiles) >= min_sample
            and stats["repeat_pct"] < 5
        ):
            items.append({
                "finding": "Poca recompra observada en el período",
                "evidence": (
                    f"{number(stats['repeat'])}/"
                    f"{number(stats['customers'])} compradores "
                    f"({number(stats['repeat_pct'], 2)} %) tienen "
                    "dos o más pedidos."
                ),
                "action": (
                    "Examinar cohortes con igual tiempo de observación "
                    "antes de proponer acciones de fidelización."
                ),
            })

        content.append(findings(items))
        content.append(html.P(
            f"Umbrales exploratorios: mínimo {min_sample} casos, reseña "
            "media ≤ 3/5 y recurrencia < 5 %. Seleccionar meses aislados "
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
            "El ticket usa valor total de productos / pedidos. "
            "Las reseñas se ponderan por pedidos con puntuación.",
        ))

    return html.Div(content)
