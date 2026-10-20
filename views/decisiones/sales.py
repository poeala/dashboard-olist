
# Vista de toma de decisiones de ventas
from dash import html, dcc, dash_table


def crear_vista_decisiones_ventas():

    def tarjeta(titulo, componente_id):
        return html.Div(
            [
                html.P(
                    titulo,
                    style={
                        "fontSize": "12px",
                        "color": "#666",
                        "margin": "0 0 8px 0"
                    }
                ),
                html.H3(
                    "0",
                    id=componente_id,
                    style={
                        "fontSize": "25px",
                        "margin": "0"
                    }
                )
            ],
            style={
                "backgroundColor": "white",
                "padding": "16px",
                "borderRadius": "8px",
                "boxShadow": "0 1px 5px #dddddd",
                "flex": "1",
                "minWidth": "180px"
            }
        )

    def selector(titulo, componente_id):
        return html.Div(
            [
                html.Label(
                    titulo,
                    style={
                        "fontSize": "12px",
                        "color": "#666",
                        "display": "block",
                        "marginBottom": "5px"
                    }
                ),
                dcc.Dropdown(
                    id=componente_id,
                    options=[],
                    value="__todos__",
                    clearable=False,
                    searchable=False
                )
            ],
            style={
                "flex": "1",
                "minWidth": "130px"
            }
        )

    return html.Div(
        [
            # Encabezado con filtros a la derecha.
            html.Div(
                [
                    html.Div(
                        [
                            html.H2(
                                "Inteligencia comercial",
                                style={
                                    "margin": "0 0 4px 0",
                                    "fontSize": "23px"
                                }
                            ),
                            html.P(
                                "Identificar tendencias, desvíos y oportunidades para orientar las decisiones del negocio.",
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
                            selector("Año", "decisiones_filtro_anio"),
                            selector("Mes", "decisiones_filtro_mes")
                        ],
                        style={
                            "display": "flex",
                            "gap": "10px",
                            "flex": "1",
                            "minWidth": "280px",
                            "maxWidth": "440px"
                        }
                    )
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "gap": "20px",
                    "flexWrap": "wrap",
                    "marginBottom": "16px"
                }
            ),

            # Indicadores principales.
            html.Div(
                [
                    tarjeta(
                        "Hallazgos detectados",
                        "decisiones_total_alertas"
                    ),
                    tarjeta(
                        "Categorías con reseñas bajas",
                        "decisiones_categorias_resenas"
                    ),
                    tarjeta(
                        "Caídas de facturación",
                        "decisiones_caida_facturacion"
                    ),
                    tarjeta(
                        "Tasa de cancelación",
                        "decisiones_tasa_cancelacion"
                    )
                ],
                style={
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px"
                }
            ),

            # Gráficos: estados a la izquierda y categorías a la derecha.
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(
                                id="decisiones_grafico_facturacion",
                                config={"displayModeBar": False},
                                style={"height": "320px"}
                            )
                        ],
                        style={
                            "backgroundColor": "white",
                            "padding": "10px",
                            "borderRadius": "8px",
                            "boxShadow": "0 1px 5px #dddddd",
                            "flex": "1 1 400px",
                            "minWidth": "0"
                        }
                    ),
                    html.Div(
                        [
                            dcc.Graph(
                                id="decisiones_grafico_categorias",
                                config={"displayModeBar": False},
                                style={"height": "320px"}
                            )
                        ],
                        style={
                            "backgroundColor": "white",
                            "padding": "10px",
                            "borderRadius": "8px",
                            "boxShadow": "0 1px 5px #dddddd",
                            "flex": "1 1 400px",
                            "minWidth": "0"
                        }
                    )
                ],
                style={
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px"
                }
            ),

            # Tabla de hallazgos.
            html.Div(
                [
                    html.H3(
                        "Hallazgos",
                        style={
                            "fontSize": "16px",
                            "margin": "0 0 12px 0"
                        }
                    ),
                    html.P(
                        "La facturación es el valor de productos en R$, sin flete, "
                        "excluyendo cancelados y no disponibles. Las caídas comparan meses "
                        "consecutivos con datos. Cancelación usa todos los pedidos con artículos. "
                        "Las alertas señalan situaciones para investigar, no demuestran sus causas.",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "0 0 12px 0"
                        }
                    ),
                    dash_table.DataTable(
                        id="decisiones_tabla_hallazgos",
                        columns=[],
                        data=[],
                        page_size=10,
                        sort_action="native",
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "padding": "9px",
                            "textAlign": "left",
                            "fontFamily": "Arial",
                            "fontSize": "12px",
                            "minWidth": "120px",
                            "maxWidth": "300px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "textAlign": "left"
                        },
                        style_data_conditional=[
                            {
                                "if": {
                                    "filter_query": (
                                        '{Prioridad} = "Alta"'
                                    ),
                                    "column_id": "Prioridad"
                                },
                                "color": "#b91c1c",
                                "fontWeight": "bold"
                            },
                            {
                                "if": {
                                    "filter_query": (
                                        '{Prioridad} = "Media"'
                                    ),
                                    "column_id": "Prioridad"
                                },
                                "color": "#a16207",
                                "fontWeight": "bold"
                            }
                        ]
                    )
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "14px",
                    "borderRadius": "8px",
                    "boxShadow": "0 1px 5px #dddddd"
                }
            )
        ],
        style={
            "fontFamily": "Arial",
            "backgroundColor": "#f5f6fa",
            "padding": "14px 20px",
            "minHeight": "100vh",
            "boxSizing": "border-box"
        }
    )
