"""Pruebas del prefijo y la navegación, sin consultar la base de datos."""
import importlib
import unittest
from unittest.mock import patch

import pandas as pd
from fixtures_business import logistics_fixture, customers_fixture


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

    def test_business_callback_delivers_all_six_views(self):
        with patch("callbacks.business.cargar_logistica", side_effect=logistics_fixture), \
             patch("callbacks.business.cargar_clientes", side_effect=customers_fixture):
            for area in ("logistica", "clientes"):
                for view in ("gerencial", "analitica", "decisiones"):
                    with self.subTest(area=area, view=view):
                        values = [
                            ("business-area", "data", area), ("business-view", "data", view),
                            ("business-year", "value", "__todos__"), ("business-month", "value", "__todos__"),
                            ("business-dimension", "value", "customer_state" if area == "logistica" else "segment"),
                            ("business-min-sample", "value", 5), ("business-recency", "value", 90),
                        ]
                        response = self.client.post("/dashboard/_dash-update-component", json={
                            "output": "business-content.children",
                            "outputs": {"id": "business-content", "property": "children"},
                            "inputs": [{"id": i, "property": p, "value": v} for i, p, v in values],
                            "state": [], "changedPropIds": ["business-area.data"],
                        })
                        self.assertEqual(response.status_code, 200)
                        self.assertNotIn("No pudimos cargar", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
