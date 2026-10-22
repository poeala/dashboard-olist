from dash import dcc, html

from views.analitica.customers import crear_vista_analitica_clientes

MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

TODOS = "__todos__"


def crear_vista_clientes(vista, anios):
    # La vista analítica utiliza su propio layout y sus propios callbacks.
    if vista == "analitica":
        return crear_vista_analitica_clientes()

    dimensions = [
        ("Segmento recalculado del período", "segment"),
        ("Segmento histórico Gold", "gold_segment"),
    ]

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
        [{"label": "Todos", "value": TODOS}]
        + [{"label": str(int(year)), "value": int(year)} for year in anios]
    )

    month_options = (
        [{"label": "Todos", "value": TODOS}]
        + [
            {"label": month, "value": index}
            for index, month in enumerate(MONTHS, 1)
        ]
    )

    return html.Div([
        dcc.Store(id="customers-view", data=vista),

        html.Div([
            html.Div([
                html.H2("Comportamiento de clientes"),
                html.P(
                    "Análisis del comportamiento y la recurrencia de clientes.",
                    className="business-subtitle",
                ),
            ], className="business-heading-text"),

            html.Div([
                dropdown(
                    "Año de compra",
                    "customers-year",
                    year_options,
                    TODOS,
                ),
                dropdown(
                    "Mes de compra",
                    "customers-month",
                    month_options,
                    TODOS,
                    disabled=True,
                ),
            ], className="business-period-filters"),
        ], className="business-heading business-heading-row"),

        html.Div([
            html.Div(
                dropdown(
                    "Agrupar por",
                    "customers-dimension",
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
                    htmlFor="customers-min-sample",
                ),
                dcc.Input(
                    id="customers-min-sample",
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
                    htmlFor="customers-recency",
                ),
                dcc.Input(
                    id="customers-recency",
                    type="number",
                    min=1,
                    max=3650,
                    step=1,
                    value=90,
                ),
            ], className="business-filter",
                style={"display": "none"} if vista != "decisiones" else {}),
        ], className="business-filters",
            style={"display": "none"} if vista == "gerencial" else {}),

        dcc.Loading(
            html.Div(id="customers-content"),
            type="circle",
            color="#003D7C",
        ),
    ], className="business-page")
