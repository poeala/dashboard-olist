# Vista de toma de decisiones de clientes

from dash import html, dcc, dash_table


def crear_vista_decisiones_clientes():

    # Crear tarjetas para los indicadores.
    def crear_tarjeta(titulo, componente_id):
        return html.Div(
            [
                html.P(
                    titulo,
                    style={
                        "fontSize": "12px",
                        "color": "#666",
                        "margin": "0 0 8px 0",
                    },
                ),
                html.H3(
                    "0",
                    id=componente_id,
                    style={
                        "fontSize": "25px",
                        "margin": "0",
                    },
                ),
            ],
            style={
                "backgroundColor": "white",
                "padding": "16px",
                "borderRadius": "8px",
                "boxShadow": "0 1px 5px #dddddd",
                "flex": "1 1 180px",
                "minWidth": "180px",
                "boxSizing": "border-box",
            },
        )

    # Crear los selectores de año y mes.
    def crear_filtro(titulo, componente_id):
        return html.Div(
            [
                html.Label(
                    titulo,
                    style={
                        "fontSize": "12px",
                        "color": "#666",
                        "display": "block",
                        "marginBottom": "5px",
                    },
                ),
                dcc.Dropdown(
                    id=componente_id,
                    options=[
                        {"label": "Todos", "value": "todos"}
                    ],
                    value="todos",
                    clearable=False,
                    searchable=False,
                ),
            ],
            style={
                "flex": "1",
                "minWidth": "140px",
            },
        )

    # Estilo compartido para los paneles.
    estilo_panel = {
        "backgroundColor": "white",
        "padding": "14px",
        "borderRadius": "8px",
        "boxShadow": "0 1px 5px #dddddd",
        "boxSizing": "border-box",
        "minWidth": "0",
    }

    return html.Div(
        [
            # Encabezado y filtros.
            html.Div(
                [
                    html.Div(
                        [
                            html.H2(
                                "Decisiones de clientes",
                                style={
                                    "margin": "0 0 5px 0",
                                    "fontSize": "23px",
                                },
                            ),
                            html.P(
                                "Indicadores y hallazgos para identificar "
                                "oportunidades de fidelización y mejora.",
                                style={
                                    "margin": "0",
                                    "fontSize": "12px",
                                    "color": "#666",
                                },
                            ),
                        ],
                        style={
                            "flex": "1 1 280px",
                            "minWidth": "220px",
                        },
                    ),
                    html.Div(
                        [
                            crear_filtro(
                                "Año de última compra",
                                "decisiones_clientes_filtro_anio",
                            ),
                            crear_filtro(
                                "Mes",
                                "decisiones_clientes_filtro_mes",
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "10px",
                            "flex": "0 1 400px",
                            "flexWrap": "wrap",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "gap": "20px",
                    "flexWrap": "wrap",
                    "marginBottom": "16px",
                },
            ),

            # Indicadores principales.
            html.Div(
                [
                    crear_tarjeta(
                        "Clientes analizados",
                        "decisiones_clientes_total",
                    ),
                    crear_tarjeta(
                        "Clientes recurrentes",
                        "decisiones_clientes_recurrentes",
                    ),
                    crear_tarjeta(
                        "Gasto promedio por cliente",
                        "decisiones_clientes_gasto_promedio",
                    ),
                    crear_tarjeta(
                        "Puntuación promedio",
                        "decisiones_clientes_resena_promedio",
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),

            # Gráficos principales.
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(
                                id="decisiones_clientes_grafico_segmentos",
                                config={"displayModeBar": False},
                                style={"height": "330px"},
                            ),
                        ],
                        style={
                            **estilo_panel,
                            "flex": "1 1 400px",
                        },
                    ),
                    html.Div(
                        [
                            dcc.Graph(
                                id="decisiones_clientes_grafico_gasto",
                                config={"displayModeBar": False},
                                style={"height": "330px"},
                            ),
                        ],
                        style={
                            **estilo_panel,
                            "flex": "1 1 400px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "14px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),

            # Tabla de hallazgos.
            html.Div(
                [
                    html.H3(
                        "Hallazgos detectados",
                        style={
                            "fontSize": "16px",
                            "margin": "0 0 6px 0",
                        },
                    ),
                    html.P(
                        "Señales que pueden orientar decisiones sobre "
                        "fidelización y experiencia del cliente.",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "0 0 12px 0",
                        },
                    ),
                    dash_table.DataTable(
                        id="decisiones_clientes_tabla_hallazgos",
                        columns=[],
                        data=[],
                        page_size=10,
                        sort_action="native",
                        filter_action="native",
                        style_table={
                            "overflowX": "auto",
                            "minWidth": "100%",
                        },
                        style_cell={
                            "padding": "9px",
                            "textAlign": "left",
                            "fontFamily": "Arial",
                            "fontSize": "12px",
                            "minWidth": "120px",
                            "maxWidth": "340px",
                            "whiteSpace": "normal",
                            "height": "auto",
                        },
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#f0f2f5",
                            "textAlign": "left",
                            "whiteSpace": "normal",
                        },
                        style_data_conditional=[
                            {
                                "if": {
                                    "filter_query": (
                                        '{Prioridad} = "Alta"'
                                    ),
                                    "column_id": "Prioridad",
                                },
                                "color": "#b91c1c",
                                "fontWeight": "bold",
                            },
                            {
                                "if": {
                                    "filter_query": (
                                        '{Prioridad} = "Media"'
                                    ),
                                    "column_id": "Prioridad",
                                },
                                "color": "#a16207",
                                "fontWeight": "bold",
                            },
                        ],
                    ),
                    html.P(
                        "Los hallazgos se basan en umbrales definidos "
                        "para el análisis. Son señales para investigar, "
                        "no pruebas de causalidad.",
                        style={
                            "fontSize": "11px",
                            "color": "#666",
                            "margin": "10px 0 0 0",
                        },
                    ),
                ],
                style={
                    **estilo_panel,
                    "marginBottom": "14px",
                },
            ),
        ],
        style={
            "fontFamily": "Arial",
            "backgroundColor": "#f5f6fa",
            "padding": "14px 20px",
            "minHeight": "100vh",
            "boxSizing": "border-box",
        },
    )