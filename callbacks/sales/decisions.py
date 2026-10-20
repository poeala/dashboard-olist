
# Callbacks para la vista de toma de decisiones de ventas
import pandas as pd
import plotly.express as px
from dash import Input, Output, State

from components.charts import aplicar_estilo_grafico
from data.definitions import facturacion_mensual


def registrar_callbacks_decisiones_ventas(app, df):

    # Preparar las opciones del filtro de año.
    @app.callback(
        Output("decisiones_filtro_anio", "options"),
        Output("decisiones_filtro_anio", "value"),
        Input("selector_vista", "value"),
        State("decisiones_filtro_anio", "value")
    )
    def actualizar_opciones_anio(vista, anio_actual):
        anios = sorted(
            pd.to_numeric(df["anio"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
        )

        opciones = [
            {"label": "Todos", "value": "__todos__"}
        ] + [
            {"label": str(anio), "value": int(anio)}
            for anio in anios
        ]

        if anio_actual == "__todos__":
            valor = "__todos__"
        elif anio_actual in anios:
            valor = anio_actual
        else:
            valor = "__todos__"

        return opciones, valor

    # Actualizar los meses disponibles para el año seleccionado.
    @app.callback(
        Output("decisiones_filtro_mes", "options"),
        Output("decisiones_filtro_mes", "value"),
        Output("decisiones_filtro_mes", "disabled"),
        Input("decisiones_filtro_anio", "value"),
        State("decisiones_filtro_mes", "value")
    )
    def actualizar_opciones_mes(anio, mes_actual):
        nombres_meses = {
            1: "Enero",
            2: "Febrero",
            3: "Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Septiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre"
        }

        if anio in (None, "__todos__"):
            return (
                [{"label": "Todos", "value": "__todos__"}],
                "__todos__",
                True
            )

        anio_numerico = pd.to_numeric(
            df["anio"], errors="coerce"
        )

        meses = sorted(
            pd.to_numeric(
                df.loc[anio_numerico == int(anio), "mes_numero"],
                errors="coerce"
            )
            .dropna()
            .astype(int)
            .unique()
        )

        opciones = [
            {"label": "Todos", "value": "__todos__"}
        ] + [
            {"label": nombres_meses[mes], "value": mes}
            for mes in meses
        ]

        valor = (
            mes_actual
            if mes_actual in meses or mes_actual == "__todos__"
            else "__todos__"
        )

        return opciones, valor, False

    # Actualizar indicadores, gráficos y hallazgos.
    @app.callback(
        Output("decisiones_total_alertas", "children"),
        Output("decisiones_caida_facturacion", "children"),
        Output("decisiones_categorias_resenas", "children"),
        Output("decisiones_tasa_cancelacion", "children"),
        Output("decisiones_tasa_cancelacion", "style"),
        Output("decisiones_grafico_facturacion", "figure"),
        Output("decisiones_grafico_categorias", "figure"),
        Output("decisiones_tabla_hallazgos", "columns"),
        Output("decisiones_tabla_hallazgos", "data"),
        Input("selector_vista", "value"),
        Input("decisiones_filtro_anio", "value"),
        Input("decisiones_filtro_mes", "value")
    )
    def actualizar_decisiones(vista, anio, mes):

        nombres_meses = {
            1: "Enero",
            2: "Febrero",
            3: "Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Septiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre"
        }

        # Preparar los datos originales sin excluir estados.
        datos = df.copy()

        datos["order_purchase_date"] = pd.to_datetime(
            datos["order_purchase_date"],
            errors="coerce"
        )
        datos["price"] = pd.to_numeric(
            datos["price"],
            errors="coerce"
        )
        datos["review_score"] = pd.to_numeric(
            datos["review_score"],
            errors="coerce"
        )

        datos = datos.dropna(
            subset=["order_purchase_date"]
        )

        datos["product_category_name"] = (
            datos["product_category_name"]
            .fillna("Sin categoría")
        )

        datos["order_status"] = (
            datos["order_status"]
            .fillna("Sin estado")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        datos["periodo"] = (
            datos["order_purchase_date"].dt.to_period("M")
        )

        # Aplicar los filtros de año y mes.
        datos_periodo = datos.copy()

        if anio not in (None, "__todos__"):
            datos_periodo = datos_periodo[
                datos_periodo["order_purchase_date"].dt.year
                == int(anio)
            ]

        if (
            anio not in (None, "__todos__")
            and mes not in (None, "__todos__")
        ):
            datos_periodo = datos_periodo[
                datos_periodo["order_purchase_date"].dt.month
                == int(mes)
            ]

        # Calcular la facturación mensual y su variación.
        # Se usa el histórico completo para conservar el mes anterior
        # al calcular las caídas.
        # Misma base de facturación que Gerencial y Analítica.
        # Cancelación sigue calculándose sobre todos los pedidos más abajo.
        ventas_mensuales = facturacion_mensual(datos)

        caidas = ventas_mensuales.copy()

        if anio not in (None, "__todos__"):
            caidas = caidas[
                caidas["periodo"].map(lambda p: p.year) == int(anio)
            ]

        if (
            anio not in (None, "__todos__")
            and mes not in (None, "__todos__")
        ):
            caidas = caidas[
                caidas["periodo"].map(lambda p: p.month) == int(mes)
            ]

        caidas = caidas[
            caidas["Variación (%)"] < -10
        ].copy()

        # Preparar las reseñas únicas por pedido y categoría.
        resenas = (
            datos_periodo.dropna(subset=["review_score"])
            .drop_duplicates(
                subset=["order_id", "product_category_name"]
            )
        )

        categorias_resenas = (
            resenas.groupby("product_category_name")
            .agg(
                Puntuacion_promedio=("review_score", "mean"),
                Resenas_unicas=("order_id", "nunique")
            )
            .reset_index()
        )

        # Exigir cinco reseñas únicas para generar hallazgos.
        categorias_validas = categorias_resenas[
            categorias_resenas["Resenas_unicas"] >= 5
        ].copy()

        categorias_resenas_bajas = (
            categorias_validas[
                categorias_validas["Puntuacion_promedio"] <= 3.5
            ]
            .sort_values(
                ["Puntuacion_promedio", "Resenas_unicas"],
                ascending=[True, False]
            )
        )

        # Gráfico: cinco categorías con al menos cinco reseñas.
        categorias_con_hallazgo = set(
            categorias_resenas_bajas["product_category_name"]
        )

        categorias_grafico = (
            categorias_validas
            .sort_values(
                ["Puntuacion_promedio", "Resenas_unicas"],
                ascending=[True, False]
            )
            .head(5)
            .copy()
        )

        categorias_grafico["Color"] = (
            categorias_grafico["product_category_name"].apply(
                lambda categoria: (
                    "Reseñas bajas"
                    if categoria in categorias_con_hallazgo
                    else "Sin hallazgo"
                )
            )
        )

        if categorias_grafico.empty:
            fig_categorias = px.bar(
                title="No hay categorías con al menos 5 reseñas"
            )
        else:
            # En el gráfico horizontal, la menor puntuación debe quedar arriba.
            categorias_grafico = categorias_grafico.sort_values(
                "Puntuacion_promedio",
                ascending=False
            )

            fig_categorias = px.bar(
                categorias_grafico,
                x="Puntuacion_promedio",
                y="product_category_name",
                orientation="h",
                color="Color",
                color_discrete_map={
                    "Reseñas bajas": "#dc2626",
                    "Sin hallazgo": "#f59e0b"
                },
                text="Puntuacion_promedio",
                hover_data=["Resenas_unicas"],
                title="Top 5 de categorías con peor puntuación",
                labels={
                    "product_category_name": "Categoría",
                    "Puntuacion_promedio": "Puntuación promedio",
                    "Resenas_unicas": "Reseñas únicas",
                    "Color": "Resultado"
                }
            )

            fig_categorias.update_traces(
                texttemplate="%{text:.2f}",
                textposition="outside",
                cliponaxis=False
            )
            fig_categorias.update_layout(
                showlegend=False
            )

        fig_categorias.update_xaxes(
            range=[0, 5],
            title="Puntuación promedio (1 a 5)"
        )
        fig_categorias.update_yaxes(
            title="Categoría",
            automargin=True
        )
        aplicar_estilo_grafico(fig_categorias, 32)

        # Agrupar los estados de pedidos en tres categorías.
        pedidos = datos_periodo.drop_duplicates(
            subset=["order_id"]
        ).copy()

        pedidos["Estado agrupado"] = pedidos["order_status"].apply(
            lambda estado: (
                "Entregado"
                if estado == "delivered"
                else (
                    "Cancelado"
                    if estado in ("canceled", "unavailable")
                    else "En proceso"
                )
            )
        )

        estados = (
            pedidos.groupby("Estado agrupado")["order_id"]
            .nunique()
            .reindex(
                ["Entregado", "En proceso", "Cancelado"],
                fill_value=0
            )
            .rename("Pedidos")
            .reset_index()
        )

        estados = estados[estados["Pedidos"] > 0]

        if estados.empty:
            fig_facturacion = px.pie(
                title="No hay pedidos para el período seleccionado"
            )
        else:
            fig_facturacion = px.pie(
                estados,
                names="Estado agrupado",
                values="Pedidos",
                hole=0.35,
                title="Distribución de estados de pedidos",
                custom_data=["Pedidos"],
                color="Estado agrupado",
                color_discrete_map={
                    "Entregado": "#16a34a",
                    "En proceso": "#2563eb",
                    "Cancelado": "#dc2626"
                },
                category_orders={
                    "Estado agrupado": [
                        "Entregado",
                        "En proceso",
                        "Cancelado"
                    ]
                }
            )

            fig_facturacion.update_traces(
                textposition="inside",
                textinfo="label+percent",
                hovertemplate=(
                    "%{label}<br>"
                    "Pedidos: %{value:,}<br>"
                    "Porcentaje: %{percent}"
                    "<extra></extra>"
                )
            )

        aplicar_estilo_grafico(fig_facturacion, 24)

        # Calcular la tasa de cancelación sobre pedidos únicos.
        total_pedidos = pedidos["order_id"].nunique()

        pedidos_cancelados = pedidos[
            pedidos["order_status"].isin(
                ["canceled", "unavailable"]
            )
        ]["order_id"].nunique()

        tasa_cancelacion = (
            pedidos_cancelados / total_pedidos * 100
            if total_pedidos > 0
            else 0.0
        )

        color_tasa = (
            "#16a34a"
            if tasa_cancelacion < 5
            else "#dc2626"
        )

        estilo_tasa = {
            "fontSize": "25px",
            "margin": "0",
            "color": color_tasa
        }

        # Crear hallazgos sin acciones genéricas.
        hallazgos = []

        for _, fila in caidas.iterrows():
            variacion = fila["Variación (%)"]
            periodo = fila["periodo"]

            prioridad = (
                "Alta" if variacion <= -20 else "Media"
            )

            hallazgos.append({
                "_periodo_orden": periodo,
                "_prioridad_orden": (
                    0 if prioridad == "Alta" else 1
                ),
                "Prioridad": prioridad,
                "Hallazgo": "Caída de facturación",
                "Período": (
                    f"{nombres_meses[periodo.month]} {periodo.year}"
                ),
                "Evidencia": (
                    f"Valor de productos de R$ {fila['Facturación']:,.2f}; "
                    f"variación de {variacion:.2f}% "
                    "respecto del mes anterior."
                ),
                "Acción sugerida": "Revisar categorías y vendedores que explican la caída; "
                                  "contrastar con estacionalidad y cobertura del período."
            })

        # Crear hallazgos por reseñas bajas.
        if not categorias_resenas_bajas.empty:
            if (
                anio not in (None, "__todos__")
                and mes not in (None, "__todos__")
            ):
                periodo_resenas = (
                    f"{nombres_meses[int(mes)]} {int(anio)}"
                )
            elif anio not in (None, "__todos__"):
                periodo_resenas = f"Año {int(anio)}"
            else:
                periodo_resenas = "Todos los períodos"

            periodo_orden_resenas = (
                datos_periodo["periodo"].max()
                if not datos_periodo.empty
                else pd.Period("1900-01", freq="M")
            )

            for _, fila in categorias_resenas_bajas.iterrows():
                puntuacion = fila["Puntuacion_promedio"]
                categoria = fila["product_category_name"]
                cantidad = int(fila["Resenas_unicas"])

                prioridad = (
                    "Alta" if puntuacion <= 2.5 else "Media"
                )

                hallazgos.append({
                    "_periodo_orden": periodo_orden_resenas,
                    "_prioridad_orden": (
                        0 if prioridad == "Alta" else 1
                    ),
                    "Prioridad": prioridad,
                    "Hallazgo": f"Reseñas bajas: {categoria}",
                    "Período": periodo_resenas,
                    "Evidencia": (
                        f"Puntuación promedio de {puntuacion:.2f}/5 "
                        f"en {cantidad} reseñas únicas."
                    ),
                    "Acción sugerida": "Cruzar reseñas con entregas y vendedores antes de atribuir una causa."
                })

        # Ordenar por período más reciente y prioridad alta primero.
        hallazgos.sort(
            key=lambda fila: (
                fila["_periodo_orden"],
                fila["_prioridad_orden"]
            ),
            reverse=False
        )

        # Ordenar primero por fecha descendente y luego por prioridad.
        hallazgos.sort(
            key=lambda fila: fila["_prioridad_orden"]
        )
        hallazgos.sort(
            key=lambda fila: fila["_periodo_orden"],
            reverse=True
        )

        columnas = [
            {"name": nombre, "id": nombre}
            for nombre in [
                "Prioridad",
                "Hallazgo",
                "Período",
                "Evidencia",
                "Acción sugerida"
            ]
        ]

        datos_tabla = [
            {
                clave: valor
                for clave, valor in fila.items()
                if not clave.startswith("_")
            }
            for fila in hallazgos
        ]

        return (
            str(len(hallazgos)),
            str(len(caidas)),
            str(len(categorias_resenas_bajas)),
            f"{tasa_cancelacion:.2f}%",
            estilo_tasa,
            fig_facturacion,
            fig_categorias,
            columnas,
            datos_tabla
        )
