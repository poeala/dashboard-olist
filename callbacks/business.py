
import logging

from dash import Input, Output, State, html

from data.business import cargar_clientes, cargar_logistica
from data.business_metrics import filtrar_periodo, corte_periodo
from components.business import customers_content, logistics_content

logger = logging.getLogger(__name__)

TODOS = "__todos__"


def registrar_callbacks_negocio(app):

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
        Input("business-area", "data"),
        Input("business-view", "data"),
        Input("business-year", "value"),
        Input("business-month", "value"),
        Input("business-dimension", "value"),
        Input("business-min-sample", "value"),
        Input("business-recency", "value"),
    )
    def actualizar(area, view, year, month, dimension, min_sample, recency):
        if area not in {"logistica", "clientes"}:
            return html.P("Área no disponible.")

        if view not in {"gerencial", "analitica", "decisiones"}:
            view = "gerencial"

        min_sample = max(5, min(10000, int(min_sample or 30)))
        recency = max(1, min(3650, int(recency or 90)))

        # Sin año seleccionado, no se aplica ningún filtro mensual.
        if year == TODOS or year is None:
            month = TODOS

        try:
            source = (
                cargar_logistica()
                if area == "logistica"
                else cargar_clientes()
            )

            reference = corte_periodo(source, year, month)
            selected = filtrar_periodo(source, year, month)

            if area == "logistica":
                if dimension not in {
                    "customer_state",
                    "seller_id",
                    "seller_state",
                    "distance_band",
                }:
                    dimension = "customer_state"

                return logistics_content(
                    selected, view, dimension, min_sample, reference
                )

            if dimension not in {"segment", "gold_segment"}:
                dimension = "segment"

            return customers_content(
                selected, view, dimension, min_sample, recency, reference
            )

        except Exception as exc:
            # Nunca mostrar SQL, host ni credenciales en el navegador o log.
            logger.error(
                "No se pudo actualizar %s: %s",
                area,
                type(exc).__name__,
            )
            return html.Div([
                html.H3("No pudimos cargar este análisis"),
                html.P(
                    "Verificá la conexión con Supabase y las tablas Gold. "
                    "Usá el botón de recarga del portal para volver a intentar."
                ),
            ], className="business-empty", role="alert")
