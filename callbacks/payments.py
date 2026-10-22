import logging
from dash import Input, Output, State, html

from data.business import cargar_pagos_bi
from data.business_metrics import filtrar_periodo, corte_periodo, ALL
from components.payments import payments_content

logger = logging.getLogger(__name__)


def registrar_callbacks_pagos(app):
    @app.callback(
        Output("payments-month", "disabled"), Output("payments-month", "value"),
        Input("payments-year", "value"), State("payments-month", "value"),
    )
    def month_options(year, month):
        return (True, ALL) if year in (None, ALL) else (False, month or ALL)

    @app.callback(
        Output("payments-content", "children"),
        Input("payments-view", "data"), Input("payments-year", "value"),
        Input("payments-month", "value"), Input("payments-minimum", "value"),
        Input("payments-uplift", "value"), Input("payments-preference", "value"),
    )
    def update(view, year, month, minimum, uplift, preference):
        try:
            source = cargar_pagos_bi()
            if year in (None, ALL):
                month = ALL
            view = view if view in {"gerencial", "analitica", "decisiones"} else "gerencial"
            return payments_content(
                filtrar_periodo(source, year, month), view, corte_periodo(source, year, month),
                max(5, min(10000, int(minimum or 30))),
                max(1, min(200, float(uplift or 20))),
                max(1, min(100, float(preference or 10))),
            )
        except Exception as exc:
            logger.error("No se pudo cargar Pagos: %s", type(exc).__name__)
            return html.Div([
                html.H3("No pudimos cargar el análisis de pagos"),
                html.P("Verificá la conexión y la integridad de las tablas Gold. Luego, volvé a intentar."),
            ], className="business-empty", role="alert")
