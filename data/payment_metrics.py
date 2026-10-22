"""Pagos: registros para participación monetaria; pedidos para ticket y cuotas."""
import numpy as np
import pandas as pd

METHODS = {
    "credit_card": "Tarjeta de crédito", "boleto": "Boleto",
    "voucher": "Voucher", "debit_card": "Tarjeta de débito",
}


def preparar_pagos(rows):
    rows = rows.copy()
    payments = rows[rows["has_payment"].fillna(False)].copy()
    # Solo eliminar repeticiones idénticas; una clave conflictiva requiere revisión.
    columns = ["order_id", "payment_sequential", "payment_type", "payment_value", "payment_installments"]
    payments = payments.drop_duplicates(columns)
    keyed = payments[payments["payment_sequential"].notna()]
    if keyed.duplicated(["order_id", "payment_sequential"]).any():
        raise ValueError("Registros de pago contradictorios para una misma clave")
    for col in ("payment_value", "payment_installments"):
        payments[col] = pd.to_numeric(payments[col], errors="coerce")
    payments["valid_value"] = (
        np.isfinite(payments["payment_value"]) & payments["payment_value"].ge(0)
        & payments["payment_sequential"].notna()
    )
    payments["valid_installments"] = (
        np.isfinite(payments["payment_installments"])
        & payments["payment_installments"].ge(1)
        & payments["payment_installments"].mod(1).eq(0)
    )
    types = payments["payment_type"].astype("string").str.strip().str.lower()
    payments["method"] = types.map(METHODS).fillna("Sin información / otro")
    payments["known_method"] = types.isin(METHODS)
    payments["valid_amount"] = payments["payment_value"].where(payments["valid_value"])
    payments["valid_quota"] = payments["payment_installments"].where(payments["valid_installments"])
    grouped = payments.groupby("order_id")
    summary = grouped.agg(
        records=("has_payment", "size"), valid_amounts=("valid_value", "all"),
        known_method=("known_method", "all"), method_count=("method", "nunique"),
        method=("method", "first"), known_installments=("valid_installments", "all"),
        installments=("valid_quota", "max"),
    )
    summary["amount"] = grouped["valid_amount"].sum(min_count=1)
    orders = rows[["order_id", "purchase_date", "gold_segment"]].drop_duplicates("order_id").set_index("order_id")
    orders = orders.join(summary).reset_index()
    orders["complete"] = orders["valid_amounts"].eq(True) & orders["records"].gt(0)
    orders["known_method"] = orders["known_method"].eq(True)
    orders["known_installments"] = orders["known_installments"].eq(True)
    orders["method"] = orders["method"].fillna("Sin información / otro")
    orders.loc[orders["method_count"].gt(1), "method"] = "Pagos mixtos"
    orders.loc[~orders["known_method"], "method"] = "Sin información / otro"
    orders["gold_segment"] = orders["gold_segment"].fillna("Sin segmento")
    orders["financed"] = orders["known_installments"] & orders["installments"].gt(1)
    orders["mixed"] = orders["known_method"] & orders["method_count"].gt(1)
    complete = orders[orders["complete"]].copy()
    payments = payments[payments["order_id"].isin(complete["order_id"])]
    quality = {
        "source_orders": len(orders), "without_payment": int(orders["records"].isna().sum()),
        "invalid_orders": int((orders["records"].notna() & ~orders["complete"]).sum()),
        "unknown_installments": int((~complete["known_installments"]).sum()),
        "unknown_method": int((~complete["known_method"]).sum()),
    }
    return payments, complete, quality


def resumen_pagos(orders):
    quotas = orders[orders["known_installments"]]
    methods = orders[orders["known_method"]]
    return {
        "amount": orders["amount"].sum() if len(orders) else None,
        "orders": len(orders), "ticket": orders["amount"].mean(),
        "financed_pct": 100 * quotas["financed"].mean() if len(quotas) else None,
        "avg_installments": quotas["installments"].mean(),
        "mixed_pct": 100 * methods["mixed"].mean() if len(methods) else None,
        "quota_orders": len(quotas), "method_orders": len(methods),
    }


