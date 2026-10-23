# Diseño compacto de la vista gerencial de ventas
from dash import html, dcc
from components.kpi import crear_tarjeta
from components.filters import crear_filtros_fecha


# Construir la vista principal del dashboard.
def crear_vista_gerencial_ventas(anios, meses):
    return html.Div(
        [
            # Encabezado y filtros de fechas.
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
                        ]
                    ),
                    html.Div(
                        crear_filtros_fecha(anios, meses),
                        style={
                            "flex": "1",
                            "maxWidth": "650px"
                        }
                    )
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": "16px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px"
                }
            ),

            # Indicadores principales.
            html.Div(
                [
                    crear_tarjeta("Facturación", "0", "kpi_facturacion"),
                    crear_tarjeta("Artículos vendidos", "0", "kpi_articulos"),
                    crear_tarjeta("Compradores únicos", "0", "kpi_compradores"),
                    crear_tarjeta("Vendedores activos", "0", "kpi_vendedores")
                ],
                style={
                    "display": "flex",
                    "gap": "10px",
                    "flexWrap": "nowrap",
                    "marginBottom": "12px"
                }
            ),

            # Gráfico central de facturación.
            html.Div(
                [
                    dcc.Graph(
                        id="grafico_facturacion",
                        config={"displayModeBar": False},
                        style={"height": "300px"}
                    )
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "10px",
                    "borderRadius": "8px",
                    "marginBottom": "12px",
                    "boxShadow": "0 1px 5px #dddddd"
                }
            ),

            # Gráficos inferiores de categorías y vendedores.
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(
                                id="grafico_categorias",
                                config={"displayModeBar": False},
                                style={
                                    "height": "220px",
                                    "minHeight": "220px"
                                }
                            )
                        ],
                        style={
                            "backgroundColor": "white",
                            "padding": "10px",
                            "borderRadius": "8px",
                            "flex": "1 1 0",
                            "boxShadow": "0 1px 5px #dddddd",
                            "minWidth": "0"
                        }
                    ),
                    html.Div(
                        [
                            dcc.Graph(
                                id="grafico_vendedores",
                                config={"displayModeBar": False},
                                style={
                                    "height": "220px",
                                    "minHeight": "220px"
                                }
                            )
                        ],
                        style={
                            "backgroundColor": "white",
                            "padding": "10px",
                            "borderRadius": "8px",
                            "flex": "1 1 0",
                            "boxShadow": "0 1px 5px #dddddd",
                            "minWidth": "0"
                        }
                    )
                ],
                style={
                    "display": "flex",
                    "gap": "10px",
                    "flexWrap": "nowrap"
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