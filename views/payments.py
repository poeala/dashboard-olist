
"""Tres vistas de Pagos con filtros de fecha de compra compartidos."""

from dash import dcc, html
from views.gerencial.customers import MONTHS, TODOS


def crear_vista_pagos(view, years):
    descriptions = {
        "gerencial": "Volumen, medios de pago y evolución.",
        "analitica": "Importes, cuotas y composición de los pagos.",
        "decisiones": "Diferencias observadas que merecen revisión.",
    }

    def select(label, name, options, disabled=False):
        return html.Div([
            html.Label(label, htmlFor=name),
            dcc.Dropdown(
                id=name,
                options=options,
                value=TODOS,
                clearable=False,
                searchable=False,
                disabled=disabled,
            ),
        ], className="business-filter")

    all_option = [{"label": "Todos", "value": TODOS}]

    return html.Div([
        dcc.Store(id="payments-view", data=view),
        html.Div([
            html.Div([
                html.H2("Comportamiento de pagos"),
                html.P(
                    descriptions[view],
                    className="business-subtitle",
                ),
            ], className="business-heading-text"),
            html.Div([
                select(
                    "Año de compra",
                    "payments-year",
                    all_option + [
                        {"label": str(int(year)), "value": int(year)}
                        for year in years
                    ],
                ),
                select(
                    "Mes de compra",
                    "payments-month",
                    all_option + [
                        {"label": month, "value": i}
                        for i, month in enumerate(MONTHS, 1)
                    ],
                    True,
                ),
            ], className="business-period-filters"),
        ], className="business-heading business-heading-row"),
        dcc.Loading(
            html.Div(id="payments-content"),
            type="circle",
            color="#003D7C",
        ),
    ], className="business-page")
