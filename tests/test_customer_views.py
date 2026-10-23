"""Separación de vistas, reglas de intervención y filtros reales de callbacks."""
import json
import unittest
from unittest.mock import patch

import pandas as pd
from dash import Dash
from plotly.utils import PlotlyJSONEncoder

from callbacks.customers.analytics import registrar_callbacks_analitica_clientes
from callbacks.customers.decisions import generar_intervenciones, registrar_callbacks_decisiones_clientes
from components.customers import customers_content
from components.customer_analysis import customer_analysis
from fixtures_business import customers_fixture
from views.decisiones.customers import crear_vista_decisiones_clientes


def gold_fixture():
    return pd.DataFrame([
        dict(customer_id=f"{segment}-{i}", customer_segment=segment,
             total_orders=orders, total_spent=spent, avg_review_score=score,
             first_purchase_date=pd.Timestamp("2017-01-01"),
             last_purchase_date=pd.Timestamp(date), preferred_payment_type="credit_card")
        for segment, orders, spent, score, date in (
            ("Insatisfechos", 2, 100, 2, "2018-01-01"),
            ("Compra única", 1, 500, 4, "2018-02-01"),
        ) for i in range(20)
    ])


def serialize(component):
    return json.dumps(component, cls=PlotlyJSONEncoder, ensure_ascii=False)


class CustomerViewsTests(unittest.TestCase):
    def test_management_has_four_kpis_and_only_time_charts(self):
        rendered = serialize(customers_content(
            customers_fixture(), "gerencial", "segment", 20, 90, pd.Timestamp("2018-03-31"),
        ))
        self.assertEqual(rendered.count('"className": "business-card"'), 4)
        self.assertIn("Compradores activos por mes", rendered)
        self.assertIn("Evolución del gasto promedio por cliente", rendered)
        self.assertNotIn("Distribución de segmentos", rendered)

    def test_decisions_has_no_descriptive_graphs_or_kpis(self):
        rendered = serialize(crear_vista_decisiones_clientes())
        self.assertNotIn('"type": "Graph"', rendered)
        self.assertNotIn("decisiones_clientes_total", rendered)
        self.assertIn("Hallazgos detectados", rendered)

    def test_priorities_and_targeted_high_spending(self):
        rows = generar_intervenciones(gold_fixture())
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["Prioridad"], "Alta")
        self.assertEqual(rows[0]["Segmento"], "Insatisfechos")
        self.assertTrue(all(row["Acción sugerida"] and row["Seguimiento"] for row in rows))
        duplicate = pd.concat([gold_fixture(), gold_fixture()])
        self.assertEqual(rows, generar_intervenciones(duplicate))

    def test_minimum_valid_samples_and_boundary(self):
        df = gold_fixture().iloc[:20].copy()
        df["avg_review_score"] = 3.5
        self.assertEqual(generar_intervenciones(df)[0]["Prioridad"], "Media")
        df.loc[0, "avg_review_score"] = None
        self.assertEqual(generar_intervenciones(df), [])
        df["avg_review_score"] = None
        df["total_orders"] = [2] * 5 + [1] * 15
        self.assertEqual(generar_intervenciones(df), [])  # exactamente 25 %
        df["total_orders"] = None
        self.assertEqual(generar_intervenciones(df), [])
        self.assertEqual(generar_intervenciones(df.iloc[:0]), [])

    def test_analytics_distributions_and_no_customer_ids(self):
        rendered = serialize(customer_analysis(gold_fixture()))
        for title in ("Distribución de segmentos", "Recurrencia por segmento",
                      "Distribución del gasto por cliente", "Relación entre frecuencia y gasto"):
            self.assertIn(title, rendered)
        self.assertNotIn("Insatisfechos-0", rendered)

    def test_callbacks_apply_filters_and_empty_states(self):
        app = Dash(__name__, suppress_callback_exceptions=True)
        registrar_callbacks_decisiones_clientes(app)
        registrar_callbacks_analitica_clientes(app)
        decisions = next(v["callback"].__wrapped__ for k, v in app.callback_map.items()
                         if "tabla_hallazgos.data" in k)
        analytics = app.callback_map["clientes_patrones_analitica.children"]["callback"].__wrapped__
        with patch("callbacks.customers.decisions.cargar_clientes_gold", side_effect=gold_fixture), \
             patch("callbacks.customers.analytics.cargar_clientes_gold", side_effect=gold_fixture):
            _, rows, _ = decisions(2018, 1)
            self.assertEqual({row["Segmento"] for row in rows}, {"Insatisfechos"})
            _, rows, message = decisions(1900, "todos")
            self.assertEqual(rows, [])
            self.assertIn("No hay clientes", message)
            rendered = serialize(analytics("gold_segment", "__ninguna__", "Compra única", ""))
            self.assertNotIn("Insatisfechos", rendered)
            self.assertIn("Compra única", rendered)


if __name__ == "__main__":
    unittest.main()
