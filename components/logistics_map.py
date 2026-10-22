"""Mapa Leaflet con datos agregados y recursos locales bajo el prefijo de Dash."""
from dash import dcc, html, get_asset_url

from data.brazil_regions import resumen_regiones


def mapa_logistica_regiones(orders):
    data = resumen_regiones(orders)
    data["geojson_url"] = get_asset_url("br_regions.geojson")
    return html.Section([
        dcc.Store(id="logistics-map-data", data=data),
        html.Div([
            html.H3("Mapa de calor por región"),
            html.Label("Colorear por", htmlFor="logistics-map-metric"),
            dcc.Dropdown(
                id="logistics-map-metric",
                options=[
                    {"label": "Cantidad de pedidos", "value": "orders"},
                    {"label": "Entregas con retraso (%)", "value": "late_pct"},
                ],
                value="orders", clearable=False, searchable=False,
            ),
        ], className="logistics-map-heading"),
        html.Div(id="logistics-region-map", className="logistics-region-map",
                 role="region", **{"aria-label": "Mapa interactivo de las cinco regiones de Brasil"}),
        html.Div(id="logistics-map-status", className="business-note logistics-map-status",
                 role="status", **{"aria-live": "polite"}),
        html.Details([
            html.Summary("Ver datos por región"),
            html.Div(html.Table([
                html.Thead(html.Tr([html.Th(label, scope="col") for label in
                                   ("Región", "Pedidos", "Comparables", "Tardíos", "Retrasos")])),
                html.Tbody([html.Tr([
                    html.Th(r["name"], scope="row"), html.Td(r["orders"]),
                    html.Td(r["eligible"]), html.Td(r["late"]),
                    html.Td(f"{r['late_pct']:.1f} %".replace(".", ",")
                            if r["late_pct"] is not None else "Sin datos"),
                ]) for r in data["regions"]]),
            ]), className="logistics-map-table"),
        ], className="logistics-map-details"),
        html.P(
            "Destino del cliente · pedidos únicos. Retrasos sobre entregas con fecha real y estimada. "
            + (f"{data['unmapped']} pedidos sin estado reconocido quedan fuera del mapa. " if data["unmapped"] else "")
            + "Pasá el cursor o tocá una región para ver su detalle.",
            className="business-note logistics-map-note",
        ),
    ], className="business-chart logistics-map-card")
