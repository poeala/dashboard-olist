import unittest

import pandas as pd
from plotly.utils import PlotlyJSONEncoder
import json

from data.business_metrics import (
    filtrar_periodo, corte_periodo, pedidos_logistica, resumen_logistica,
    agrupar_logistica, perfil_clientes, resumen_clientes, agrupar_clientes,
)
from data.definitions import facturacion_mensual, ventas_validas
from components.business import logistics_content, customers_content
from fixtures_business import logistics_fixture, customers_fixture


class LogisticsTests(unittest.TestCase):
    def test_multi_seller_order_counts_once_and_sums_freight(self):
        orders = pedidos_logistica(logistics_fixture())
        summary = resumen_logistica(orders)
        self.assertEqual(summary["orders"], 3)
        self.assertEqual(summary["eligible"], 2)
        self.assertEqual(summary["late"], 1)
        self.assertEqual(summary["late_pct"], 50)
        self.assertEqual(summary["avg_days"], 8)
        self.assertAlmostEqual(summary["avg_freight"], 50 / 3)

    def test_no_delivery_is_not_counted_on_time(self):
        rows = logistics_fixture().query("order_id == 'b'")
        summary = resumen_logistica(pedidos_logistica(rows))
        self.assertIsNone(summary["late_pct"])
        self.assertTrue(pd.isna(summary["avg_days"]))

    def test_same_origin_deduplicates_order_and_weights_reviews_by_order(self):
        groups = agrupar_logistica(logistics_fixture(), "seller_state").set_index("group")
        self.assertEqual(groups.loc["RJ", "orders"], 2)
        self.assertEqual(groups.loc["RJ", "eligible"], 1)
        self.assertEqual(groups.loc["RJ", "avg_freight"], 17.5)
        self.assertEqual(groups.loc["RJ", "avg_review"], 2)

    def test_unknown_distance_is_retained(self):
        groups = agrupar_logistica(logistics_fixture(), "distance_band")
        self.assertIn("Sin información", groups["group"].values)


class CustomersTests(unittest.TestCase):
    def test_ticket_is_weighted_by_orders_and_not_by_customers(self):
        profiles = perfil_clientes(customers_fixture(), pd.Timestamp("2018-03-31"))
        summary = resumen_clientes(profiles)
        self.assertEqual(summary["customers"], 2)
        self.assertEqual(summary["repeat_pct"], 50)
        self.assertAlmostEqual(summary["ticket"], 500 / 3)
        groups = agrupar_clientes(profiles, "gold_segment")
        self.assertEqual(groups.iloc[0]["avg_review"], 3)
        self.assertAlmostEqual(groups.iloc[0]["ticket"], 500 / 3)

    def test_monthly_recalculation_and_historical_reference(self):
        source = customers_fixture()
        january = filtrar_periodo(source, 2018, 1)
        reference = corte_periodo(source, 2018, 1)
        profiles = perfil_clientes(january, reference)
        self.assertEqual(reference, pd.Timestamp("2018-01-31"))
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles.iloc[0]["recency_days"], 11)
        self.assertEqual(profiles.iloc[0]["spent"], 200)
        self.assertEqual(profiles.iloc[0]["orders"], 2)

    def test_reference_never_exceeds_available_cutoff(self):
        source = customers_fixture()
        self.assertEqual(corte_periodo(source, 2018, 12), pd.Timestamp("2018-03-31"))
        self.assertEqual(corte_periodo(source, "__todos__", 12), pd.Timestamp("2017-12-31"))
        source.attrs["cutoff"] = pd.Timestamp("2018-03-31", tz="UTC")
        self.assertEqual(corte_periodo(source), pd.Timestamp("2018-03-31"))

    def test_duplicate_order_does_not_inflate_customer_value(self):
        source = customers_fixture()
        duplicated = pd.concat([source, source.iloc[[0]]])
        stats = resumen_clientes(perfil_clientes(duplicated, pd.Timestamp("2018-03-31")))
        self.assertEqual(stats["spent"], 500)
        self.assertEqual(stats["orders"], 3)


class SalesTests(unittest.TestCase):
    def test_canceled_orders_do_not_change_revenue_trends(self):
        df = pd.DataFrame({
            "order_purchase_date": ["2018-01-01", "2018-02-01", "2018-02-02", "2018-02-03"],
            "order_status": ["delivered", "shipped", " canceled ", "unavailable"],
            "price": [100, 80, 1000, 1000],
        })
        result = facturacion_mensual(df)
        self.assertEqual(ventas_validas(df)["price"].sum(), 180)
        self.assertEqual(result.iloc[1]["Facturación"], 80)
        self.assertEqual(result.iloc[1]["Variación (%)"], -20)

    def test_month_gap_is_not_compared_to_non_consecutive_month(self):
        df = pd.DataFrame({
            "order_purchase_date": ["2018-01-01", "2018-03-01"],
            "order_status": ["delivered", "delivered"], "price": [100, 50],
        })
        result = facturacion_mensual(df)
        self.assertEqual(len(result), 3)
        self.assertTrue(pd.isna(result.iloc[2]["Variación (%)"]))


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dash import Dash
        cls.app = Dash(__name__, url_base_pathname="/dashboard/")

    def test_all_views_serialize_for_populated_and_empty_periods(self):
        for empty in (False, True):
            for view in ("gerencial", "analitica", "decisiones"):
                for area in ("logistica", "clientes"):
                    with self.subTest(empty=empty, view=view, area=area):
                        df = logistics_fixture() if area == "logistica" else customers_fixture()
                        if empty:
                            df = df.iloc[0:0]
                        if area == "logistica":
                            component = logistics_content(df, view, "customer_state", 5, pd.Timestamp("2018-03-31"))
                        else:
                            component = customers_content(df, view, "segment", 5, 90, pd.Timestamp("2018-03-31"))
                        serialized = json.dumps(component, cls=PlotlyJSONEncoder)
                        self.assertIn("Sin datos" if empty else "Pedidos" if area == "logistica" else "Clientes compradores", serialized)


if __name__ == "__main__":
    unittest.main()
