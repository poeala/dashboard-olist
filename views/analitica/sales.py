# Vista analítica de ventas con agrupaciones configurables
from dash import html, dcc, dash_table


def crear_vista_analitica_ventas():
    dimensiones = [
        {"label": "Año", "value": "anio"},
        {"label": "Trimestre", "value": "trimestre"},
        {"label": "Mes", "value": "mes"},
        {"label": "Fecha", "value": "fecha"},
        {"label": "Categoría de producto", "value": "categoria"},
        {"label": "Vendedor", "value": "vendedor"},
        {"label": "Estado del pedido", "value": "estado"}
    ]

    metricas = [
        {"label": "Facturación", "value": "facturacion"},
        {"label": "Cantidad de artículos", "value": "articulos"},
        {"label": "Pedidos únicos", "value": "pedidos"},
        {"label": "Compradores únicos", "value": "compradores"}
    ]

    return html.Div(
        [
            dcc.Download(id="descargar_analitica_pdf"),

            # Estado de apertura del detalle.
            dcc.Store(
                id="estado_detalle_analitica",
                data=False
            ),

            # Encabezado y filtros generales.
            html.Div(
                [
                    html.Div(
                        [
                            html.H2(
                                "Análisis de ventas",
                                style={
                                    "margin": "0 0 4px 0",
                                    "fontSize": "23px"
                                }
                            ),
                            html.P(
                                "Explorá las ventas mediante distintas dimensiones, agrupaciones y métricas.",
                                style={
                                    "margin": "0",
                                    "fontSize": "12px",
                                    "color": "#666"
                                }
                            )
                        ],
                        style={
                            "flex": "1",
                            "minWidth": "220px"
                        }
                    ),

                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Agrupar por",
                                        style={
                                            "fontSize": "12px",
                                            "fontWeight": "600"
                                        }
                                    ),
                                    dcc.Dropdown(
                                        id="analitica_dimension",
                                        options=dimensiones,
                                        value="anio",
                                        clearable=False
                                    )
                                ],
                                style={
                                    "flex": "1",
                                    "minWidth": "150px"
                                }
                            ),

                            html.Div(
                                [
                                    html.Label(
                                        "Agrupación secundaria",
                                        style={
                                            "fontSize": "12px",
                                            "fontWeight": "600"
                                        }
                                    ),
                                    dcc.Dropdown(
                                        id="analitica_dimension_secundaria",
                                        options=[
                                            {
                                                "label": "Ninguna",
                                                "value": "__ninguna__"
                                            }
                                        ] + dimensiones,
                                        value="__ninguna__",
                                        clearable=False
                                    )
                                ],
                                style={
                                    "flex": "1",
                                    "minWidth": "170px"
                                }
                            ),

                            html.Div(
                                [
                                    html.Label(
                                        "Año",
                                        style={
                                            "fontSize": "12px",
                                            "fontWeight": "600"
                                        }
                                    ),
                                    dcc.Dropdown(
                                        id="analitica_anio",
                                        options=[
                                            {
                                                "label": "Todos",
                                                "value": "__todos__"
                                            }
                                        ],
                                        value="__todos__",
                                        clearable=False
                                    )
                                ],
                                style={
                                    "flex": "1",
                                    "minWidth": "100px"
                                }
                            ),

                            html.Div(
                                [
                                    html.Label(
                                        "Estado del pedido",
                                        style={
                                            "fontSize": "12px",
                                            "fontWeight": "600"
                                        }
                                    ),
                                    dcc.Dropdown(
                                        id="analitica_estado",
                                        options=[
                                            {
                                                "label": "Todos",
                                                "value": "__todos__"
                                            }
                                        ],
                                        value="__todos__",
                                        clearable=False
                                    )
                                ],
                                style={
                                    "flex": "1",
                                    "minWidth": "145px"
                                }
                            )
                        ],
                        style={
                            "display": "flex",
                            "gap": "10px",
                            "flexWrap": "wrap",
                            "flex": "2",
                            "minWidth": "300px"
                        }
                    )
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "gap": "24px",
                    "flexWrap": "wrap",
                    "marginBottom": "18px"
                }
            ),

            # Selector de métricas.
            html.Div(
                [
                    html.Label("Métricas"),
                    dcc.Checklist(
                        id="analitica_metricas",
                        options=metricas,
                        value=["facturacion"],
                        inline=True,
                        style={
                            "display": "flex",
                            "gap": "18px",
                            "flexWrap": "wrap"
                        }
                    )
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "marginBottom": "14px"
                }
            ),

            # Resultados agrupados.
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(
                                "Resultados del análisis",
                                style={
                                    "margin": "0",
                                    "fontSize": "16px"
                                }
                            ),
                            html.Button(
                                "Exportar a PDF",
                                id="btn_exportar_analitica_pdf",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "#003D7C",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "6px",
                                    "padding": "9px 14px",
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "cursor": "pointer"
                                }
                            )
                        ],
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "gap": "12px",
                            "flexWrap": "wrap",
                            "marginBottom": "12px"
                        }
                    ),

                    # Filtros de las dimensiones.
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Filtrar dimensión principal",
                                        id="label_filtro_dimension",
                                        style={
                                            "fontSize": "12px",
                                            "fontWeight": "600",
                                            "display": "block",
                                            "marginBottom": "5px"
                                        }
                                    ),
                                    dcc.Input(
                                        id="filtro_dimension",
                                        type="text",
                                        value="",
                                        placeholder="Buscar texto o número...",
                                        debounce=True,
                                        style={
                                            "width": "100%",
                                            "padding": "8px",
                                            "boxSizing": "border-box",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px"
                                        }
                                    )
                                ],
                                style={
                                    "flex": "1",
                                    "minWidth": "180px"
                                }
                            ),

                            html.Div(
                                [
                                    html.Label(
                                        "Filtrar dimensión secundaria",
                                        id="label_filtro_secundaria",
                                        style={
                                            "fontSize": "12px",
                                            "fontWeight": "600",
                                            "display": "block",
                                            "marginBottom": "5px"
                                        }
                                    ),
                                    dcc.Input(
                                        id="filtro_secundaria",
                                        type="text",
                                        value="",
                                        placeholder="Buscar texto o número...",
                                        debounce=True,
                                        style={
                                            "width": "100%",
                                            "padding": "8px",
                                            "boxSizing": "border-box",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px"
                                        }
                                    )
                                ],
                                id="contenedor_filtro_secundaria",
                                style={
                                    "flex": "1",
                                    "minWidth": "180px",
                                    "display": "none"
                                }
                            ),

                            html.Button(
                                "Limpiar filtros",
                                id="btn_limpiar_filtros",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "#f0f2f5",
                                    "color": "#333",
                                    "border": "1px solid #ccc",
                                    "borderRadius": "6px",
                                    "padding": "9px 14px",
                                    "fontSize": "12px",
                                    "cursor": "pointer"
                                }
                            )
                        ],
                        style={
                            "display": "flex",
                            "gap": "12px",
                            "alignItems": "end",
                            "flexWrap": "wrap",
                            "marginBottom": "12px"
                        }
                    ),

                    html.P(
                        "Hacé clic en una fila para seleccionarla y después "
                        "usá el botón para mostrar sus registros de origen.",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "0 0 10px 0"
                        }
                    ),

                    dash_table.DataTable(
                        id="tabla_analitica_ventas",
                        columns=[],
                        data=[],
                        page_size=15,
                        sort_action="native",
                        filter_action="none",

                        # La selección se realiza haciendo clic en una celda.
                        # No se muestra una columna de checkboxes.
                        active_cell=None,

                        style_table={"overflowX": "auto"},
                        style_cell={
                            "padding": "9px",
                            "textAlign": "left",
                            "fontFamily": "Arial",
                            "fontSize": "13px",
                            "minWidth": "100px",
                            "width": "150px",
                            "maxWidth": "280px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "textAlign": "left"
                        },
                        style_cell_conditional=[
                            {
                                "if": {"column_type": "text"},
                                "width": "220px",
                                "minWidth": "220px",
                                "maxWidth": "220px"
                            },
                            {
                                "if": {"column_type": "numeric"},
                                "width": "150px",
                                "minWidth": "150px",
                                "maxWidth": "150px"
                            }
                        ],
                        style_data_conditional=[
                            {
                                "if": {"state": "active"},
                                "backgroundColor": "#e8f1fb",
                                "border": "1px solid #8bb8e8"
                            }
                        ]
                    ),

                    html.Div(
                        [
                            html.Button(
                                "Mostrar detalle",
                                id="btn_deseleccionar_analitica",
                                n_clicks=0,
                                disabled=True,
                                style={
                                    "backgroundColor": "#003D7C",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "6px",
                                    "padding": "9px 14px",
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "cursor": "pointer"
                                }
                            )
                        ],
                        style={
                            "marginTop": "10px",
                            "textAlign": "right"
                        }
                    )
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "marginBottom": "14px",
                    "boxShadow": "0 1px 5px #dddddd"
                }
            ),

            # Detalle de los registros que componen una agrupación.
            html.Div(
                [
                    html.H3(
                        "Registros de origen",
                        style={
                            "margin": "0 0 8px 0",
                            "fontSize": "16px"
                        }
                    ),

                    html.P(
                        "Seleccioná una fila de la tabla anterior para ver "
                        "los artículos que componen el resultado.",
                        id="texto_detalle_analitica_ventas",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "0 0 12px 0"
                        }
                    ),

                    dash_table.DataTable(
                        id="tabla_detalle_analitica_ventas",
                        columns=[],
                        data=[],
                        page_size=10,
                        page_action="native",
                        sort_action="native",
                        filter_action="none",
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "padding": "8px",
                            "textAlign": "left",
                            "fontFamily": "Arial",
                            "fontSize": "12px",
                            "minWidth": "100px",
                            "width": "140px",
                            "maxWidth": "240px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "textAlign": "left"
                        }
                    )
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "marginBottom": "14px",
                    "boxShadow": "0 1px 5px #dddddd"
                }
            ),

            # Gráfico.
            html.Div(
                [
                    dcc.Graph(
                        id="grafico_analitica_ventas",
                        config={"displayModeBar": False},
                        style={"height": "350px"}
                    )
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "boxShadow": "0 1px 5px #dddddd"
                }
            )
        ],
        style={
            "fontFamily": "Arial",
            "padding": "14px 20px",
            "boxSizing": "border-box"
        }
    )