"""Prueba HTTP de lectura contra Docker local o un despliegue accesible.

Uso: python scripts/check_deployment.py [http://127.0.0.1:8080]
No requiere credenciales, no modifica Supabase y no imprime registros.
No sustituye una revisión visual en navegador.
"""
import json
import sys
from urllib.request import Request, urlopen


BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")


def get(path):
    with urlopen(BASE + path, timeout=90) as response:
        return response.read()


def callback(outputs, inputs, changed=None):
    multiple = len(outputs) > 1
    descriptors = [{"id": i, "property": p} for i, p in outputs]
    names = [f"{i}.{p}" for i, p in outputs]
    payload = {
        "output": ".." + "...".join(names) + ".." if multiple else names[0],
        "outputs": descriptors if multiple else descriptors[0],
        "inputs": [{"id": i, "property": p, "value": v} for i, p, v in inputs],
        "state": [], "changedPropIds": changed or [f"{inputs[0][0]}.{inputs[0][1]}"],
    }
    request = Request(BASE + "/dashboard/_dash-update-component",
                      data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=90) as response:
        raw = response.read().decode()
    assert "No pudimos cargar" not in raw, "El backend devolvió un estado de error"
    return json.loads(raw)["response"]


def business(area, view, dimension, year="__todos__", month="__todos__"):
    return callback([("business-content", "children")], [
        ("business-area", "data", area), ("business-view", "data", view),
        ("business-year", "value", year), ("business-month", "value", month),
        ("business-dimension", "value", dimension),
        ("business-min-sample", "value", 30), ("business-recency", "value", 90),
    ])


def main():
    assert b"UCASAL" in get("/")
    assert json.loads(get("/dashboard/healthz"))["status"] == "ok"
    assert get("/dashboard/assets/ucasal-logo.png").startswith(b"\x89PNG")
    for area in ("ventas", "logistica", "clientes"):
        for view in ("gerencial", "analitica", "decisiones"):
            route = callback([
                ("selector_dashboard", "value"), ("selector_vista", "value"),
                ("dashboard-navigation", "style"),
            ], [
                ("selector_dashboard", "value", "ventas"),
                ("dashboard-location", "search", f"?area={area}&vista={view}&embed=1"),
            ], changed=["dashboard-location.search"])
            assert route["selector_dashboard"]["value"] == area
            assert route["selector_vista"]["value"] == view
            callback([("contenedor_dashboard", "children")], [
                ("selector_dashboard", "value", area), ("selector_vista", "value", view),
            ])
            if area != "ventas":
                business(area, view, "customer_state" if area == "logistica" else "segment")
            print(f"OK {area}/{view}", flush=True)

    for dimension in ("seller_id", "seller_state", "distance_band"):
        business("logistica", "analitica", dimension, 2018, 1)
    business("clientes", "analitica", "gold_segment", 2018, 1)
    for area in ("logistica", "clientes"):
        result = business(area, "gerencial", "customer_state" if area == "logistica" else "segment", 1900)
        assert "No hay" in json.dumps(result)
    print("OK filtros, agrupaciones alternativas y periodos vacios", flush=True)

    callback([
        ("kpi_facturacion", "children"), ("kpi_articulos", "children"),
        ("kpi_compradores", "children"), ("kpi_vendedores", "children"),
        ("grafico_facturacion", "figure"), ("grafico_categorias", "figure"),
        ("grafico_vendedores", "figure"),
    ], [
        ("filtro_modo_fecha", "value", "anual"), ("filtro_anio", "value", "__todos__"),
        ("filtro_trimestre", "value", "__todos__"), ("filtro_mes", "value", None),
    ])
    callback([
        ("tabla_analitica_ventas", "columns"), ("tabla_analitica_ventas", "data"),
        ("tabla_analitica_ventas", "style_data_conditional"), ("grafico_analitica_ventas", "figure"),
    ], [
        ("analitica_dimension", "value", "anio"), ("analitica_dimension_secundaria", "value", "__ninguna__"),
        ("analitica_anio", "value", "__todos__"), ("analitica_estado", "value", "__todos__"),
        ("analitica_metricas", "value", ["facturacion", "pedidos", "compradores"]),
    ])
    result = callback([
        ("decisiones_total_alertas", "children"), ("decisiones_caida_facturacion", "children"),
        ("decisiones_categorias_resenas", "children"), ("decisiones_tasa_cancelacion", "children"),
        ("decisiones_tasa_cancelacion", "style"), ("decisiones_grafico_facturacion", "figure"),
        ("decisiones_grafico_categorias", "figure"), ("decisiones_tabla_hallazgos", "columns"),
        ("decisiones_tabla_hallazgos", "data"),
    ], [
        ("selector_vista", "value", "decisiones"),
        ("decisiones_filtro_anio", "value", "__todos__"),
        ("decisiones_filtro_mes", "value", "__todos__"),
    ])
    assert any(c["id"] == "Acción sugerida" for c in result["decisiones_tabla_hallazgos"]["columns"])
    print("OK indicadores, analitica y decisiones de Ventas", flush=True)


if __name__ == "__main__":
    main()
