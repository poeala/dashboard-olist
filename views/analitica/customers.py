# Vista analítica de clientes
from dash import html, dcc, dash_table


def crear_vista_analitica_clientes():
    dimensiones = [
        {"label": "Segmento histórico", "value": "gold_segment"},
        {"label": "Año de última compra", "value": "anio_ultima_compra"},
        {
            "label": "Tipo de pago preferido",
            "value": "preferred_payment_type",
        },
    ]

    metricas = [
        {"label": "Cantidad de clientes", "value": "clientes"},
        {"label": "Total de pedidos", "value": "total_orders"},
        {"label": "Gasto total", "value": "total_spent"},
        {"label": "Calificación promedio", "value": "avg_review_score"},
    ]

    estilo_label = {
        "fontSize": "12px",
        "fontWeight": "600",
        "display": "block",
        "marginBottom": "5px",
    }

    estilo_control = {
        "flex": "1",
        "minWidth": "180px",
    }

    estilo_boton = {
        "backgroundColor": "#003D7C",
        "color": "white",
        "border": "none",
        "borderRadius": "6px",
        "padding": "9px 14px",
        "fontSize": "12px",
        "fontWeight": "600",
        "cursor": "pointer",
    }

    estilo_tarjeta = {
        "backgroundColor": "white",
        "padding": "12px",
        "borderRadius": "8px",
        "marginBottom": "14px",
        "boxShadow": "0 1px 5px #dddddd",
    }

    estilo_celda = {
        "padding": "9px",
        "textAlign": "left",
        "fontFamily": "Arial",
        "fontSize": "13px",
        "minWidth": "120px",
        "width": "160px",
        "maxWidth": "280px",
        "whiteSpace": "normal",
        "height": "auto",
    }

    columnas_variacion = [
        "Cantidad de clientes - Variación",
        "Cantidad de clientes - % variación",
        "Total de pedidos - Variación",
        "Total de pedidos - % variación",
        "Gasto total - Variación",
        "Gasto total - % variación",
        "Calificación promedio - Variación",
        "Calificación promedio - % variación",
    ]

    estilos_variacion = [
        {
            "if": {
                "column_id": columna,
                "filter_query": f"{{{columna}}} > 0",
            },
            "color": "#198754",
            "fontWeight": "600",
        }
        for columna in columnas_variacion
    ] + [
        {
            "if": {
                "column_id": columna,
                "filter_query": f"{{{columna}}} < 0",
            },
            "color": "#dc3545",
            "fontWeight": "600",
        }
        for columna in columnas_variacion
    ]

    # La dimensión principal cambia según la agrupación seleccionada.
    estilos_total = [
        {
            "if": {
                "filter_query": '{Segmento histórico} = "TOTAL"',
            },
            "backgroundColor": "#f0f2f5",
            "fontWeight": "bold",
            "borderTop": "2px solid #c7ccd4",
        },
        {
            "if": {
                "filter_query": '{Año de última compra} = "TOTAL"',
            },
            "backgroundColor": "#f0f2f5",
            "fontWeight": "bold",
            "borderTop": "2px solid #c7ccd4",
        },
        {
            "if": {
                "filter_query": '{Tipo de pago preferido} = "TOTAL"',
            },
            "backgroundColor": "#f0f2f5",
            "fontWeight": "bold",
            "borderTop": "2px solid #c7ccd4",
        },
    ]

    return html.Div(
        [
            dcc.Download(
                id="clientes_descargar_analitica_pdf"
            ),

            dcc.Store(
                id="clientes_estado_detalle_analitica",
                data=None,
            ),

            # Encabezado y agrupaciones
            html.Div(
                [
                    html.Div(
                        [
                            html.H2(
                                "Análisis de clientes",
                                style={
                                    "margin": "0 0 4px 0",
                                    "fontSize": "23px",
                                },
                            ),
                            html.P(
                                "Explorá segmentación, recurrencia, distribución del gasto "
                                "y relaciones entre variables.",
                                style={
                                    "margin": "0",
                                    "fontSize": "12px",
                                    "color": "#666",
                                },
                            ),
                        ],
                        style={
                            "flex": "1",
                            "minWidth": "220px",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Agrupar por",
                                        style=estilo_label,
                                    ),
                                    dcc.Dropdown(
                                        id="clientes_analitica_dimension",
                                        options=dimensiones,
                                        value="anio_ultima_compra",
                                        clearable=False,
                                    ),
                                ],
                                style=estilo_control,
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Agrupación secundaria",
                                        style=estilo_label,
                                    ),
                                    dcc.Dropdown(
                                        id="clientes_analitica_dimension_secundaria",
                                        options=[
                                            {
                                                "label": "Ninguna",
                                                "value": "__ninguna__",
                                            }
                                        ] + dimensiones,
                                        value="__ninguna__",
                                        clearable=False,
                                    ),
                                ],
                                style=estilo_control,
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "10px",
                            "flexWrap": "wrap",
                            "flex": "2",
                            "minWidth": "300px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "gap": "24px",
                    "flexWrap": "wrap",
                    "marginBottom": "18px",
                },
            ),

            # Indicadores
            html.Div(
                [
                    html.Label(
                        "Indicadores",
                        style=estilo_label,
                    ),
                    dcc.Checklist(
                        id="clientes_analitica_metricas",
                        options=metricas,
                        value=["clientes"],
                        inline=True,
                        style={
                            "display": "flex",
                            "gap": "18px",
                            "flexWrap": "wrap",
                        },
                    ),
                ],
                style={
                    **estilo_tarjeta,
                    "boxShadow": "none",
                },
            ),

            # Tabla de resultados
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(
                                "Resultados del análisis",
                                style={
                                    "margin": "0",
                                    "fontSize": "16px",
                                },
                            ),
                            html.Button(
                                "Exportar a PDF",
                                id="clientes_btn_exportar_analitica_pdf",
                                n_clicks=0,
                                style=estilo_boton,
                            ),
                        ],
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "gap": "12px",
                            "flexWrap": "wrap",
                            "marginBottom": "12px",
                        },
                    ),

                    # Filtros independientes por dimensión.
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Buscar en la agrupación principal",
                                        style=estilo_label,
                                    ),
                                    dcc.Input(
                                        id="clientes_filtro_dimension",
                                        type="text",
                                        value="",
                                        placeholder="Buscar en la agrupación principal...",
                                        debounce=True,
                                        style={
                                            "width": "100%",
                                            "padding": "8px",
                                            "boxSizing": "border-box",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                        },
                                    ),
                                ],
                                style={
                                    "flex": "1",
                                    "minWidth": "220px",
                                },
                            ),

                            html.Div(
                                [
                                    html.Label(
                                        "Buscar en la agrupación secundaria",
                                        style=estilo_label,
                                    ),
                                    dcc.Input(
                                        id="clientes_filtro_dimension_secundaria",
                                        type="text",
                                        value="",
                                        placeholder="Buscar en la agrupación secundaria...",
                                        debounce=True,
                                        style={
                                            "width": "100%",
                                            "padding": "8px",
                                            "boxSizing": "border-box",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                        },
                                    ),
                                ],
                                id="clientes_contenedor_filtro_secundario",
                                style={"display": "none"},
                            ),

                            html.Button(
                                "Limpiar filtros",
                                id="clientes_btn_limpiar_filtros",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "#f0f2f5",
                                    "color": "#333",
                                    "border": "1px solid #ccc",
                                    "borderRadius": "6px",
                                    "padding": "9px 14px",
                                    "fontSize": "12px",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "12px",
                            "alignItems": "end",
                            "flexWrap": "wrap",
                            "marginBottom": "12px",
                        },
                    ),

                    html.P(
                        "Seleccioná una celda de la fila y pulsá Mostrar detalle.",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "0 0 10px 0",
                        },
                    ),

                    dash_table.DataTable(
                        id="clientes_tabla_analitica",
                        columns=[],
                        data=[],
                        page_size=15,
                        sort_action="custom",
                        sort_mode="multi",
                        filter_action="none",
                        active_cell=None,
                        style_table={
                            "overflowX": "auto",
                        },
                        style_cell=estilo_celda,
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "textAlign": "left",
                        },
                        style_data_conditional=[
                            {
                                "if": {"state": "active"},
                                "backgroundColor": "#e8f1fb",
                                "border": "1px solid #8bb8e8",
                            },
                        ] + estilos_variacion + estilos_total,
                    ),

                    html.Div(
                        [
                            html.Button(
                                "Mostrar detalle",
                                id="clientes_btn_detalle_analitica",
                                n_clicks=0,
                                disabled=True,
                                style={
                                    **estilo_boton,
                                    "backgroundColor": "#d1d5db",
                                    "color": "#6b7280",
                                    "cursor": "not-allowed",
                                },
                            ),
                        ],
                        style={
                            "marginTop": "10px",
                            "textAlign": "right",
                        },
                    ),
                ],
                style=estilo_tarjeta,
            ),

            # Detalle del grupo seleccionado
            html.Div(
                [
                    html.H3(
                        "Detalle de clientes",
                        style={
                            "margin": "0 0 8px 0",
                            "fontSize": "16px",
                        },
                    ),
                    html.P(
                        "Seleccioná un grupo y pulsá Mostrar detalle.",
                        id="clientes_texto_detalle_analitica",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "0 0 12px 0",
                        },
                    ),
                    dash_table.DataTable(
                        id="clientes_tabla_detalle_analitica",
                        columns=[],
                        data=[],
                        page_size=10,
                        page_action="native",
                        sort_action="native",
                        filter_action="none",
                        style_table={
                            "overflowX": "auto",
                        },
                        style_cell={
                            **estilo_celda,
                            "fontSize": "12px",
                            "width": "140px",
                            "maxWidth": "240px",
                        },
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "textAlign": "left",
                        },
                    ),
                ],
                id="clientes_contenedor_detalle_analitica",
                style={
                    **estilo_tarjeta,
                    "display": "none",
                },
            ),

            html.H3("Patrones de comportamiento"),
            html.P(
                "Historial Gold de los clientes seleccionados por los filtros de la tabla. "
                "El año corresponde a la última compra, no al período del gasto. "
                "Recurrencia: al menos dos pedidos entre clientes con pedidos válidos. "
                "Cada burbuja agrupa clientes del mismo segmento y frecuencia; "
                "su tamaño indica cantidad de clientes y su altura, gasto promedio. "
                "Las relaciones son descriptivas y no prueban causalidad.",
                className="business-note",
            ),
            dcc.Loading(html.Div(id="clientes_patrones_analitica"), type="circle"),

            # Gráfico
            html.Div(
                [
                    dcc.Graph(
                        id="clientes_grafico_analitica",
                        config={"displayModeBar": False},
                        style={"height": "350px"},
                    ),
                ],
                style=estilo_tarjeta,
            ),
        ],
        style={
            "fontFamily": "Arial",
            "padding": "14px 20px",
            "boxSizing": "border-box",
        },
    )