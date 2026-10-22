# Callbacks para navegar entre dashboards y vistas
from urllib.parse import parse_qs

from dash import Input, Output, ctx

from views.gerencial.sales import crear_vista_gerencial_ventas
from views.analitica.sales import crear_vista_analitica_ventas
from views.decisiones.sales import crear_vista_decisiones_ventas
from views.decisiones.customers import crear_vista_decisiones_clientes
from views.placeholder import crear_vista_vacia
from views.business import crear_vista_negocio
from views.gerencial.customers import crear_vista_clientes
from views.payments import crear_vista_pagos


def registrar_callbacks_navegacion(app, anios, meses, df):

    # Volver a Gerencial cada vez que cambia el dashboard.
    @app.callback(
        Output("selector_dashboard", "value"),
        Output("selector_vista", "value"),
        Output("dashboard-navigation", "style"),
        Input("selector_dashboard", "value"),
        Input("dashboard-location", "search"),
    )
    def reiniciar_vista(dashboard, search):
        params = parse_qs((search or "").lstrip("?"))

        requested_area = params.get("area", ["ventas"])[0]
        if requested_area not in {
            "ventas", "logistica", "clientes", "pagos"
        }:
            requested_area = "ventas"

        vista = params.get("vista", ["gerencial"])[0]
        if vista not in {"gerencial", "analitica", "decisiones"}:
            vista = "gerencial"

        if ctx.triggered_id == "selector_dashboard":
            vista = "gerencial"
        else:
            dashboard = requested_area

        embedded = params.get("embed", ["0"])[0] == "1"

        return (
            dashboard,
            vista,
            {"display": "none"} if embedded else {},
        )

    # Mostrar la vista seleccionada.
    @app.callback(
        Output("contenedor_dashboard", "children"),
        Input("selector_dashboard", "value"),
        Input("selector_vista", "value"),
    )
    def cambiar_vista(dashboard, vista):

        if dashboard == "ventas" and vista == "gerencial":
            return crear_vista_gerencial_ventas(anios, meses)

        if dashboard == "ventas" and vista == "analitica":
            return crear_vista_analitica_ventas()

        if dashboard == "ventas" and vista == "decisiones":
            return crear_vista_decisiones_ventas()

        # Mostrar la vista de decisiones de clientes.
        if dashboard == "clientes" and vista == "decisiones":
            return crear_vista_decisiones_clientes()

        # Las demás vistas de clientes mantienen su implementación.
        if dashboard == "clientes":
            return crear_vista_clientes(vista, anios)

        # Logística conserva la vista compartida original.
        if dashboard == "logistica":
            return crear_vista_negocio(dashboard, vista, anios)

        if dashboard == "pagos":
            return crear_vista_pagos(vista, anios)

        return crear_vista_vacia(dashboard, vista)
