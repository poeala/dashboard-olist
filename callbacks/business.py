import logging

from dash import Input, Output, html

from data.business import cargar_clientes, cargar_logistica
from data.business_metrics import filtrar_periodo, corte_periodo
from components.business import customers_content, logistics_content

logger = logging.getLogger(__name__)


def registrar_callbacks_negocio(app):
    @app.callback(
        Output("business-content", "children"),
        Input("business-area", "data"), Input("business-view", "data"),
        Input("business-year", "value"), Input("business-month", "value"),
        Input("business-dimension", "value"), Input("business-min-sample", "value"),
        Input("business-recency", "value"),
    )
    def actualizar(area, view, year, month, dimension, min_sample, recency):
        if area not in {"logistica", "clientes"}:
            return html.P("Área no disponible.")
        if view not in {"gerencial", "analitica", "decisiones"}:
            view = "gerencial"
        min_sample = max(5, min(10000, int(min_sample or 30)))
        recency = max(1, min(3650, int(recency or 90)))
        try:
            source = cargar_logistica() if area == "logistica" else cargar_clientes()
            reference = corte_periodo(source, year, month)
            selected = filtrar_periodo(source, year, month)
            if area == "logistica":
                if dimension not in {"customer_state", "seller_id", "seller_state", "distance_band"}:
                    dimension = "customer_state"
                return logistics_content(selected, view, dimension, min_sample, reference)
            if dimension not in {"segment", "gold_segment"}:
                dimension = "segment"
            return customers_content(selected, view, dimension, min_sample, recency, reference)
        except Exception as exc:
            # Nunca mostrar SQL, host ni credenciales en el navegador o log.
            logger.error("No se pudo actualizar %s: %s", area, type(exc).__name__)
            return html.Div([
                html.H3("No pudimos cargar este análisis"),
                html.P("Verificá la conexión con Supabase y las tablas Gold. "
                       "Usá el botón de recarga del portal para volver a intentar."),
            ], className="business-empty", role="alert")
