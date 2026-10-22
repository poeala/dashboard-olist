"""Evaluación descriptiva de reglas: fronteras, sensibilidad y grano compartido."""
import json
import unittest

import pandas as pd
from plotly.utils import PlotlyJSONEncoder

from components.business import logistics_content
from data.business_metrics import (
    agrupar_logistica, evaluar_regla_logistica, pedidos_logistica,
    resumen_logistica, sensibilidad_logistica,
)
from fixtures_business import logistics_fixture


class LogisticsRulesTests(unittest.TestCase):
    def setUp(self):
        self.groups = pd.DataFrame({
            "group": ["A", "B", "C", "D", "Pequeño", "Sin fechas"],
            "eligible": [100, 100, 100, 100, 29, 0],
            "late_pct": [8., 10., 12., 18., 90., float("nan")],
        })

    def test_strict_threshold_and_minimum(self):
        limit, selected = evaluar_regla_logistica(self.groups, 3)
        self.assertEqual(limit, 10)
        self.assertEqual(self.groups.loc[selected, "group"].tolist(), ["C", "D"])
        self.groups.loc[4, "eligible"] = 30
        _, selected = evaluar_regla_logistica(self.groups, 3)
        self.assertTrue(selected.iloc[4])

    def test_membership_changes_match_counts(self):
        summary, detail = sensibilidad_logistica(self.groups, 3)
        summary = summary.set_index("scenario")
        self.assertEqual(summary.loc["Base", "selected"], 2)
        self.assertEqual(summary.loc["Piso 5 %", "limit"], 8)
        self.assertEqual(summary.loc["Piso 5 %", "entered"], 1)
        self.assertEqual(summary.loc["Piso 15 %", "exited"], 1)
        self.assertEqual(summary.loc["Margen +10 pp", "selected"], 1)
        self.assertEqual(detail.set_index("group").loc["Pequeño", "Base"], "No evaluable")
        for scenario in summary.index:
            self.assertEqual((detail[scenario] == "Seleccionado").sum(), summary.loc[scenario, "selected"])
            self.assertEqual(summary.loc[scenario, "selected"],
                             summary.loc[scenario, "retained"] + summary.loc[scenario, "entered"])

    def test_floor_has_no_effect_when_relative_threshold_dominates(self):
        summary, _ = sensibilidad_logistica(self.groups, 20)
        self.assertEqual(summary.loc[:2, "limit"].tolist(), [25, 25, 25])
        self.assertTrue(summary.loc[:2, "entered"].eq(0).all())
        self.assertTrue(summary.loc[:2, "exited"].eq(0).all())

    def test_no_reference_and_unreachable_threshold(self):
        for reference in (None, float("nan")):
            summary, detail = sensibilidad_logistica(self.groups, reference)
            self.assertTrue(summary["limit"].isna().all())
            self.assertTrue(summary["evaluable"].eq(0).all())
            self.assertTrue(summary["selected"].eq(0).all())
            self.assertTrue(detail["Base"].eq("No evaluable").all())
        limit, selected = evaluar_regla_logistica(self.groups, 98)
        self.assertEqual(limit, 103)
        self.assertFalse(selected.any())
        summary, detail = sensibilidad_logistica(self.groups.iloc[:0], None)
        self.assertEqual(len(summary), 5)
        self.assertTrue(detail.empty)

    def test_shared_order_is_an_association_in_both_seller_groups(self):
        rows = logistics_fixture()
        groups = agrupar_logistica(rows, "seller_id").set_index("group")
        self.assertEqual(groups.loc["s1", "late"], 1)
        self.assertEqual(groups.loc["s2", "late"], 1)
        stats = resumen_logistica(pedidos_logistica(rows))
        self.assertEqual(stats["late"], 1)
        self.assertEqual(stats["late_pct"], 50)
        # La referencia global no es la media de las tres tasas por vendedor.
        self.assertNotEqual(stats["late_pct"], groups["late_pct"].mean())

    def test_scope_is_visible_in_all_views_and_sensitivity_in_decisions(self):
        for view in ("gerencial", "analitica", "decisiones"):
            content = logistics_content(logistics_fixture(), view, "customer_state", 5, pd.Timestamp("2018-03-31"))
            rendered = json.dumps(content, cls=PlotlyJSONEncoder, ensure_ascii=False)
            self.assertIn("no atribuir automáticamente un retraso", rendered)
            if view == "decisiones":
                self.assertIn("Sensibilidad de la regla de prioridad", rendered)
                self.assertIn("Selección de cada grupo por escenario", rendered)


if __name__ == "__main__":
    unittest.main()
