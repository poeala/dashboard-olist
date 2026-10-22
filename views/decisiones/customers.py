
# Vista de toma de decisiones de clientes

from dash import dcc, html, dash_table


def crear_vista_decisiones_clientes():

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
                    options=[{"label": "Todos", "value": "todos"}],
                    value="todos",
                    clearable=False,
                    searchable=False,
                ),
            ],
            style={"flex": "1", "minWidth": "140px"},
        )

    estilo_panel = {
        "backgroundColor": "white",
        "padding": "14px",
        "borderRadius": "8px",
        "boxShadow": "0 1px 5px #dddddd",
        "boxSizing": "border-box",
        "minWidth": "0",
    }

    estilo_tarjeta = {
        **estilo_panel,
        "flex": "1 1 190px",
        "minWidth": "180px",
    }

    estilo_titulo_tarjeta = {
        "fontSize": "12px",
        "color": "#666",
        "margin": "0 0 8px 0",
    }

    estilo_valor_tarjeta = {
        "fontSize": "25px",
        "margin": "0 0 6px 0",
        "color": "#222",
    }

    estilo_detalle_tarjeta = {
        "fontSize": "11px",
        "color": "#777",
        "margin": "0",
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
                                "Identificá clientes que requieren atención y "
                                "oportunidades de fidelización a partir de los datos.",
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
                style={
                    "fontSize": "12px",
                    "color": "#666",
                    "margin": "0 0 12px 0",
                },
            ),

            # Indicadores principales.
            html.Div(
                [
                    html.Div(
                        [
                            html.P(
                                "Hallazgos detectados",
                                style=estilo_titulo_tarjeta,
                            ),
                            html.H3(
                                "0",
                                id="decisiones_clientes_kpi_hallazgos",
                                style=estilo_valor_tarjeta,
                            ),
                            html.P(
                                "Reglas que requieren revisión",
                                style=estilo_detalle_tarjeta,
                            ),
                        ],
                        style=estilo_tarjeta,
                    ),
                    html.Div(
                        [
                            html.P(
                                "Clientes con baja satisfacción",
                                style=estilo_titulo_tarjeta,
                            ),
                            html.H3(
                                "0 %",
                                id="decisiones_clientes_kpi_baja_satisfaccion",
                                style=estilo_valor_tarjeta,
                            ),
                            html.P(
                                "Calificación promedio por cliente ≤ 3/5",
                                style=estilo_detalle_tarjeta,
                            ),
                        ],
                        style=estilo_tarjeta,
                    ),
                    html.Div(
                        [
                            html.P(
                                "Alto valor y baja satisfacción",
                                style=estilo_titulo_tarjeta,
                            ),
                            html.H3(
                                "0 %",
                                id="decisiones_clientes_kpi_alto_valor",
                                style=estilo_valor_tarjeta,
                            ),
                            html.P(
                                "Clientes de alto gasto con calificación ≤ 3/5",
                                style=estilo_detalle_tarjeta,
                            ),
                        ],
                        style=estilo_tarjeta,
                    ),
                    html.Div(
                        [
                            html.P(
                                "Clientes de una sola compra",
                                style=estilo_titulo_tarjeta,
                            ),
                            html.H3(
                                "0 %",
                                id="decisiones_clientes_kpi_compra_unica",
                                style=estilo_valor_tarjeta,
                            ),
                            html.P(
                                "Clientes con un único pedido registrado",
                                style=estilo_detalle_tarjeta,
                            ),
                        ],
                        style=estilo_tarjeta,
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),

            # Gráficos.
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(
                                id="decisiones_clientes_grafico_satisfaccion",
                                config={
                                    "displaylogo": False,
                                    "responsive": True,
                                },
                            ),
                        ],
                        style=estilo_panel,
                    ),
                    html.Div(
                        [
                            dcc.Graph(
                                id="decisiones_clientes_grafico_gasto",
                                config={
                                    "displaylogo": False,
                                    "responsive": True,
                                },
                            ),
                        ],
                        style=estilo_panel,
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": (
                        "repeat(auto-fit, minmax(320px, 1fr))"
                    ),
                    "gap": "14px",
                    "marginBottom": "14px",
                },
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
                        "Los hallazgos señalan segmentos que conviene revisar. "
                        "La prioridad depende de la regla detectada y de su evidencia.",
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "margin": "0 0 12px 0",
                        },
                    ),
                    dash_table.DataTable(
                        id="decisiones_clientes_tabla_hallazgos",
                        columns=[],
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
                                    "filter_query": '{Prioridad} = "Alta"',
                                    "column_id": "Prioridad",
                                },
                                "color": "#b91c1c",
                                "fontWeight": "bold",
                            },
                            {
                                "if": {
                                    "filter_query": '{Prioridad} = "Media"',
                                    "column_id": "Prioridad",
                                },
                                "color": "#a16207",
                                "fontWeight": "bold",
                            },
                        ],
                    ),
                ],
                style={
                    **estilo_panel,
                    "marginBottom": "14px",
                },
            ),

            # Criterios de detección.
            html.Details(
                [
                    html.Summary(
                        "Reglas de detección y criterios de análisis",
                        style={
                            "cursor": "pointer",
                            "fontSize": "14px",
                            "fontWeight": "bold",
                        },
                    ),
                    html.Div(
                        [
                            html.P(
                                "Las reglas son exploratorias: ayudan a priorizar "
                                "revisiones, pero no demuestran causalidad ni abandono.",
                                style={
                                    "fontSize": "12px",
                                    "color": "#666",
                                    "margin": "10px 0",
                                },
                            ),
                            dash_table.DataTable(
                                id="decisiones_clientes_tabla_reglas",
                                columns=[
                                    {"name": "Regla", "id": "Regla"},
                                    {"name": "Criterio", "id": "Criterio"},
                                    {
                                        "name": "Interpretación",
                                        "id": "Interpretación",
                                    },
                                ],
                                data=[
                                    {
                                        "Regla": "Baja satisfacción",
                                        "Criterio": (
                                            "Promedio de calificaciones por cliente "
                                            "del segmento ≤ 3,5/5 y al menos 20 "
                                            "clientes con calificación válida."
                                        ),
                                        "Interpretación": (
                                            "Revisar reseñas, entregas y categorías "
                                            "para identificar posibles problemas."
                                        ),
                                    },
                                    {
                                        "Regla": "Alto valor con baja satisfacción",
                                        "Criterio": (
                                            "Gasto histórico igual o superior al "
                                            "percentil 75 y calificación por cliente "
                                            "≤ 3/5. Al menos 5 casos en el segmento."
                                        ),
                                        "Interpretación": (
                                            "Priorizar la revisión de experiencias "
                                            "negativas entre clientes de alto gasto."
                                        ),
                                    },
                                    {
                                        "Regla": "Alto gasto con compra única",
                                        "Criterio": (
                                            "Un pedido y gasto histórico igual o "
                                            "superior al percentil 75. Al menos "
                                            "10 casos en el segmento."
                                        ),
                                        "Interpretación": (
                                            "Evaluar acciones de segunda compra y "
                                            "medir su conversión antes de generalizarlas."
                                        ),
                                    },
                                ],
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "padding": "9px",
                                    "textAlign": "left",
                                    "fontFamily": "Arial",
                                    "fontSize": "12px",
                                    "minWidth": "150px",
                                    "maxWidth": "400px",
                                    "whiteSpace": "normal",
                                    "height": "auto",
                                },
                                style_header={
                                    "fontWeight": "bold",
                                    "backgroundColor": "#f0f2f5",
                                    "textAlign": "left",
                                    "whiteSpace": "normal",
                                },
                            ),
                            html.P(
                                "El año y el mes filtran por fecha de última compra. "
                                "Los pedidos, el gasto y las calificaciones de cada "
                                "cliente conservan su historial Gold. Los clientes "
                                "sin calificación válida no participan en los promedios.",
                                style={
                                    "fontSize": "11px",
                                    "color": "#666",
                                    "margin": "10px 0 0 0",
                                },
                            ),
                        ],
                        style={"marginTop": "10px"},
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
