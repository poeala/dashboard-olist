"""Gráficos descriptivos del historial Gold, sin identificadores personales."""
import pandas as pd
import plotly.express as px
from dash import html

from components.customers import chart


def customer_analysis(df):
    if df.empty:
        return html.Div("No hay clientes para los filtros seleccionados.", className="business-empty")
    df = df.drop_duplicates("customer_id").copy()
    df["customer_segment"] = df["customer_segment"].fillna("Sin segmento")
    for column in ("total_orders", "total_spent"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    segments = df.groupby("customer_segment", as_index=False).agg(clientes=("customer_id", "nunique"))
    valid_orders = df[df["total_orders"].ge(1)].copy()
    valid_orders["recurrente"] = valid_orders["total_orders"].ge(2)
    recurrence = valid_orders.groupby("customer_segment", as_index=False).agg(
        clientes=("customer_id", "nunique"), recurrentes=("recurrente", "sum"),
    )
    recurrence["porcentaje"] = recurrence["recurrentes"] / recurrence["clientes"] * 100
    spending = df[df["total_spent"].ge(0)]
    # Agregar por frecuencia y segmento para no enviar puntos individuales.
    relation = valid_orders[valid_orders["total_spent"].ge(0)].groupby(
        ["customer_segment", "total_orders"], as_index=False,
    ).agg(gasto=("total_spent", "mean"), clientes=("customer_id", "nunique"))
    labels = {
        "customer_segment": "Segmento histórico", "clientes": "Clientes",
        "total_orders": "Pedidos históricos por cliente", "total_spent": "Gasto histórico (R$)",
        "gasto": "Gasto promedio (R$)", "porcentaje": "Recurrentes (%)", "recurrentes": "Recurrentes",
    }
    recurrence_fig = px.bar(recurrence, x="customer_segment", y="porcentaje", labels=labels,
                            hover_data=["clientes", "recurrentes"]) if not recurrence.empty else None
    if recurrence_fig is not None:
        recurrence_fig.update_yaxes(range=[0, 100])
    spending_fig = px.histogram(spending, x="total_spent", nbins=40, labels=labels) if not spending.empty else None
    if spending_fig is not None:
        spending_fig.update_yaxes(title="Clientes")
    return html.Div([
        chart(px.bar(segments, x="customer_segment", y="clientes", labels=labels), "Distribución de segmentos"),
        chart(recurrence_fig, "Recurrencia por segmento"),
        chart(spending_fig, "Distribución del gasto por cliente"),
        chart(px.scatter(relation, x="total_orders", y="gasto", size="clientes",
                         color="customer_segment", labels=labels, size_max=45)
              if not relation.empty else None, "Relación entre frecuencia y gasto"),
    ], className="business-charts")
