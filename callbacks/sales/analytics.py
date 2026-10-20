# Callbacks para la vista analítica de ventas
from io import BytesIO
from html import escape

import pandas as pd
import plotly.express as px

from dash import Input, Output, State, dcc

from data.sales import consultar_ventas_agrupadas
from data.definitions import ventas_validas


def registrar_callbacks_analitica_ventas(app, df):

    # Preparar las opciones de los filtros.
    anios = sorted(df["anio"].dropna().astype(int).unique())

    opciones_anio = [
        {"label": "Todos", "value": "__todos__"}
    ] + [
        {"label": str(anio), "value": int(anio)}
        for anio in anios
    ]

    opciones_estado = [
        {"label": "Todos", "value": "__todos__"},
        {"label": "Entregado", "value": "__entregado__"},
        {"label": "En proceso", "value": "__en_proceso__"}
    ]

    nombres_metricas = {
        "facturacion": "Facturación",
        "articulos": "Cantidad de artículos",
        "pedidos": "Pedidos únicos",
        "compradores": "Compradores únicos"
    }

    nombres_dimensiones = {
        "anio": "Año",
        "trimestre": "Trimestre",
        "mes": "Mes",
        "fecha": "Fecha",
        "categoria": "Categoría",
        "vendedor": "Vendedor",
        "estado": "Estado"
    }

    # Cargar las opciones de los filtros cuando aparece la vista.
    @app.callback(
        Output("analitica_anio", "options"),
        Output("analitica_estado", "options"),
        Input("selector_vista", "value")
    )
    def cargar_opciones_filtros(vista):
        return opciones_anio, opciones_estado

    # Calcular los totales utilizando los filtros seleccionados.
    def calcular_totales(anio, estado, metricas):
        df_filtrado = df.copy()

        if anio is not None:
            df_filtrado = df_filtrado[
                pd.to_numeric(
                    df_filtrado["anio"], errors="coerce"
                ) == int(anio)
            ]

        estados = (
            df_filtrado["order_status"]
            .fillna("Sin estado")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        if estado == "__entregado__":
            df_filtrado = df_filtrado[
                estados == "delivered"
            ]

        elif estado == "__en_proceso__":
            df_filtrado = df_filtrado[
                ~estados.isin([
                    "delivered",
                    "canceled",
                    "unavailable"
                ])
            ]

        else:
            df_filtrado = ventas_validas(df_filtrado)

        totales = {}

        if "facturacion" in metricas:
            totales["Facturación"] = pd.to_numeric(
                df_filtrado["price"], errors="coerce"
            ).sum()

        if "articulos" in metricas:
            totales["Cantidad de artículos"] = len(df_filtrado)

        if "pedidos" in metricas:
            totales["Pedidos únicos"] = (
                df_filtrado["order_id"].nunique()
            )

        if "compradores" in metricas:
            totales["Compradores únicos"] = (
                df_filtrado["customer_unique_id"].nunique()
            )

        return totales

    # Actualizar la tabla, sus estilos y el gráfico.
    @app.callback(
        Output("tabla_analitica_ventas", "columns"),
        Output("tabla_analitica_ventas", "data"),
        Output("tabla_analitica_ventas", "style_data_conditional"),
        Output("grafico_analitica_ventas", "figure"),
        Input("analitica_dimension", "value"),
        Input("analitica_dimension_secundaria", "value"),
        Input("analitica_anio", "value"),
        Input("analitica_estado", "value"),
        Input("analitica_metricas", "value")
    )
    def actualizar_analisis(
        dimension, secundaria, anio, estado, metricas
    ):
        # Evitar consultas si no hay métricas seleccionadas.
        if not metricas:
            figura = px.bar(
                title="Seleccioná al menos una métrica"
            )
            figura.update_layout(template="plotly_white")
            return [], [], [], figura

        # Convertir las opciones que representan "todos" o "ninguna".
        secundaria = (
            None if secundaria == "__ninguna__"
            else secundaria
        )

        anio = None if anio == "__todos__" else anio

        # Consultar los datos agrupados en PostgreSQL.
        df_analisis = consultar_ventas_agrupadas(
            dimension=dimension,
            dimension_secundaria=secundaria,
            metricas=metricas,
            anio=anio,
            estado=estado
        )

        # Identificar las columnas de las dimensiones seleccionadas.
        nombre_dimension = nombres_dimensiones[dimension]

        hay_doble_agrupacion = (
            secundaria is not None and secundaria != dimension
        )

        nombre_dimension_secundaria = (
            nombres_dimensiones[secundaria]
            if hay_doble_agrupacion
            else None
        )

        # Calcular variaciones cuando la dimensión principal es temporal.
        calcular_variacion = (
            dimension in ("mes", "anio")
            or (dimension == "trimestre" and anio is not None)
        )

        if calcular_variacion and not df_analisis.empty:

            # Ordenar cronológicamente dentro de cada grupo secundario.
            columnas_orden = (
                [nombre_dimension_secundaria, nombre_dimension]
                if hay_doble_agrupacion
                else [nombre_dimension]
            )

            df_analisis = df_analisis.sort_values(
                columnas_orden
            ).copy()

            # Calcular diferencias absolutas y porcentuales.
            for metrica in metricas:
                nombre = nombres_metricas[metrica]

                if hay_doble_agrupacion:
                    anterior = df_analisis.groupby(
                        nombre_dimension_secundaria,
                        dropna=False
                    )[nombre].shift(1)
                else:
                    anterior = df_analisis[nombre].shift(1)

                diferencia = df_analisis[nombre] - anterior

                porcentaje = (
                    diferencia / anterior.where(anterior != 0)
                ) * 100

                df_analisis[f"Variación {nombre}"] = diferencia.round(2)
                df_analisis[f"% variación {nombre}"] = porcentaje.round(2)

            # Mostrar los resultados en orden cronológico.
            columnas_orden_final = (
                [nombre_dimension, nombre_dimension_secundaria]
                if hay_doble_agrupacion
                else [nombre_dimension]
            )

            df_analisis = df_analisis.sort_values(
                columnas_orden_final
            )

        # Agregar la fila TOTAL después de calcular las variaciones.
        totales = calcular_totales(anio, estado, metricas)

        fila_total = {
            columna: None
            for columna in df_analisis.columns
        }

        fila_total[nombre_dimension] = "TOTAL"

        if hay_doble_agrupacion:
            fila_total[nombre_dimension_secundaria] = ""

        for nombre, valor in totales.items():
            if nombre in fila_total:
                fila_total[nombre] = valor

        df_analisis = pd.concat(
            [
                df_analisis,
                pd.DataFrame([fila_total])
            ],
            ignore_index=True
        )

        # Preparar las columnas de la tabla.
        columnas_numericas = set(nombres_metricas.values())

        columnas_numericas.update(
            columna
            for columna in df_analisis.columns
            if columna.startswith("Variación ")
            or columna.startswith("% variación ")
        )

        columnas = [
            {
                "name": columna,
                "id": columna,
                "type": (
                    "numeric"
                    if columna in columnas_numericas
                    else "text"
                )
            }
            for columna in df_analisis.columns
        ]

        # Redondear los valores numéricos a dos decimales.
        datos = df_analisis.round(2).to_dict("records")

        # Resaltar la fila TOTAL.
        estilos_condicionales = [
            {
                "if": {
                    "filter_query": '{' + nombre_dimension + '} = "TOTAL"'
                },
                "fontWeight": "bold",
                "backgroundColor": "#f0f2f5",
                "borderTop": "2px solid #9ca3af"
            }
        ]

        # Aplicar colores según el signo de las variaciones.
        for columna in df_analisis.columns:
            if (
                columna.startswith("Variación ")
                or columna.startswith("% variación ")
            ):
                estilos_condicionales.extend([
                    {
                        "if": {
                            "filter_query": f"{{{columna}}} > 0",
                            "column_id": columna
                        },
                        "color": "green",
                        "fontWeight": "bold"
                    },
                    {
                        "if": {
                            "filter_query": f"{{{columna}}} < 0",
                            "column_id": columna
                        },
                        "color": "red",
                        "fontWeight": "bold"
                    }
                ])

        # Seleccionar la primera métrica para el gráfico.
        nombre_metrica = nombres_metricas[metricas[0]]

        # Excluir la fila TOTAL del gráfico.
        datos_grafico = df_analisis[
            df_analisis[nombre_dimension] != "TOTAL"
        ].copy()

        if nombre_metrica not in datos_grafico.columns:
            figura = px.bar(
                title="No se encontró la métrica seleccionada"
            )
            figura.update_layout(template="plotly_white")
            return (
                columnas, datos, estilos_condicionales, figura
            )

        if datos_grafico.empty:
            figura = px.bar(
                title="No hay datos para los filtros seleccionados"
            )

        elif hay_doble_agrupacion:
            datos_grafico[
                nombre_dimension_secundaria
            ] = datos_grafico[
                nombre_dimension_secundaria
            ].astype(str)

            figura = px.bar(
                datos_grafico,
                x=nombre_dimension,
                y=nombre_metrica,
                color=nombre_dimension_secundaria,
                barmode="group",
                title=nombre_metrica,
                hover_data=[
                    nombre_dimension,
                    nombre_dimension_secundaria
                ]
            )

        else:
            if dimension in ("anio", "trimestre", "mes", "fecha"):
                datos_grafico = datos_grafico.sort_values(
                    nombre_dimension,
                    ascending=True
                )
            else:
                datos_grafico = datos_grafico.sort_values(
                    nombre_metrica,
                    ascending=True
                ).head(20)

            figura = px.bar(
                datos_grafico,
                x=nombre_dimension,
                y=nombre_metrica,
                title=nombre_metrica,
                hover_data=[nombre_dimension],
                category_orders={
                    nombre_dimension: (
                        datos_grafico[nombre_dimension]
                        .astype(str)
                        .tolist()
                    )
                }
            )

        figura.update_layout(
            template="plotly_white",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
            xaxis_title=nombre_dimension,
            yaxis_title=nombre_metrica
        )

        figura.update_xaxes(type="category")

        return (
            columnas,
            datos,
            estilos_condicionales,
            figura
        )

    # Exportar la tabla completa a PDF.
    @app.callback(
        Output("descargar_analitica_pdf", "data"),
        Input("btn_exportar_analitica_pdf", "n_clicks"),
        State("tabla_analitica_ventas", "columns"),
        State("tabla_analitica_ventas", "data"),
        State("analitica_dimension", "value"),
        State("analitica_dimension_secundaria", "value"),
        State("analitica_anio", "value"),
        State("analitica_estado", "value"),
        State("analitica_metricas", "value"),
        prevent_initial_call=True
    )
    def exportar_analisis_pdf(
        n_clicks,
        columnas,
        datos,
        dimension,
        secundaria,
        anio,
        estado,
        metricas
    ):
        if not n_clicks or not columnas:
            return None

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle
        )

        # Crear el documento en orientación horizontal.
        buffer = BytesIO()

        documento = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm
        )

        estilos = getSampleStyleSheet()

        estilo_celda = ParagraphStyle(
            "Celda",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            alignment=TA_LEFT,
            wordWrap="CJK"
        )

        estilo_encabezado = ParagraphStyle(
            "EncabezadoTabla",
            parent=estilo_celda,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#222222")
        )

        contenido = [
            Paragraph("Análisis de ventas", estilos["Title"]),
            Spacer(1, 3 * mm)
        ]

        # Mostrar los filtros aplicados.
        nombre_dimension = {
            "anio": "Año",
            "trimestre": "Trimestre",
            "mes": "Mes",
            "fecha": "Fecha",
            "categoria": "Categoría",
            "vendedor": "Vendedor",
            "estado": "Estado"
        }

        nombre_estado = {
            "__todos__": "Todos",
            "__entregado__": "Entregado",
            "__en_proceso__": "En proceso"
        }

        nombre_metricas = {
            "facturacion": "Facturación",
            "articulos": "Cantidad de artículos",
            "pedidos": "Pedidos únicos",
            "compradores": "Compradores únicos"
        }

        texto_anio = "Todos" if anio == "__todos__" else str(anio)
        texto_secundaria = (
            "Ninguna"
            if secundaria == "__ninguna__"
            else nombre_dimension.get(secundaria, str(secundaria))
        )
        texto_estado = nombre_estado.get(estado, str(estado))
        texto_metricas = ", ".join(
            nombre_metricas.get(metrica, metrica)
            for metrica in (metricas or [])
        )

        filtros = (
            f"<b>Agrupar por:</b> "
            f"{escape(nombre_dimension.get(dimension, str(dimension)))}"
            f"&nbsp;&nbsp; <b>Agrupación secundaria:</b> "
            f"{escape(texto_secundaria)}"
            f"&nbsp;&nbsp; <b>Año:</b> {escape(texto_anio)}"
            f"<br/><b>Estado del pedido:</b> {escape(texto_estado)}"
            f"&nbsp;&nbsp; <b>Métricas:</b> {escape(texto_metricas)}"
        )

        contenido.extend([
            Paragraph(filtros, estilos["Normal"]),
            Spacer(1, 5 * mm)
        ])

        # Preparar los encabezados y todos los registros de la tabla.
        encabezados = [
            Paragraph(
                escape(str(columna["name"])),
                estilo_encabezado
            )
            for columna in columnas
        ]

        filas = [encabezados]
        fila_total_pdf = None

        for indice, registro in enumerate(datos or [], start=1):
            fila = []

            for columna in columnas:
                valor = registro.get(columna["id"])

                if valor is None:
                    texto = ""
                else:
                    try:
                        texto = "" if pd.isna(valor) else str(valor)
                    except (TypeError, ValueError):
                        texto = str(valor)

                fila.append(
                    Paragraph(escape(texto), estilo_celda)
                )

            filas.append(fila)

            if registro.get(nombre_dimension[dimension]) == "TOTAL":
                fila_total_pdf = indice

        # Distribuir el ancho disponible entre las columnas.
        ancho_disponible = landscape(A4)[0] - 24 * mm
        cantidad_columnas = max(len(columnas), 1)

        pesos = [
            1.6 if indice == 0 else 1
            for indice in range(cantidad_columnas)
        ]

        suma_pesos = sum(pesos)

        anchos = [
            ancho_disponible * peso / suma_pesos
            for peso in pesos
        ]

        tabla = Table(
            filas,
            colWidths=anchos,
            repeatRows=1,
            hAlign="LEFT"
        )

        estilos_tabla = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f2f5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ]

        if fila_total_pdf is not None:
            estilos_tabla.extend([
                (
                    "BACKGROUND",
                    (0, fila_total_pdf),
                    (-1, fila_total_pdf),
                    colors.HexColor("#e5e7eb")
                ),
                (
                    "FONTNAME",
                    (0, fila_total_pdf),
                    (-1, fila_total_pdf),
                    "Helvetica-Bold"
                ),
                (
                    "LINEABOVE",
                    (0, fila_total_pdf),
                    (-1, fila_total_pdf),
                    1,
                    colors.HexColor("#9ca3af")
                )
            ])

        tabla.setStyle(TableStyle(estilos_tabla))
        contenido.append(tabla)

        documento.build(contenido)
        buffer.seek(0)

        return dcc.send_bytes(
            buffer.getvalue(),
            "analisis_ventas.pdf"
        )
