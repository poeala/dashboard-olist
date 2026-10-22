"""Tres vistas de Pagos con filtros de fecha de compra compartidos."""
from dash import dcc, html
from views.gerencial.customers import MONTHS, TODOS


def crear_vista_pagos(view, years):
    descriptions = {
        "gerencial": "Volumen registrado, uso de cuotas, pagos mixtos y evolución.",
        "analitica": "Medios de pago, valor de los pedidos, cuotas y segmentos históricos.",
        "decisiones": "Oportunidades comerciales basadas en contrastes observados y criterios explícitos.",
    }
    def select(label, name, options, disabled=False):
        return html.Div([
            html.Label(label, htmlFor=name),
            dcc.Dropdown(id=name, options=options, value=TODOS, clearable=False,
                         searchable=False, disabled=disabled),
        ], className="business-filter")

    def numeric(label, name, value, minimum, maximum):
        return html.Div([
            html.Label(label, htmlFor=name),
            dcc.Input(id=name, type="number", value=value, min=minimum, max=maximum, step=1, debounce=True),
        ], className="business-filter")

    all_option = [{"label": "Todos", "value": TODOS}]
    return html.Div([
        dcc.Store(id="payments-view", data=view),
        html.Div([
            html.Div([html.H2("Comportamiento y oportunidades de pago"),
                      html.P(descriptions[view], className="business-subtitle")]),
            html.Div([
                select("Año de compra", "payments-year", all_option + [
                    {"label": str(int(year)), "value": int(year)} for year in years]),
                select("Mes de compra", "payments-month", all_option + [
                    {"label": month, "value": i} for i, month in enumerate(MONTHS, 1)], True),
            ], className="business-period-filters"),
        ], className="business-heading business-heading-row"),
        html.Div([
            numeric("Mínimo de pedidos por grupo", "payments-minimum", 30, 5, 10000),
            numeric("Diferencia mínima de importe (%)", "payments-uplift", 20, 1, 200),
            numeric("Diferencia mínima de preferencia (pp)", "payments-preference", 10, 1, 100),
        ], className="business-filters", style={} if view == "decisiones" else {"display": "none"}),
        dcc.Loading(html.Div(id="payments-content"), type="circle", color="#003D7C"),
    ], className="business-page")
