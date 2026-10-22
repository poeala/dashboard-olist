import json
import unittest

import pandas as pd
from plotly.utils import PlotlyJSONEncoder

from components.payments import payments_content
from data.payment_metrics import (
    preparar_pagos, resumen_pagos, participacion_pagos,
    agrupar_pedidos_pago, oportunidades_pago,
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
        self.assertTrue(any("7 o más cuotas" in f["finding"] for f in findings))
        self.assertTrue(any("Ticket elevado" in f["finding"] for f in findings))
        self.assertTrue(any("Preferencia observada" in f["finding"] for f in findings))
        self.assertTrue(all(f["evidence"] and f["followup"] for f in findings))
        self.assertFalse(any("7 o más cuotas" in f["finding"] for f in oportunidades_pago(orders, minimum=31)))
        self.assertFalse(any("Ticket elevado" in f["finding"] for f in oportunidades_pago(orders, uplift=201)))
        orders["amount"] = 0
        self.assertFalse(any("Ticket elevado" in f["finding"] for f in oportunidades_pago(orders)))

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
