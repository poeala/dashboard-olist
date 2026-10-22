"""Callbacks del dashboard de Logística."""

import logging

import pandas as pd
from dash import (
    ClientsideFunction,
    Input,
    Output,
    State,
    dcc,
    html,
)

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
                year,
                month,
            )

        except Exception:
            # Registra el tipo de excepción, el mensaje y la traza completa.
            logger.exception(
                "No se pudo actualizar Logística. "
                "Vista=%r, año=%r, mes=%r, dimensión=%r, mínimo=%r",
                view,
                year,
                month,
                dimension,
                min_sample,
            )

            return html.Div([
                html.H3("No pudimos cargar el análisis logístico"),
                html.P(
                    "Se produjo un error al calcular o presentar los datos. "
                    "Revisá la consola del servidor para identificar "
                    "la línea que lo provoca."
                ),
            ], className="business-empty", role="alert")

    @app.callback(
        Output("business-logistics-export-download", "data"),
        Input("business-logistics-export-button", "n_clicks"),
        State("business-logistics-detail-table", "data"),
        State("business-logistics-detail-table", "columns"),
        prevent_initial_call=True,
    )
    def exportar_detalle_logistico(n_clicks, data, columns):
        if not n_clicks or not data or not columns:
            return None

        column_ids = [column["id"] for column in columns]
        column_names = {
            column["id"]: column["name"]
            for column in columns
        }

        dataframe = pd.DataFrame(data)
        dataframe = dataframe.reindex(columns=column_ids)
        dataframe = dataframe.rename(columns=column_names)

        return dcc.send_data_frame(
            dataframe.to_csv,
            "detalle_logistico.csv",
            index=False,
            encoding="utf-8-sig",
        )