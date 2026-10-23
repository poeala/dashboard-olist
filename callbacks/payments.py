
import logging

from dash import Input, Output, State, html

from data.business import cargar_pagos_bi
from data.business_metrics import filtrar_periodo, corte_periodo, ALL
from components.payments import payments_content
from views.gerencial.customers import MONTHS


logger = logging.getLogger(__name__)


def registrar_callbacks_pagos(app):
    @app.callback(
        Output("payments-month", "disabled"),
        Output("payments-month", "value"),
        Input("payments-year", "value"),
        State("payments-month", "value"),
    )
    def month_options(year, month):
        return (True, ALL) if year in (None, ALL) else (False, month or ALL)

    @app.callback(
        Output("payments-content", "children"),
        Input("payments-view", "data"),
        Input("payments-year", "value"),
        Input("payments-month", "value"),
    )
    def update(view, year, month):
        try:
            source = cargar_pagos_bi()

            if year in (None, ALL):
                month = ALL

            view = (
                view
                if view in {"gerencial", "analitica", "decisiones"}
                else "gerencial"
            )

            filtered = filtrar_periodo(source, year, month)
            reference = corte_periodo(source, year, month)

            if year in (None, ALL):
                period_label = "Todos los periodos"
            elif month in (None, ALL):
                period_label = f"Año {int(year)}"
            else:
                period_label = f"{MONTHS[int(month) - 1]} {int(year)}"

            return payments_content(
                filtered,
                view,
                reference,
                daily=year not in (None, ALL) and month not in (None, ALL),
                period_label=period_label,
            )

        except Exception as exc:
            logger.error(
                "No se pudo cargar Pagos: %s",
                type(exc).__name__,
            )
            return html.Div([
                html.H3("No pudimos cargar el análisis de pagos"),
                html.P(
                    "Verificá la conexión y la integridad de las tablas Gold. "
                    "Luego, volvé a intentar."
                ),
            ], className="business-empty", role="alert")
