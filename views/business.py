
from dash import dcc, html

from dash import dcc, html


MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def crear_vista_negocio(area, vista, anios):
    logistics = area == "logistica"
    title = "Desempeño logístico" if logistics else "Comportamiento de clientes"
    description = (
        "Seguimiento de entregas, retrasos y costos de flete."
        if logistics else
        "Análisis del comportamiento y la recurrencia de clientes."
    )

    dimensions = (
        [
            ("Estado de destino", "customer_state"),
            ("Vendedor", "seller_id"),
            ("Estado de origen", "seller_state"),
            ("Distancia estimada", "distance_band"),
        ]
        if logistics else
        [
            ("Segmento recalculado del período", "segment"),
            ("Segmento histórico Gold", "gold_segment"),
        ]
    )

    def dropdown(label, component_id, options, value, disabled=False):
        return html.Div([
            html.Label(label, htmlFor=component_id),
            dcc.Dropdown(
                id=component_id,
                options=options,
                value=value,
                clearable=False,
                searchable=False,
                disabled=disabled,
            ),
        ], className="business-filter")

    year_options = (
        [{"label": "Todos", "value": "__todos__"}]
        + [{"label": str(int(y)), "value": int(y)} for y in anios]
    )
    month_options = (
        [{"label": "Todos", "value": "__todos__"}]
        + [{"label": month, "value": i} for i, month in enumerate(MONTHS, 1)]
    )

    return html.Div([
        dcc.Store(id="business-area", data=area),
        dcc.Store(id="business-view", data=vista),

        html.Div([
            html.Div([
                html.H2(title),
                html.P(description, className="business-subtitle"),
            ], className="business-heading-text"),

            html.Div([
                dropdown(
                    "Año de compra",
                    "business-year",
                    year_options,
                    "__todos__",
                ),
                dropdown(
                    "Mes de compra",
                    "business-month",
                    month_options,
                    "__todos__",
                    disabled=True,
                ),
            ], className="business-period-filters"),
        ], className="business-heading business-heading-row"),

        html.Div([
            html.Div(
                dropdown(
                    "Agrupar por",
                    "business-dimension",
                    [
                        {"label": label, "value": value}
                        for label, value in dimensions
                    ],
                    dimensions[0][1],
                ),
                style={"display": "none"} if vista == "gerencial" else {},
            ),

            html.Div([
                html.Label(
                    "Mínimo de casos para alertas",
                    htmlFor="business-min-sample",
                ),
                dcc.Input(
                    id="business-min-sample",
                    type="number",
                    min=5,
                    max=10000,
                    step=1,
                    value=30,
                ),
            ], className="business-filter",
                style={"display": "none"} if vista == "gerencial" else {}),

            html.Div([
                html.Label(
                    "Días sin compra al corte",
                    htmlFor="business-recency",
                ),
                dcc.Input(
                    id="business-recency",
                    type="number",
                    min=1,
                    max=3650,
                    step=1,
                    value=90,
                ),
            ], className="business-filter",
                style={
                    "display": "none"
                } if logistics or vista != "decisiones" else {}),
        ], className="business-filters",
            style={"display": "none"} if vista == "gerencial" else {}),

        dcc.Loading(
            html.Div(id="business-content"),
            type="circle",
            color="#003D7C",
        ),
    ], className="business-page")
