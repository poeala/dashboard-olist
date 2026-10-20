
# Callbacks para filtrar fechas y actualizar los gráficos
from dash import Input, Output, State
from data.definitions import ventas_validas

from components.kpi import formato_numero
from components.charts import (
    crear_grafico_facturacion,
    crear_grafico_categorias,
    crear_grafico_vendedores
)


def registrar_callbacks_ventas(app, df):

    # Definir los nombres de los meses.
    nombres_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo",
        4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre",
        10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    # Mostrar los filtros correspondientes al modo seleccionado.
    @app.callback(
        Output("contenedor_trimestre", "style"),
        Output("contenedor_mes", "style"),
        Input("filtro_modo_fecha", "value")
    )
    def mostrar_filtros_fecha(modo):
        estilo_base = {"minWidth": "140px", "flex": "1"}

        if modo == "mensual":
            return {"display": "none"}, estilo_base

        return estilo_base, {"display": "none"}

    # Habilitar el trimestre solo para un año específico en modo anual.
    @app.callback(
        Output("filtro_trimestre", "disabled"),
        Input("filtro_modo_fecha", "value"),
        Input("filtro_anio", "value")
    )
    def habilitar_trimestre(modo, anio):
        return modo != "anual" or anio == "__todos__"

    # Restablecer el trimestre cuando corresponda.
    @app.callback(
        Output("filtro_trimestre", "value"),
        Input("filtro_anio", "value"),
        Input("filtro_modo_fecha", "value")
    )
    def restablecer_trimestre(anio, modo):
        if modo != "anual" or anio == "__todos__":
            return "__todos__"

        return "__todos__"

    # Actualizar los años disponibles según el modo de análisis.
    @app.callback(
        Output("filtro_anio", "options"),
        Output("filtro_anio", "value"),
        Input("filtro_modo_fecha", "value"),
        State("filtro_anio", "value")
    )
    def actualizar_opciones_anio(modo, anio_actual):
        anios_disponibles = sorted(
            df["anio"].dropna().astype(int).unique()
        )

        opciones_anio = [
            {"label": str(anio), "value": anio}
            for anio in anios_disponibles
        ]

        if modo == "anual":
            opciones_anio.insert(
                0, {"label": "Todos", "value": "__todos__"}
            )

            if anio_actual == "__todos__":
                return opciones_anio, "__todos__"

        if anio_actual in anios_disponibles:
            return opciones_anio, anio_actual

        return (
            opciones_anio,
            max(anios_disponibles) if anios_disponibles else None
        )

    # Actualizar los meses disponibles para el año seleccionado.
    @app.callback(
        Output("filtro_mes", "options"),
        Output("filtro_mes", "value"),
        Input("filtro_anio", "value"),
        State("filtro_mes", "value")
    )
    def actualizar_meses(anio, mes_actual):
        if anio is None or anio == "__todos__":
            return [], None

        datos_anio = df[df["anio"] == int(anio)]

        meses_disponibles = sorted(
            datos_anio["mes_numero"].dropna().astype(int).unique()
        )

        opciones_mes = [
            {"label": nombres_meses[mes], "value": mes}
            for mes in meses_disponibles
        ]

        if mes_actual in meses_disponibles:
            return opciones_mes, mes_actual

        return (
            opciones_mes,
            meses_disponibles[0] if meses_disponibles else None
        )

    # Aplicar los filtros y actualizar las tarjetas y los gráficos.
    @app.callback(
        Output("kpi_facturacion", "children"),
        Output("kpi_articulos", "children"),
        Output("kpi_compradores", "children"),
        Output("kpi_vendedores", "children"),
        Output("grafico_facturacion", "figure"),
        Output("grafico_categorias", "figure"),
        Output("grafico_vendedores", "figure"),
        Input("filtro_modo_fecha", "value"),
        Input("filtro_anio", "value"),
        Input("filtro_trimestre", "value"),
        Input("filtro_mes", "value")
    )
    def actualizar_dashboard(modo, anio, trimestre, mes):

        # Excluir pedidos cancelados o no disponibles.
        datos_base = ventas_validas(df)

        # Evitar consultas con filtros incompletos.
        if modo == "mensual" and (
            anio in (None, "__todos__") or mes is None
        ):
            datos = datos_base.iloc[0:0].copy()
        else:
            datos = datos_base.copy()

            # Aplicar el filtro de año.
            if anio != "__todos__" and anio is not None:
                datos = datos[datos["anio"] == int(anio)]

            # Aplicar el trimestre solo para un año específico.
            if (
                modo == "anual"
                and anio != "__todos__"
                and trimestre != "__todos__"
                and trimestre is not None
            ):
                datos = datos[
                    datos["trimestre"] == int(trimestre)
                ]

            # Aplicar el mes seleccionado dentro del año.
            if modo == "mensual" and mes is not None:
                datos = datos[
                    datos["mes_numero"] == int(mes)
                ]

        # Calcular los indicadores con los datos filtrados.
        facturacion = datos["price"].sum()
        articulos = len(datos)
        compradores = datos["customer_unique_id"].nunique()
        vendedores = datos["seller_id"].nunique()

        # Construir los gráficos.
        fig_facturacion = crear_grafico_facturacion(
            datos, modo, anio, mes
        )
        fig_categorias = crear_grafico_categorias(datos)
        fig_vendedores = crear_grafico_vendedores(datos)

        # Mostrar un mensaje cuando falta seleccionar un año o mes.
        if modo == "mensual" and (
            anio in (None, "__todos__") or mes is None
        ):
            mensaje = (
                "Seleccioná un año y un mes para consultar los datos"
            )
            fig_facturacion.update_layout(title=mensaje)
            fig_categorias.update_layout(title=mensaje)
            fig_vendedores.update_layout(title=mensaje)

        return (
            formato_numero(facturacion),
            formato_numero(articulos),
            formato_numero(compradores),
            formato_numero(vendedores),
            fig_facturacion,
            fig_categorias,
            fig_vendedores
        )
