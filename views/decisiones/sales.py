# Vista de toma de decisiones de ventas
from dash import html, dcc, dash_table


def crear_vista_decisiones_ventas():

    def tarjeta(titulo, subtitulo, componente_id):
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
                ),
                html.P(
                    subtitulo,
                    style={
                        "fontSize": "11px",
                        "color": "#888",
                        "margin": "8px 0 0 0"
                    }
                )
            ],
            style={
                "backgroundColor": "white",
                "padding": "16px",
                "borderRadius": "8px",
                "boxShadow": "0 1px 5px #dddddd",
                "flex": "1 1 180px",
                "minWidth": "180px",
                "boxSizing": "border-box"
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

    estilo_panel = {
        "backgroundColor": "white",
        "padding": "14px",
        "borderRadius": "8px",
        "boxShadow": "0 1px 5px #dddddd",
        "boxSizing": "border-box"
    }

    return html.Div(
        [
            # Encabezado y filtros.
            html.Div(
                [
                    html.Div(
                        [
                            html.H2(
                                "Desempeño comercial",
                                style={
                                    "margin": "0 0 4px 0",
                                    "fontSize": "23px"
                                }
                            ),
                            html.P(
                                "Ventas, facturación y evolución comercial.",
                                style={
                                    "margin": "0",
                                    "fontSize": "12px",
                                    "color": "#666"
                                }
                            )
                        ],
                        style={
                            "flex": "1 1 280px",
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
                            "flex": "0 1 380px",
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
                        "Situaciones que requieren revisión.",
                        "decisiones_total_alertas"
                    ),
                    tarjeta(
                        "Categorías con reseñas bajas",
                        "Promedio de 3,5 puntos o menos sobre 5.",
                        "decisiones_categorias_resenas"
                    ),
                    tarjeta(
                        "Caídas de facturación",
                        "Meses con una disminución superior al 10 %.",
                        "decisiones_caida_facturacion"
                    ),
                    tarjeta(
                        "Tasa de cancelación",
                        "Porcentaje de pedidos cancelados o no disponibles.",
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

            # Gráficos.
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
                            **estilo_panel,
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
                            **estilo_panel,
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
                    html.Div(
                        [
                            html.H3(
                                "Hallazgos detectados",
                                style={
                                    "fontSize": "16px",
                                    "margin": "0 0 5px 0"
                                }
                            ),
                            html.P(
                                "Situaciones que cumplen las reglas de detección configuradas.",
                                style={
                                    "fontSize": "12px",
                                    "color": "#666",
                                    "margin": "0"
                                }
                            )
                        ],
                        style={"marginBottom": "12px"}
                    ),

                    dash_table.DataTable(
                        id="decisiones_tabla_hallazgos",
                        columns=[],
                        data=[],
                        page_size=10,
                        sort_action="native",
                        filter_action="native",
                        style_table={
                            "overflowX": "auto",
                            "minWidth": "100%"
                        },
                        style_cell={
                            "padding": "9px",
                            "textAlign": "left",
                            "fontFamily": "Arial",
                            "fontSize": "12px",
                            "minWidth": "120px",
                            "maxWidth": "320px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "textAlign": "left",
                            "whiteSpace": "normal"
                        },
                        style_data_conditional=[
                            {
                                "if": {
                                    "filter_query": '{Prioridad} = "Alta"',
                                    "column_id": "Prioridad"
                                },
                                "color": "#b91c1c",
                                "fontWeight": "bold"
                            },
                            {
                                "if": {
                                    "filter_query": '{Prioridad} = "Media"',
                                    "column_id": "Prioridad"
                                },
                                "color": "#a16207",
                                "fontWeight": "bold"
                            }
                        ]
                    ),

                    html.P(
                        "La evidencia muestra los datos que activaron cada regla. Las acciones sugeridas orientan la revisión, pero los hallazgos no demuestran por sí solos las causas.",
                        style={
                            "fontSize": "11px",
                            "color": "#666",
                            "margin": "10px 0 0 0"
                        }
                    )
                ],
                style={
                    **estilo_panel,
                    "marginBottom": "14px"
                }
            ),

            # Catálogo de reglas de detección.
            html.Details(
                [
                    html.Summary(
                        "Reglas de detección y criterios de análisis",
                        style={
                            "fontSize": "14px",
                            "fontWeight": "bold",
                            "cursor": "pointer",
                            "padding": "4px 0"
                        }
                    ),

                    html.P(
                        "Este catálogo detalla las condiciones que debe cumplir un dato para generar un hallazgo.",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "10px 0"
                        }
                    ),

                    dash_table.DataTable(
                        id="decisiones_tabla_reglas",
                        columns=[
                            {"name": "Hallazgo", "id": "Hallazgo"},
                            {"name": "Regla de detección", "id": "Regla"},
                            {"name": "Alcance", "id": "Alcance"}
                        ],
                        data=[
                            {
                                "Hallazgo": "Caída de facturación",
                                "Regla": (
                                    "Variación mensual inferior a -10 %. "
                                    "Prioridad alta si es igual o inferior a -20 %."
                                ),
                                "Alcance": (
                                    "Comparación con el mes calendario anterior."
                                )
                            },
                            {
                                "Hallazgo": "Reseñas bajas",
                                "Regla": (
                                    "Puntuación promedio igual o inferior "
                                    "a 3,5 sobre 5 y al menos 5 reseñas únicas."
                                ),
                                "Alcance": (
                                    "Por categoría de producto y período seleccionado."
                                )
                            },
                            {
                                "Hallazgo": "Aumento de cancelaciones",
                                "Regla": (
                                    "Aumento superior a 0,5 puntos porcentuales "
                                    "respecto del mes anterior."
                                ),
                                "Alcance": (
                                    "Pedidos únicos cancelados o no disponibles "
                                    "sobre el total de pedidos."
                                )
                            }
                        ],
                        style_table={
                            "overflowX": "auto"
                        },
                        style_cell={
                            "padding": "9px",
                            "textAlign": "left",
                            "fontFamily": "Arial",
                            "fontSize": "12px",
                            "minWidth": "150px",
                            "maxWidth": "360px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "whiteSpace": "normal"
                        }
                    ),

                    html.P(
                        "La facturación considera el valor de los productos en R$, sin flete, excluyendo pedidos cancelados y no disponibles. La tasa de cancelación incluye ambos estados y se calcula sobre pedidos únicos con artículos. Los hallazgos son señales para revisar, no pruebas de causalidad.",
                        style={
                            "fontSize": "11px",
                            "color": "#666",
                            "margin": "10px 0 0 0"
                        }
                    )
                ],
                open=False,
                style={
                    **estilo_panel,
                    "marginBottom": "14px"
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