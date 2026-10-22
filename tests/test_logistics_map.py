"""Regiones, denominadores y filtros del mapa, sin base de datos."""
import json
import unittest
from pathlib import Path

from data.brazil_regions import REGIONS, STATE_REGION, resumen_regiones
from data.business_metrics import pedidos_logistica, filtrar_periodo
from fixtures_business import logistics_fixture


class RegionMapTests(unittest.TestCase):
    def test_unique_orders_and_weighted_delay_denominator(self):
        summary = resumen_regiones(pedidos_logistica(logistics_fixture()))
        regions = {r["id"]: r for r in summary["regions"]}
        self.assertEqual(sum(r["orders"] for r in regions.values()), 3)
        self.assertEqual(regions["SE"]["orders"], 2)
        self.assertEqual(regions["SE"]["eligible"], 1)
        self.assertEqual(regions["SE"]["late_pct"], 100)
        self.assertEqual(regions["NE"]["late_pct"], 0)
        self.assertIsNone(regions["N"]["late_pct"])

    def test_month_filter_and_empty_period(self):
        for month, expected in ((1, 2), (3, 1), (12, 0)):
            with self.subTest(month=month):
                orders = pedidos_logistica(filtrar_periodo(logistics_fixture(), 2018, month))
                summary = resumen_regiones(orders)
                self.assertEqual(len(summary["regions"]), 5)
                self.assertEqual(sum(r["orders"] for r in summary["regions"]), expected)
                if not expected:
                    self.assertTrue(all(r["late_pct"] is None for r in summary["regions"]))

    def test_normalized_and_unknown_destinations(self):
        rows = logistics_fixture()
        rows.loc[rows.order_id == "a", "customer_state"] = " sp "
        rows.loc[rows.order_id == "b", "customer_state"] = "XX"
        rows.loc[rows.order_id == "c", "customer_state"] = None
        summary = resumen_regiones(pedidos_logistica(rows))
        self.assertEqual(summary["unmapped"], 2)
        self.assertEqual(sum(r["orders"] for r in summary["regions"]), 1)
        json.dumps(summary, allow_nan=False)

    def test_geojson_has_five_regions_covering_all_27_states(self):
        path = Path(__file__).resolve().parents[1] / "assets/br_regions.geojson"
        geojson = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual({f["id"] for f in geojson["features"]}, set(REGIONS))
        self.assertEqual(len(STATE_REGION), 27)
        for feature in geojson["features"]:
            self.assertIn(feature["geometry"]["type"], {"Polygon", "MultiPolygon"})
            self.assertTrue(feature["geometry"]["coordinates"])
            self.assertEqual(set(feature["properties"]["states"]), set(REGIONS[feature["id"]][1]))


if __name__ == "__main__":
    unittest.main()
