import json
import unittest

import pandas as pd
from plotly.utils import PlotlyJSONEncoder

from components.payments import payments_content
from data.payment_metrics import (
    preparar_pagos, resumen_pagos, participacion_pagos,
    agrupar_pedidos_pago, oportunidades_pago, comparaciones_pago,
    evolucion_pagos, resumen_cuotas, participacion_por_tipo_pedido,
)


def payments_fixture():
    rows = pd.DataFrame([
        ["a", 1, "credit_card", 80, 3, True],
        ["a", 2, "voucher", 20, 1, True],
        ["b", 1, "credit_card", 100, 2, True],
        ["b", 2, "credit_card", 100, 4, True],
        ["c", 1, "boleto", 50, 1, True],
        ["d", 1, "credit_card", 70, 0, True],
        ["e", None, None, None, None, False],
        ["f", 1, "voucher", 20, 1, True],
        ["f", 2, "credit_card", None, 2, True],
    ], columns=["order_id", "payment_sequential", "payment_type", "payment_value", "payment_installments", "has_payment"])
    rows["purchase_date"] = pd.Timestamp("2018-01-01")
    rows["gold_segment"] = "Histórico"
    rows.attrs["cutoff"] = pd.Timestamp("2018-03-31")
    return rows


class PaymentsTests(unittest.TestCase):
    def test_consolidation_mixed_payments_and_denominators(self):
        payments, orders, quality = preparar_pagos(payments_fixture())
        self.assertEqual(len(payments), 6)
        self.assertEqual(len(orders), 4)
        stats = resumen_pagos(orders)
        self.assertEqual(stats["amount"], 420)
        self.assertEqual(stats["ticket"], 105)
        self.assertAlmostEqual(stats["financed_pct"], 200 / 3)
        self.assertAlmostEqual(stats["avg_installments"], 8 / 3)
        self.assertEqual(stats["mixed_pct"], 25)
        by_order = orders.set_index("order_id")
        self.assertEqual(by_order.loc["a", "method"], "Pagos mixtos")
        self.assertEqual(by_order.loc["b", "method"], "Tarjeta de crédito")
        self.assertEqual(by_order.loc["b", "installments"], 4)
        self.assertEqual(quality["without_payment"], 1)
        self.assertEqual(quality["invalid_orders"], 1)
        self.assertEqual(quality["unknown_installments"], 1)
        shares = participacion_pagos(payments)
        self.assertAlmostEqual(shares["share"].sum(), 100)
        self.assertEqual(shares["amount"].sum(), stats["amount"])
        groups = agrupar_pedidos_pago(orders)
        self.assertEqual(groups["orders"].sum(), 4)
        self.assertEqual(groups.set_index("method").loc["Pagos mixtos", "ticket"], 100)

    def test_duplicates_do_not_inflate_and_conflicts_fail(self):
        rows = payments_fixture()
        _, orders, _ = preparar_pagos(pd.concat([rows, rows.iloc[:1]]))
        self.assertEqual(resumen_pagos(orders)["amount"], 420)
        conflict = rows.iloc[:1].copy()
        conflict["payment_value"] = 999
        with self.assertRaises(ValueError):
            preparar_pagos(pd.concat([rows, conflict]))

    def test_invalid_amount_excludes_whole_order_and_unknown_type_is_not_mixed(self):
        rows = payments_fixture()
        rows.loc[0, "payment_value"] = -1
        rows.loc[2, "payment_type"] = "not_defined"
        _, orders, quality = preparar_pagos(rows)
        self.assertNotIn("a", orders["order_id"].tolist())
        self.assertEqual(quality["unknown_method"], 1)
        self.assertFalse(orders.set_index("order_id").loc["b", "known_method"])
        self.assertEqual(resumen_pagos(orders)["mixed_pct"], 0)

    def test_empty_and_zero_amounts_render_without_fake_percentages(self):
        empty = payments_fixture().iloc[:0]
        for rows in (empty, payments_fixture().query("order_id == 'e'")):
            _, orders, _ = preparar_pagos(rows)
            self.assertIsNone(resumen_pagos(orders)["financed_pct"])
            for view in ("gerencial", "analitica", "decisiones"):
                rendered = json.dumps(payments_content(rows, view, pd.NaT), cls=PlotlyJSONEncoder)
                self.assertIn("No hay pedidos", rendered)
        rows = payments_fixture().query("order_id == 'c'").copy()
        rows["payment_value"] = 0
        payments, _, _ = preparar_pagos(rows)
        self.assertTrue(participacion_pagos(payments)["share"].isna().all())

    def test_rules_use_real_comparators_and_respect_minimum(self):
        orders = pd.DataFrame([
            {"order_id": f"{method}-{quota}-{i}", "method": method, "amount": amount,
             "installments": quota, "known_method": True, "known_installments": True,
             "gold_segment": segment}
            for method, quota, amount, segment in (
                ("Tarjeta de crédito", 1, 100, "A"),
                ("Tarjeta de crédito", 8, 200, "A"),
                ("Boleto", 1, 50, "B"),
            ) for i in range(30)
        ])
        findings = oportunidades_pago(orders)
        quota = next(f for f in findings if f["group"] == "7 o más cuotas")
        self.assertEqual(quota["gap"], 100)
        self.assertEqual(quota["reference_orders"], 30)
        self.assertEqual(quota["value"], 200)
        self.assertTrue(any(f["kind"] == "medio" for f in findings))
        self.assertTrue(all(f["action"] and f["followup"] for f in findings))
        self.assertFalse(any(f["kind"] == "cuotas" for f in oportunidades_pago(orders, minimum=31)))
        self.assertFalse(oportunidades_pago(orders, uplift=201))
        statuses = {f["status"] for f in comparaciones_pago(orders)}
        self.assertIn("Muestra insuficiente", statuses)
        self.assertIn("Sin hallazgo según estas reglas", statuses)
        orders["amount"] = 0
        self.assertFalse(oportunidades_pago(orders))
        self.assertIn("Referencia monetaria no positiva", {f["status"] for f in comparaciones_pago(orders)})

    def test_daily_and_monthly_evolution_preserve_gaps(self):
        _, orders, _ = preparar_pagos(payments_fixture())
        orders = orders.iloc[:2].copy()
        orders["purchase_date"] = pd.to_datetime(["2018-01-01", "2018-01-03"])
        daily = evolucion_pagos(orders, daily=True)
        self.assertEqual(len(daily), 3)
        self.assertTrue(pd.isna(daily.iloc[1]["amount"]))
        self.assertEqual(daily["amount"].sum(), 300)
        self.assertEqual(daily["orders"].sum(), 2)
        orders["purchase_date"] = pd.to_datetime(["2018-01-01", "2018-03-03"])
        monthly = evolucion_pagos(orders)
        self.assertEqual(len(monthly), 3)
        self.assertTrue(pd.isna(monthly.iloc[1]["ticket"]))
        self.assertTrue(evolucion_pagos(orders.iloc[:0]).empty)

    def test_shares_keep_mixed_orders_separate_without_losing_amounts(self):
        payments, orders, _ = preparar_pagos(payments_fixture())
        records = participacion_pagos(payments).set_index("method")
        classified = participacion_por_tipo_pedido(payments, orders).set_index("method")
        self.assertEqual(records.loc["Tarjeta de crédito", "amount"], 350)
        self.assertEqual(classified.loc["Tarjeta de crédito", "amount"], 270)
        self.assertEqual(classified.loc["Pagos mixtos", "amount"], 100)
        self.assertEqual(classified["orders"].sum(), 4)
        self.assertEqual(classified["amount"].sum(), records["amount"].sum())
        self.assertAlmostEqual(classified["share"].sum(), 100)

    def test_quota_distribution_excludes_mixed_and_unknown_quotas(self):
        _, orders, _ = preparar_pagos(payments_fixture())
        quotas = resumen_cuotas(orders).set_index("range")
        self.assertEqual(quotas["orders"].sum(), 1)
        self.assertEqual(quotas.loc["4–6 cuotas", "median"], 200)
        self.assertTrue(pd.isna(quotas.loc["1 cuota", "median"]))

    def test_coverage_and_denominators_remain_visible_for_invalid_orders(self):
        rows = payments_fixture()
        rendered = json.dumps(payments_content(rows, "gerencial", pd.NaT),
                              cls=PlotlyJSONEncoder, ensure_ascii=False)
        self.assertIn("Cobertura: 4 de 6", rendered)
        self.assertIn("Sin pagos: 1", rendered)
        self.assertIn("Cuotas desconocidas: 1", rendered)
        self.assertIn("R$ 105,00", rendered)
        self.assertIn("2 de 3 con cuotas conocidas", rendered)
        invalid = rows[rows.order_id.isin(["e", "f"])]
        rendered = json.dumps(payments_content(invalid, "gerencial", pd.NaT),
                              cls=PlotlyJSONEncoder, ensure_ascii=False)
        self.assertIn("Cobertura: 0 de 2", rendered)
        self.assertIn("No hay pedidos", rendered)

    def test_each_view_serializes_and_decisions_has_no_general_kpis(self):
        for view in ("gerencial", "analitica", "decisiones"):
            rendered = json.dumps(payments_content(payments_fixture(), view, pd.Timestamp("2018-03-31")),
                                  cls=PlotlyJSONEncoder, ensure_ascii=False)
            self.assertNotIn('"order_id"', rendered)
            if view == "decisiones":
                self.assertNotIn('"business-card"', rendered)
                self.assertNotIn('"type": "Graph"', rendered)
            elif view == "analitica":
                self.assertIn("Pagos mixtos", rendered)
                self.assertIn("Mediana por cuotas", rendered)


if __name__ == "__main__":
    unittest.main()
