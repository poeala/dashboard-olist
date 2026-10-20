"""Pruebas del prefijo y la navegación, sin consultar la base de datos."""
import importlib
import unittest
from unittest.mock import patch

import pandas as pd


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
        output = "..selector_vista.value...dashboard-navigation.style.."
        for search, changed, view, hidden in (
            ("?vista=analitica&embed=1", [], "analitica", True),
            ("?vista=decisiones&embed=1", [], "decisiones", True),
            ("?vista=desconocida&embed=1", [], "gerencial", True),
            ("?vista=analitica", [], "analitica", False),
            ("?vista=analitica", ["selector_dashboard.value"], "gerencial", False),
        ):
            with self.subTest(search=search, changed=changed):
                response = self.client.post("/dashboard/_dash-update-component", json={
                    "output": output,
                    "outputs": [
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
                self.assertEqual(result["selector_vista"]["value"], view)
                self.assertEqual(result["dashboard-navigation"]["style"], {"display": "none"} if hidden else {})


if __name__ == "__main__":
    unittest.main()
