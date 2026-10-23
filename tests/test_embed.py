"""Pruebas del prefijo y la navegación, sin consultar la base de datos."""
import importlib
import json
import unittest
from unittest.mock import patch

import pandas as pd
from fixtures_business import logistics_fixture
from test_payments import payments_fixture


class EmbedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("data.sales.cargar_ventas", return_value=pd.DataFrame({"anio": [2018]})):
            cls.module = importlib.import_module("app")
        cls.client = cls.module.server.test_client()

    def test_prefixed_endpoints(self):
        for path in (
            "/dashboard/",
            "/dashboard/_dash-layout",
            "/dashboard/_dash-dependencies",
            "/dashboard/assets/logo.png",
            "/dashboard/assets/ucasal-logo.png",
            "/dashboard/assets/00_leaflet/leaflet.js",
            "/dashboard/assets/00_leaflet/leaflet.css",
            "/dashboard/assets/logistics_map.js",
            "/dashboard/assets/01_logistics_scale.js",
            "/dashboard/assets/br_regions.geojson",
        ):
            with self.subTest(path=path):
                with self.client.get(path) as response:
                    self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get("/dashboard/healthz").json,
            {"status": "ok", "service": "olist-dashboard"},
        )
        html = self.client.get("/dashboard/").get_data(as_text=True)
        self.assertIn("/dashboard/_dash-component-suites/", html)
        self.assertIn("/dashboard/assets/styles.css", html)
        # Leaflet must be available when Dash invokes the clientside callback.
        self.assertLess(html.index("00_leaflet/leaflet.js"), html.index("dash_renderer.v"))

    def test_logistics_navigation_builds_the_layout(self):
        response = self.client.post("/dashboard/_dash-update-component", json={
            "output": "contenedor_dashboard.children",
            "outputs": {"id": "contenedor_dashboard", "property": "children"},
            "inputs": [
                {"id": "selector_dashboard", "property": "value", "value": "logistica"},
                {"id": "selector_vista", "property": "value", "value": "gerencial"},
            ],
            "state": [], "changedPropIds": ["selector_dashboard.value"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("business-content", response.get_data(as_text=True))

    def test_payments_navigation_and_callbacks(self):
        with patch("callbacks.payments.cargar_pagos_bi", side_effect=payments_fixture):
            for view in ("gerencial", "analitica", "decisiones"):
                response = self.client.post("/dashboard/_dash-update-component", json={
                    "output": "contenedor_dashboard.children",
                    "outputs": {"id": "contenedor_dashboard", "property": "children"},
                    "inputs": [
                        {"id": "selector_dashboard", "property": "value", "value": "pagos"},
                        {"id": "selector_vista", "property": "value", "value": view}],
                    "state": [], "changedPropIds": ["selector_dashboard.value"],
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn("payments-content", response.get_data(as_text=True))
                for year in (2018, 1900):
                    values = [("payments-view", "data", view), ("payments-year", "value", year),
                              ("payments-month", "value", "__todos__")]
                    response = self.client.post("/dashboard/_dash-update-component", json={
                        "output": "payments-content.children",
                        "outputs": {"id": "payments-content", "property": "children"},
                        "inputs": [{"id": i, "property": p, "value": v} for i, p, v in values],
                        "state": [], "changedPropIds": ["payments-view.data"],
                    })
                    self.assertEqual(response.status_code, 200)
                    rendered = json.dumps(response.json)
                    self.assertNotIn("No pudimos cargar", rendered)
                    if year == 1900:
                        self.assertIn("No hay pedidos", rendered)

    def test_payments_month_switches_to_daily_evolution(self):
        with patch("callbacks.payments.cargar_pagos_bi", side_effect=payments_fixture):
            for month, expected in ((1, "evolución diaria"), ("__todos__", "evolución mensual")):
                response = self.client.post("/dashboard/_dash-update-component", json={
                    "output": "payments-content.children",
                    "outputs": {"id": "payments-content", "property": "children"},
                    "inputs": [
                        {"id": "payments-view", "property": "data", "value": "gerencial"},
                        {"id": "payments-year", "property": "value", "value": 2018},
                        {"id": "payments-month", "property": "value", "value": month},
                    ],
                    "state": [], "changedPropIds": ["payments-month.value"],
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(expected, json.dumps(response.json, ensure_ascii=False))

    def test_embedded_view_and_standalone_navigation(self):
        output = "..selector_dashboard.value...selector_vista.value...dashboard-navigation.style.."
        for search, changed, area, view, hidden in (
            ("?vista=analitica&embed=1", [], "ventas", "analitica", True),
            ("?area=logistica&vista=decisiones&embed=1", [], "logistica", "decisiones", True),
            ("?area=clientes&vista=analitica&embed=1", [], "clientes", "analitica", True),
            ("?area=invalida&vista=desconocida&embed=1", [], "ventas", "gerencial", True),
            ("?vista=analitica", [], "ventas", "analitica", False),
            ("?area=clientes&vista=analitica", ["selector_dashboard.value"], "ventas", "gerencial", False),
        ):
            with self.subTest(search=search, changed=changed):
                response = self.client.post("/dashboard/_dash-update-component", json={
                    "output": output,
                    "outputs": [
                        {"id": "selector_dashboard", "property": "value"},
                        {"id": "selector_vista", "property": "value"},
                        {"id": "dashboard-navigation", "property": "style"},
                    ],
                    "inputs": [
                        {"id": "selector_dashboard", "property": "value", "value": "ventas"},
                        {"id": "dashboard-location", "property": "search", "value": search},
                    ],
                    "state": [],
                    "changedPropIds": changed,
                })
                self.assertEqual(response.status_code, 200)
                result = response.json["response"]
                self.assertEqual(result["selector_dashboard"]["value"], area)
                self.assertEqual(result["selector_vista"]["value"], view)
                self.assertEqual(result["dashboard-navigation"]["style"], {"display": "none"} if hidden else {})

    def test_business_callback_delivers_logistics_views(self):
        with patch("callbacks.business.cargar_logistica", side_effect=logistics_fixture):
            for view in ("gerencial", "analitica", "decisiones"):
                with self.subTest(view=view):
                    values = [
                        ("business-view", "data", view),
                        ("business-year", "value", "__todos__"), ("business-month", "value", "__todos__"),
                        ("business-dimension", "value", "customer_state"),
                        ("business-min-sample", "value", 5),
                    ]
                    response = self.client.post("/dashboard/_dash-update-component", json={
                        "output": "business-content.children",
                        "outputs": {"id": "business-content", "property": "children"},
                        "inputs": [{"id": i, "property": p, "value": v} for i, p, v in values],
                        "state": [], "changedPropIds": ["business-view.data"],
                    })
                    self.assertEqual(response.status_code, 200)
                    content = json.dumps(response.json, ensure_ascii=False)
                    self.assertNotIn("No pudimos cargar", content)
                    if view == "gerencial":
                        self.assertIn("logistics-region-map", content)
                        self.assertIn("/dashboard/assets/br_regions.geojson", content)


if __name__ == "__main__":
    unittest.main()