def participacion_pagos(payments):
    result = payments.groupby("method", as_index=False).agg(
        amount=("payment_value", "sum"), records=("order_id", "size"), orders=("order_id", "nunique"),
    )
    total = result["amount"].sum()
    result["share"] = 100 * result["amount"] / total if total > 0 else np.nan
    return result.sort_values("amount", ascending=False)


def agrupar_pedidos_pago(orders, dimension="method"):
    return orders.groupby(dimension, as_index=False).agg(
        orders=("order_id", "size"), amount=("amount", "sum"),
        ticket=("amount", "mean"), median=("amount", "median"),
    )


def preferencias_segmento(orders):
    usable = orders[orders["known_method"] & orders["gold_segment"].ne("Sin segmento")]
    result = usable.groupby(["gold_segment", "method"], as_index=False).agg(orders=("order_id", "size"))
    result["segment_orders"] = result.groupby("gold_segment")["orders"].transform("sum")
    result["share"] = 100 * result["orders"] / result["segment_orders"]
    return result


def oportunidades_pago(orders, minimum=30, uplift=20, preference_pp=10):
    """Contrastes descriptivos con el resto, sin predicciones ni atribución causal."""
    results = []
    def append(finding, evidence, action, followup, count):
        results.append({"priority": "Explorar", "finding": finding, "orders": int(count),
                        "evidence": evidence, "action": action, "followup": followup})
    known = orders[orders["known_method"]]
    for method, group in known.groupby("method"):
        if method == "Pagos mixtos":
            continue
        rest = known[known["method"].ne(method)]
        if len(group) >= minimum and len(rest) >= minimum and rest["amount"].mean() > 0:
            gap = 100 * (group["amount"].mean() / rest["amount"].mean() - 1)
            if gap >= uplift:
                append(f"Ticket elevado · {method}",
                       f"Ticket R$ {group['amount'].mean():.2f} en {len(group)} pedidos; "
                       f"resto R$ {rest['amount'].mean():.2f} en {len(rest)} (+{gap:.1f} %).",
                       "Evaluar una oferta para usuarios de este medio, revisando categorías, costos y margen antes de probarla.",
                       "Comparar conversión y margen incremental con un grupo de control.", len(group))
    credit = orders[orders["method"].eq("Tarjeta de crédito") & orders["known_installments"]]
    single = credit[credit["installments"].eq(1)]
    for label, low, high in (("2–3 cuotas", 2, 3), ("4–6 cuotas", 4, 6), ("7 o más cuotas", 7, float("inf"))):
        group = credit[credit["installments"].between(low, high)]
        if len(group) >= minimum and len(single) >= minimum and single["amount"].median() > 0:
            gap = 100 * (group["amount"].median() / single["amount"].median() - 1)
            if gap >= uplift:
                append(f"Mayor importe asociado a {label}",
                       f"Mediana R$ {group['amount'].median():.2f} en {len(group)} pedidos; "
                       f"crédito en una cuota R$ {single['amount'].median():.2f} en {len(single)} (+{gap:.1f} %).",
                       "Evaluar viabilidad y costo de financiación en este rango y diseñar una prueba comercial acotada.",
                       "Medir conversión y margen neto de costos financieros; más cuotas no implica más ventas.", len(group))
    preferences = preferencias_segmento(orders)
    usable = known[known["gold_segment"].ne("Sin segmento")]
    for _, row in preferences.iterrows():
        rest = usable[usable["gold_segment"].ne(row["gold_segment"])]
        if row["orders"] >= minimum and len(rest) >= minimum:
            rest_share = 100 * rest["method"].eq(row["method"]).mean()
            gap = row["share"] - rest_share
            if gap >= preference_pp:
                append(f"Preferencia observada · {row['gold_segment']} · {row['method']}",
                       f"{int(row['orders'])}/{int(row['segment_orders'])} pedidos del segmento "
                       f"({row['share']:.1f} %), frente a {rest_share:.1f} % en {len(rest)} pedidos "
                       f"del resto de segmentos (+{gap:.1f} pp).",
                       "Explorar promociones por medio y segmento; validar su composición y el momento de la clasificación Gold.",
                       "Comparar adopción, conversión y margen en un piloto con control; no interpretar pedidos como clientes únicos.", row["orders"])
    return sorted(results, key=lambda item: (-item["orders"], item["finding"]))
