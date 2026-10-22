
"""Callbacks del dashboard de Logística."""
import logging

from dash import ClientsideFunction, Input, Output, State, html

from data.business import cargar_logistica
from data.business_metrics import filtrar_periodo, corte_periodo
from components.business import logistics_content

logger = logging.getLogger(__name__)

TODOS = "__todos__"


def registrar_callbacks_negocio(app):
    app.clientside_callback(
        ClientsideFunction(namespace="logisticsMap", function_name="render"),
        Output("logistics-map-status", "children"),
        Input("logistics-map-data", "data"),
        Input("logistics-map-metric", "value"),
    )

    @app.callback(
        Output("business-month", "disabled"),
        Output("business-month", "value"),
        Input("business-year", "value"),
        State("business-month", "value"),
    )
    def actualizar_filtro_mes(year, month):
        if year == TODOS or year is None:
            return True, TODOS

        return False, month if month is not None else TODOS

    @app.callback(
        Output("business-content", "children"),
        Input("business-view", "data"),
        Input("business-year", "value"),
        Input("business-month", "value"),
        Input("business-dimension", "value"),
        Input("business-min-sample", "value"),
    )
    def actualizar(view, year, month, dimension, min_sample):
        if view not in {"gerencial", "analitica", "decisiones"}:
            view = "gerencial"

        try:
            min_sample = max(5, min(10000, int(min_sample or 30)))

            # Sin año seleccionado, no se aplica ningún filtro mensual.
            if year == TODOS or year is None:
                month = TODOS

            source = cargar_logistica()
            reference = corte_periodo(source, year, month)
            selected = filtrar_periodo(source, year, month)

            if dimension not in {
                "customer_state",
                "seller_id",
                "seller_state",
                "distance_band",
            }:
                dimension = "customer_state"

            return logistics_content(
                selected,
                view,
                dimension,
                min_sample,
                reference,
            )

        except Exception as exc:
            # No exponer detalles de conexión ni credenciales.
            logger.error(
                "No se pudo actualizar Logística: %s",
                type(exc).__name__,
            )

            return html.Div([
                html.H3("No pudimos cargar el análisis logístico"),
                html.P(
                    "Verificá la conexión con Supabase y las tablas Gold. "
                    "Luego, volvé a intentar."
                ),
            ], className="business-empty", role="alert")
