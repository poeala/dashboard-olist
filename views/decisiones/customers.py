# Vista de toma de decisiones de clientes

from dash import html, dcc, dash_table


def crear_vista_decisiones_clientes():

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
                                "Segmentos que requieren intervención, prioridades "
                                "y acciones fundamentadas en los datos.",
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

            html.P(
                id="decisiones_clientes_estado",
                className="business-note",
                role="status",
            ),

            # Tabla de hallazgos.
            html.Div(
                [
                    html.H3(
                        "Prioridades de intervención",
                        style={
                            "fontSize": "16px",
                            "margin": "0 0 6px 0",
                        },
                    ),
                    html.P(
                        "Primero las prioridades altas; dentro de cada nivel, "
                        "los grupos con más clientes. Un segmento puede requerir varias acciones.",
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
                        "Base histórica Gold: los filtros seleccionan clientes por última compra; "
                        "sus pedidos, gasto y calificaciones abarcan todo su historial. "
                        "Mínimo: 20 clientes con datos válidos por regla. "
                        "Prioridad alta: calificación ≤ 3/5; media: ≤ 3,5/5, "
                        "recurrencia < 25 % o compra única con gasto ≥ percentil 75. "
                        "Son criterios exploratorios, no pruebas de causalidad ni de abandono.",
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
