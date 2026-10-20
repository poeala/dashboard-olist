from dash import dcc, html

MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def crear_vista_negocio(area, vista, anios):
    logistics = area == "logistica"
    title = "Desempeño logístico" if logistics else "Comportamiento de clientes"
    dimensions = (
        [("Estado de destino", "customer_state"), ("Vendedor", "seller_id"),
         ("Estado de origen", "seller_state"), ("Distancia estimada", "distance_band")]
        if logistics else
        [("Segmento recalculado del período", "segment"),
         ("Segmento histórico Gold", "gold_segment")]
    )

    def dropdown(label, component_id, options, value):
        return html.Div([
            html.Label(label, htmlFor=component_id),
            dcc.Dropdown(id=component_id, options=options, value=value, clearable=False),
        ], className="business-filter")

    return html.Div([
        dcc.Store(id="business-area", data=area),
        dcc.Store(id="business-view", data=vista),
        html.Div([
            html.H2(title),
            html.P("De los indicadores a la evidencia para decidir."),
        ], className="business-heading"),
        html.Div([
            dropdown("Año de compra", "business-year",
                     [{"label": "Todos", "value": "__todos__"}] +
                     [{"label": str(int(y)), "value": int(y)} for y in anios], "__todos__"),
            dropdown("Mes de compra", "business-month",
                     [{"label": "Todos", "value": "__todos__"}] +
                     [{"label": month, "value": i} for i, month in enumerate(MONTHS, 1)], "__todos__"),
            html.Div(dropdown("Agrupar por", "business-dimension",
                     [{"label": label, "value": value} for label, value in dimensions],
                     dimensions[0][1]),
                     style={"display": "none"} if vista == "gerencial" else {}),
            html.Div([
                html.Label("Mínimo de casos para alertas", htmlFor="business-min-sample"),
                dcc.Input(id="business-min-sample", type="number", min=5, max=10000, step=1, value=30),
            ], className="business-filter",
                style={"display": "none"} if vista == "gerencial" else {}),
            html.Div([
                html.Label("Días sin compra al corte", htmlFor="business-recency"),
                dcc.Input(id="business-recency", type="number", min=1, max=3650, step=1, value=90),
            ], className="business-filter",
                style={"display": "none"} if logistics or vista != "decisiones" else {}),
        ], className="business-filters"),
        dcc.Loading(html.Div(id="business-content"), type="circle", color="#003D7C"),
    ], className="business-page")
