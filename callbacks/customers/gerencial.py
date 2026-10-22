
"""Callbacks del dashboard de Clientes."""
import logging

from dash import Input, Output, State, html

from data.business import cargar_clientes
from data.business_metrics import filtrar_periodo, corte_periodo
from components.customers import customers_content

logger = logging.getLogger(__name__)

TODOS = "__todos__"


def registrar_callbacks_clientes(app):

    @app.callback(
        Output("customers-month", "disabled"),
        Output("customers-month", "value"),
        Input("customers-year", "value"),
        State("customers-month", "value"),
    )
    def actualizar_filtro_mes(year, month):
        if year == TODOS or year is None:
            return True, TODOS

        return False, month if month is not None else TODOS

    @app.callback(
        Output("customers-content", "children"),
        Input("customers-view", "data"),
        Input("customers-year", "value"),
        Input("customers-month", "value"),
        Input("customers-dimension", "value"),
        Input("customers-min-sample", "value"),
        Input("customers-recency", "value"),
    )
    def actualizar(view, year, month, dimension, min_sample, recency):
        if view not in {"gerencial", "analitica", "decisiones"}:
            view = "gerencial"

        try:
            min_sample = max(5, min(10000, int(min_sample or 30)))
            recency = max(1, min(3650, int(recency or 90)))

            # Si no se selecciona año, se consideran todos los meses.
            if year == TODOS or year is None:
                month = TODOS

            source = cargar_clientes()
            reference = corte_periodo(source, year, month)
            selected = filtrar_periodo(source, year, month)

            if dimension not in {"segment", "gold_segment"}:
                dimension = "segment"

            return customers_content(
                selected,
                view,
                dimension,
                min_sample,
                recency,
                reference,
            )

        except Exception as exc:
            logger.error(
                "No se pudo actualizar Clientes: %s",
                type(exc).__name__,
            )

            return html.Div([
                html.H3("No pudimos cargar el análisis de clientes"),
                html.P(
                    "Verificá la conexión con Supabase y las tablas Gold. "
                    "Luego, volvé a intentar."
                ),
            ], className="business-empty", role="alert")
