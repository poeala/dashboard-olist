# Vista analítica de ventas con agrupaciones configurables
from dash import html, dcc, dash_table


def crear_vista_analitica_ventas():
    # Definir las dimensiones disponibles para agrupar.
    dimensiones = [
        {"label": "Año", "value": "anio"},
        {"label": "Trimestre", "value": "trimestre"},
        {"label": "Mes", "value": "mes"},
        {"label": "Fecha", "value": "fecha"},
        {"label": "Categoría de producto", "value": "categoria"},
        {"label": "Vendedor", "value": "vendedor"},
        {"label": "Estado del pedido", "value": "estado"}
    ]

    # Definir las métricas disponibles.
    metricas = [
        {"label": "Facturación", "value": "facturacion"},
        {"label": "Cantidad de artículos", "value": "articulos"},
        {"label": "Pedidos únicos", "value": "pedidos"},
        {"label": "Compradores únicos", "value": "compradores"}
    ]

    return html.Div(
        [
            # Componente para descargar el PDF.
            dcc.Download(id="descargar_analitica_pdf"),

            # Encabezado con título y filtros.
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

            # Tabla de resultados y botón de exportación.
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

                    dash_table.DataTable(
                        id="tabla_analitica_ventas",
                        columns=[],
                        data=[],
                        page_size=15,
                        sort_action="native",
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
                        ]
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

            # Gráfico de análisis.
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
