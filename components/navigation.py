# Barra compacta para navegar entre dashboards y vistas
from dash import html, dcc, get_asset_url


def crear_barra_navegacion():
    return html.Div(
        [
            # Mostrar el logo de Olist a la izquierda.
            html.Img(
                src=get_asset_url("logo.png"),
                style={
                    "height": "36px",
                    "width": "auto",
                    "objectFit": "contain",
                    "marginRight": "8px"
                }
            ),

            # Agrupar los selectores de navegación.
            html.Div(
                [
                    # Selector compacto del dashboard.
                    html.Div(
                        [
                            html.Label(
                                "Dashboard",
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "color": "#444",
                                    "whiteSpace": "nowrap"
                                }
                            ),
                            dcc.Dropdown(
                                id="selector_dashboard",
                                options=[
                                    {"label": "Ventas", "value": "ventas"},
                                    {"label": "Logística", "value": "logistica"},
                                    {"label": "Clientes", "value": "clientes"},
                                    {"label": "Pagos", "value": "pagos"}
                                ],
                                value="ventas",
                                clearable=False,
                                searchable=False,
                                style={
                                    "width": "110px",
                                    "fontSize": "12px"
                                }
                            )
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px"
                        }
                    ),

                    # Selector de vista con botones tipo pill.
                    html.Div(
                        [
                            html.Label(
                                "Vista",
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "color": "#444",
                                    "whiteSpace": "nowrap"
                                }
                            ),
                            dcc.RadioItems(
                                id="selector_vista",
                                options=[
                                    {"label": "Gerencial", "value": "gerencial"},
                                    {"label": "Analítica", "value": "analitica"},
                                    {"label": "Decisiones", "value": "decisiones"}
                                ],
                                value="gerencial",
                                inline=True,
                                className="selector-vistas",
                                labelStyle={
                                    "display": "inline-block",
                                    "padding": "6px 12px",
                                    "marginRight": "5px",
                                    "borderRadius": "16px",
                                    "fontSize": "12px",
                                    "cursor": "pointer"
                                },
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "3px",
                                    "padding": "3px",
                                    "backgroundColor": "#f1f3f5",
                                    "borderRadius": "18px"
                                }
                            )
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px"
                        }
                    )
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "24px",
                    "flexWrap": "wrap"
                }
            )
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "16px",
            "padding": "7px 20px",
            "backgroundColor": "white",
            "borderBottom": "1px solid #e5e7eb",
            "marginBottom": "10px",
            "flexWrap": "wrap"
        }
    )
