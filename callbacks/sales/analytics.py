# Callbacks para el análisis de ventas

from io import BytesIO
from html import escape

import pandas as pd
import plotly.express as px

from dash import Input, Output, State, dcc, ctx, no_update

from data.sales import (
    consultar_ventas_agrupadas,
    consultar_detalle_ventas_agrupadas,
)
from data.definitions import ventas_validas


def registrar_callbacks_analitica_ventas(app, df):

    nombres_metricas = {
        "facturacion": "Facturación",
        "articulos": "Cantidad de artículos",
        "pedidos": "Pedidos únicos",
        "compradores": "Compradores únicos",
    }

    nombres_dimensiones = {
        "anio": "Año",
        "trimestre": "Trimestre",
        "mes": "Mes",
        "fecha": "Fecha",
        "categoria": "Categoría",
        "vendedor": "Vendedor",
        "estado": "Estado",
    }

    anios = sorted(
        pd.to_numeric(df["anio"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
    )

    opciones_anio = [
        {"label": "Todos", "value": "__todos__"}
    ] + [
        {"label": str(anio), "value": int(anio)}
        for anio in anios
    ]

    opciones_estado = [
        {"label": "Todos", "value": "__todos__"},
        {"label": "Entregado", "value": "__entregado__"},
        {"label": "En proceso", "value": "__en_proceso__"},
    ]

    mensaje_inicial = (
        "Seleccioná una fila y pulsá Mostrar detalle para consultar "
        "los artículos que componen el resultado."
    )

    # ---------------------------------------------------------
    # Opciones de los filtros generales
    # ---------------------------------------------------------

    @app.callback(
        Output("analitica_anio", "options"),
        Output("analitica_estado", "options"),
        Input("selector_vista", "value"),
    )
    def cargar_opciones_filtros(vista):
        return opciones_anio, opciones_estado

    # ---------------------------------------------------------
    # Limpiar los filtros de dimensión cuando cambia la
    # agrupación principal/secundaria o se pulsa Limpiar filtros
    # ---------------------------------------------------------

    @app.callback(
        Output("label_filtro_dimension", "children"),
        Output("label_filtro_secundaria", "children"),
        Output("contenedor_filtro_secundaria", "style"),
        Output("filtro_dimension", "value"),
        Output("filtro_secundaria", "value"),
        Input("analitica_dimension", "value"),
        Input("analitica_dimension_secundaria", "value"),
        Input("btn_limpiar_filtros", "n_clicks"),
    )
    def actualizar_filtros_dimension(
        dimension,
        secundaria,
        n_clicks,
    ):
        nombre_principal = nombres_dimensiones.get(
            dimension,
            "Dimensión principal",
        )

        secundaria_activa = (
            secundaria is not None
            and secundaria != "__ninguna__"
            and secundaria != dimension
        )

        nombre_secundaria = nombres_dimensiones.get(
            secundaria,
            "Dimensión secundaria",
        )

        estilo_secundaria = {
            "flex": "1",
            "minWidth": "180px",
            "display": "block" if secundaria_activa else "none",
        }

        return (
            f"Filtrar por {nombre_principal}",
            f"Filtrar por {nombre_secundaria}",
            estilo_secundaria,
            "",
            "",
        )

    # ---------------------------------------------------------
    # Limpiar la celda seleccionada cuando cambian los datos
    # del análisis. Así evitamos usar una selección anterior.
    # ---------------------------------------------------------

    @app.callback(
        Output("tabla_analitica_ventas", "active_cell"),
        Input("analitica_dimension", "value"),
        Input("analitica_dimension_secundaria", "value"),
        Input("analitica_anio", "value"),
        Input("analitica_estado", "value"),
        Input("analitica_metricas", "value"),
        Input("filtro_dimension", "value"),
        Input("filtro_secundaria", "value"),
        prevent_initial_call=True,
    )
    def limpiar_seleccion_analitica(
        dimension,
        secundaria,
        anio,
        estado,
        metricas,
        filtro_dimension,
        filtro_secundaria,
    ):
        return None

    # ---------------------------------------------------------
    # Totales para la fila TOTAL
    # ---------------------------------------------------------

    def calcular_totales(anio, estado, metricas):
        df_filtrado = df.copy()

        if anio is not None:
            df_filtrado = df_filtrado[
                pd.to_numeric(
                    df_filtrado["anio"],
                    errors="coerce",
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
            df_filtrado = df_filtrado[estados == "delivered"]

        elif estado == "__en_proceso__":
            df_filtrado = df_filtrado[
                ~estados.isin(
                    ["delivered", "canceled", "unavailable"]
                )
            ]

        else:
            df_filtrado = ventas_validas(df_filtrado)

        totales = {}

        if "facturacion" in metricas:
            totales["Facturación"] = pd.to_numeric(
                df_filtrado["price"],
                errors="coerce",
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

    # ---------------------------------------------------------
    # Actualizar tabla y gráfico
    # ---------------------------------------------------------

    @app.callback(
        Output("tabla_analitica_ventas", "columns"),
        Output("tabla_analitica_ventas", "data"),
        Output(
            "tabla_analitica_ventas",
            "style_data_conditional",
        ),
        Output("grafico_analitica_ventas", "figure"),
        Input("analitica_dimension", "value"),
        Input("analitica_dimension_secundaria", "value"),
        Input("analitica_anio", "value"),
        Input("analitica_estado", "value"),
        Input("analitica_metricas", "value"),
        Input("filtro_dimension", "value"),
        Input("filtro_secundaria", "value"),
    )
    def actualizar_analisis(
        dimension,
        secundaria,
        anio,
        estado,
        metricas,
        filtro_dimension,
        filtro_secundaria,
    ):
        if not metricas:
            figura = px.bar(
                title="Seleccioná al menos una métrica"
            )
            figura.update_layout(template="plotly_white")

            return [], [], [], figura

        secundaria = (
            None
            if secundaria == "__ninguna__"
            else secundaria
        )

        if secundaria == dimension:
            secundaria = None

        anio = None if anio == "__todos__" else anio

        # Consultar resultados agrupados.
        df_analisis = consultar_ventas_agrupadas(
            dimension=dimension,
            dimension_secundaria=secundaria,
            metricas=metricas,
            anio=anio,
            estado=estado,
        )

        nombre_dimension = nombres_dimensiones[dimension]

        hay_doble_agrupacion = (
            secundaria is not None
            and secundaria != dimension
        )

        nombre_dimension_secundaria = (
            nombres_dimensiones[secundaria]
            if hay_doble_agrupacion
            else None
        )

        # Calcular variaciones para dimensiones temporales.
        calcular_variacion = (
            dimension in ("mes", "anio")
            or (
                dimension == "trimestre"
                and anio is not None
            )
        )

        if calcular_variacion and not df_analisis.empty:
            columnas_orden = (
                [
                    nombre_dimension_secundaria,
                    nombre_dimension,
                ]
                if hay_doble_agrupacion
                else [nombre_dimension]
            )

            df_analisis = df_analisis.sort_values(
                columnas_orden
            ).copy()

            for metrica in metricas:
                nombre = nombres_metricas[metrica]

                if hay_doble_agrupacion:
                    anterior = df_analisis.groupby(
                        nombre_dimension_secundaria,
                        dropna=False,
                    )[nombre].shift(1)
                else:
                    anterior = df_analisis[nombre].shift(1)

                diferencia = df_analisis[nombre] - anterior

                porcentaje = (
                    diferencia / anterior.where(anterior != 0)
                ) * 100

                df_analisis[f"Variación {nombre}"] = (
                    diferencia.round(2)
                )

                df_analisis[f"% variación {nombre}"] = (
                    porcentaje.round(2)
                )

            df_analisis = df_analisis.sort_values(
                (
                    [nombre_dimension, nombre_dimension_secundaria]
                    if hay_doble_agrupacion
                    else [nombre_dimension]
                )
            )

        # Agregar la fila TOTAL.
        totales = calcular_totales(
            anio,
            estado,
            metricas,
        )

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
                pd.DataFrame([fila_total]),
            ],
            ignore_index=True,
        )

        # Crear los datos del gráfico antes de aplicar los filtros
        # de texto de la tabla.
        datos_grafico = df_analisis[
            df_analisis[nombre_dimension] != "TOTAL"
        ].copy()

        nombre_metrica = nombres_metricas[metricas[0]]

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
                    nombre_dimension_secundaria,
                ],
            )

        else:
            if dimension in ("anio", "trimestre", "mes", "fecha"):
                datos_grafico = datos_grafico.sort_values(
                    nombre_dimension,
                    ascending=True,
                )
            else:
                datos_grafico = datos_grafico.sort_values(
                    nombre_metrica,
                    ascending=True,
                ).tail(20)

            figura = px.bar(
                datos_grafico,
                x=nombre_dimension,
                y=nombre_metrica,
                title=nombre_metrica,
                hover_data=[nombre_dimension],
            )

        figura.update_layout(
            template="plotly_white",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
            xaxis_title=nombre_dimension,
            yaxis_title=nombre_metrica,
        )

        figura.update_xaxes(type="category")

        # Aplicar filtros solamente sobre las dimensiones de la tabla.
        df_tabla = df_analisis.copy()

        if filtro_dimension and str(filtro_dimension).strip():
            busqueda = str(filtro_dimension).strip()

            coincidencias = (
                df_tabla[nombre_dimension]
                .astype(str)
                .str.contains(
                    busqueda,
                    case=False,
                    na=False,
                    regex=False,
                )
            )

            df_tabla = df_tabla[
                coincidencias
                | (df_tabla[nombre_dimension].astype(str) == "TOTAL")
            ]

        if (
            hay_doble_agrupacion
            and filtro_secundaria
            and str(filtro_secundaria).strip()
        ):
            busqueda = str(filtro_secundaria).strip()

            coincidencias = (
                df_tabla[nombre_dimension_secundaria]
                .astype(str)
                .str.contains(
                    busqueda,
                    case=False,
                    na=False,
                    regex=False,
                )
            )

            df_tabla = df_tabla[
                coincidencias
                | (df_tabla[nombre_dimension].astype(str) == "TOTAL")
            ]

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
                ),
            }
            for columna in df_analisis.columns
        ]

        datos = df_tabla.round(2).to_dict("records")

        # Asignar un ID estable para identificar la fila activa,
        # incluso cuando la tabla se ordena o cambia de página.
        for indice, registro in enumerate(datos):
            registro["id"] = str(indice)

        # Resaltar TOTAL y colorear variaciones.
        estilos = [
            {
                "if": {
                    "filter_query": (
                        "{" + nombre_dimension + '} = "TOTAL"'
                    )
                },
                "fontWeight": "bold",
                "backgroundColor": "#f0f2f5",
                "borderTop": "2px solid #9ca3af",
            }
        ]

        for columna in df_analisis.columns:
            if (
                columna.startswith("Variación ")
                or columna.startswith("% variación ")
            ):
                estilos.extend(
                    [
                        {
                            "if": {
                                "filter_query": f"{{{columna}}} > 0",
                                "column_id": columna,
                            },
                            "color": "green",
                            "fontWeight": "bold",
                        },
                        {
                            "if": {
                                "filter_query": f"{{{columna}}} < 0",
                                "column_id": columna,
                            },
                            "color": "red",
                            "fontWeight": "bold",
                        },
                    ]
                )

        return columnas, datos, estilos, figura
    
    
    # ---------------------------------------------------------
    # Habilitar el botón solo cuando haya una fila válida
    # seleccionada (distinta de TOTAL).
    # ---------------------------------------------------------

    @app.callback(
        Output("btn_deseleccionar_analitica", "disabled"),
        Output("btn_deseleccionar_analitica", "style"),
        Input("tabla_analitica_ventas", "active_cell"),
        State("tabla_analitica_ventas", "data"),
        State("analitica_dimension", "value"),
        prevent_initial_call=False,
    )
    def actualizar_estado_boton_detalle(
        active_cell,
        filas_tabla,
        dimension,
    ):
        estilo_base = {
            "backgroundColor": "#003D7C",
            "color": "white",
            "border": "none",
            "borderRadius": "6px",
            "padding": "9px 14px",
            "fontSize": "12px",
            "fontWeight": "600",
            "cursor": "pointer",
        }

        estilo_deshabilitado = {
            **estilo_base,
            "backgroundColor": "#d1d5db",
            "color": "#6b7280",
            "cursor": "not-allowed",
        }

        deshabilitado = True

        if active_cell is not None and filas_tabla:
            id_fila = active_cell.get("row_id")

            registro = next(
                (
                    fila
                    for fila in filas_tabla
                    if id_fila is not None
                    and str(fila.get("id")) == str(id_fila)
                ),
                None,
            )

            if registro is None:
                indice = active_cell.get("row")

                if indice is not None and 0 <= indice < len(filas_tabla):
                    registro = filas_tabla[indice]

            if registro is not None:
                nombre_dimension = nombres_dimensiones.get(dimension)

                if registro.get(nombre_dimension) != "TOTAL":
                    deshabilitado = False

        estilo = (
            estilo_deshabilitado
            if deshabilitado
            else estilo_base
        )

        return deshabilitado, estilo

    # ---------------------------------------------------------
    # Exportar tabla a PDF
    # ---------------------------------------------------------

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
        prevent_initial_call=True,
    )
    def exportar_analisis_pdf(
        n_clicks,
        columnas,
        datos,
        dimension,
        secundaria,
        anio,
        estado,
        metricas,
    ):
        if not n_clicks or not columnas:
            return None

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle,
        )
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = BytesIO()

        documento = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
        )

        estilos_pdf = getSampleStyleSheet()

        estilo_celda = ParagraphStyle(
            "Celda",
            parent=estilos_pdf["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            alignment=TA_LEFT,
            wordWrap="CJK",
        )

        estilo_encabezado = ParagraphStyle(
            "EncabezadoTabla",
            parent=estilo_celda,
            fontName="Helvetica-Bold",
        )

        contenido = [
            Paragraph("Análisis de ventas", estilos_pdf["Title"]),
            Spacer(1, 3 * mm),
        ]

        anio_texto = (
            "Todos"
            if anio == "__todos__"
            else str(anio)
        )

        estado_texto = {
            "__todos__": "Todos",
            "__entregado__": "Entregado",
            "__en_proceso__": "En proceso",
        }.get(estado, str(estado))

        secundaria_texto = (
            "Ninguna"
            if secundaria == "__ninguna__"
            else nombres_dimensiones.get(
                secundaria,
                str(secundaria),
            )
        )

        metricas_texto = ", ".join(
            nombres_metricas.get(m, m)
            for m in (metricas or [])
        )

        filtros_texto = (
            f"<b>Agrupación:</b> "
            f"{escape(nombres_dimensiones.get(dimension, str(dimension)))}"
            f"&nbsp;&nbsp; <b>Secundaria:</b> {escape(secundaria_texto)}"
            f"&nbsp;&nbsp; <b>Año:</b> {escape(anio_texto)}"
            f"<br/><b>Estado:</b> {escape(estado_texto)}"
            f"&nbsp;&nbsp; <b>Métricas:</b> {escape(metricas_texto)}"
        )

        contenido.extend(
            [
                Paragraph(filtros_texto, estilos_pdf["Normal"]),
                Spacer(1, 5 * mm),
            ]
        )

        encabezados = [
            Paragraph(escape(str(col["name"])), estilo_encabezado)
            for col in columnas
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

            if registro.get(
                nombres_dimensiones[dimension]
            ) == "TOTAL":
                fila_total_pdf = indice

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
            hAlign="LEFT",
        )

        estilos_tabla = [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#f0f2f5"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.35,
                colors.HexColor("#d1d5db"),
            ),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]

        if fila_total_pdf is not None:
            estilos_tabla.extend(
                [
                    (
                        "BACKGROUND",
                        (0, fila_total_pdf),
                        (-1, fila_total_pdf),
                        colors.HexColor("#e5e7eb"),
                    ),
                    (
                        "FONTNAME",
                        (0, fila_total_pdf),
                        (-1, fila_total_pdf),
                        "Helvetica-Bold",
                    ),
                    (
                        "LINEABOVE",
                        (0, fila_total_pdf),
                        (-1, fila_total_pdf),
                        1,
                        colors.HexColor("#9ca3af"),
                    ),
                ]
            )

        tabla.setStyle(TableStyle(estilos_tabla))
        contenido.append(tabla)

        documento.build(contenido)
        buffer.seek(0)

        return dcc.send_bytes(
            buffer.getvalue(),
            "analisis_ventas.pdf",
        )

    # ---------------------------------------------------------
    # Seleccionar una fila y abrir/cerrar el detalle mediante
    # el botón Mostrar detalle / Cerrar detalle.
    # ---------------------------------------------------------

    @app.callback(
        Output("estado_detalle_analitica", "data"),
        Output("btn_deseleccionar_analitica", "children"),
        Output("btn_deseleccionar_analitica", "disabled"),
        Output("tabla_detalle_analitica_ventas", "columns"),
        Output("tabla_detalle_analitica_ventas", "data"),
        Output("texto_detalle_analitica_ventas", "children"),
        Input("tabla_analitica_ventas", "active_cell"),
        Input("btn_deseleccionar_analitica", "n_clicks"),
        Input("analitica_dimension", "value"),
        Input("analitica_dimension_secundaria", "value"),
        Input("analitica_anio", "value"),
        Input("analitica_estado", "value"),
        Input("analitica_metricas", "value"),
        Input("filtro_dimension", "value"),
        Input("filtro_secundaria", "value"),
        State("estado_detalle_analitica", "data"),
        State("tabla_analitica_ventas", "data"),
        prevent_initial_call=False,
    )
    def alternar_detalle_analitico(
        active_cell,
        n_clicks,
        dimension,
        secundaria,
        anio,
        estado,
        metricas,
        filtro_dimension,
        filtro_secundaria,
        detalle_abierto,
        filas_tabla,
    ):
        detalle_abierto = bool(detalle_abierto)

        # Si cambia la selección de fila, no abrir el detalle
        # automáticamente: el usuario debe pulsar el botón.
        if ctx.triggered_id == "tabla_analitica_ventas":
            return (
                False,
                "Mostrar detalle",
                active_cell is None,
                [],
                [],
                mensaje_inicial,
            )

        # Los cambios en agrupaciones o filtros cierran el detalle
        # anterior y limpian la selección mediante el callback aparte.
        if ctx.triggered_id in {
            "analitica_dimension",
            "analitica_dimension_secundaria",
            "analitica_anio",
            "analitica_estado",
            "analitica_metricas",
            "filtro_dimension",
            "filtro_secundaria",
        }:
            return (
                False,
                "Mostrar detalle",
                active_cell is None,
                [],
                [],
                mensaje_inicial,
            )

        # Si no hay celda seleccionada, no hay detalle para abrir.
        if active_cell is None:
            return (
                False,
                "Mostrar detalle",
                True,
                [],
                [],
                mensaje_inicial,
            )

        # Si el botón está cerrando un detalle abierto, limpiarlo.
        if (
            ctx.triggered_id == "btn_deseleccionar_analitica"
            and detalle_abierto
        ):
            return (
                False,
                "Mostrar detalle",
                False,
                [],
                [],
                "Detalle cerrado. Podés volver a abrirlo o seleccionar otra fila.",
            )

        # Abrir el detalle al pulsar el botón.
        if ctx.triggered_id == "btn_deseleccionar_analitica":
            if not filas_tabla:
                return (
                    False,
                    "Mostrar detalle",
                    True,
                    [],
                    [],
                    mensaje_inicial,
                )

            # Cada fila posee un ID estable, independiente del orden.
            id_fila = active_cell.get("row_id")

            registro = next(
                (
                    fila
                    for fila in filas_tabla
                    if id_fila is not None
                    and str(fila.get("id")) == str(id_fila)
                ),
                None,
            )

            # Compatibilidad por si la tabla no devuelve row_id.
            if registro is None:
                indice = active_cell.get("row")

                if (
                    indice is not None
                    and 0 <= indice < len(filas_tabla)
                ):
                    registro = filas_tabla[indice]

            if registro is None:
                return (
                    False,
                    "Mostrar detalle",
                    True,
                    [],
                    [],
                    "No se pudo identificar la fila. Seleccioná otra y probá nuevamente.",
                )

            nombre_dimension = nombres_dimensiones[dimension]

            if registro.get(nombre_dimension) == "TOTAL":
                return (
                    True,
                    "Cerrar detalle",
                    False,
                    [],
                    [],
                    "La fila TOTAL resume el análisis completo y no corresponde a un único grupo de registros.",
                )

            secundaria = (
                None
                if secundaria == "__ninguna__"
                or secundaria == dimension
                else secundaria
            )

            anio_consulta = (
                None if anio == "__todos__" else anio
            )

            nombre_dimension_secundaria = (
                nombres_dimensiones[secundaria]
                if secundaria
                else None
            )

            valor_dimension = registro.get(nombre_dimension)

            valor_dimension_secundaria = (
                registro.get(nombre_dimension_secundaria)
                if nombre_dimension_secundaria
                else None
            )

            df_detalle = consultar_detalle_ventas_agrupadas(
                dimension=dimension,
                valor_dimension=valor_dimension,
                dimension_secundaria=secundaria,
                valor_dimension_secundaria=valor_dimension_secundaria,
                anio=anio_consulta,
                estado=estado,
                limite=5000,
            )

            if df_detalle.empty:
                return (
                    True,
                    "Cerrar detalle",
                    False,
                    [],
                    [],
                    "No se encontraron registros para esta agrupación.",
                )

            cantidad = len(df_detalle)

            if cantidad >= 5000:
                mensaje = (
                    "Se muestran hasta 5.000 artículos de esta agrupación. "
                    "Aplicá los filtros generales para acotar el resultado."
                )
            else:
                mensaje = (
                    f"Se encontraron {cantidad:,} artículos para esta agrupación."
                ).replace(",", ".")

            columnas_detalle = [
                {
                    "name": columna,
                    "id": columna,
                    "type": (
                        "numeric"
                        if pd.api.types.is_numeric_dtype(
                            df_detalle[columna]
                        )
                        else "text"
                    ),
                }
                for columna in df_detalle.columns
            ]

            datos_detalle = (
                df_detalle.round(2).to_dict("records")
            )

            return (
                True,
                "Cerrar detalle",
                False,
                columnas_detalle,
                datos_detalle,
                mensaje,
            )

        # En cualquier otro caso, dejar el detalle cerrado.
        return (
            False,
            "Mostrar detalle",
            active_cell is None,
            [],
            [],
            mensaje_inicial,
        )